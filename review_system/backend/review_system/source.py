import hashlib, json, re, subprocess
from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any
import yaml
from verifier_grounded_benchmark import list_tracks, load_track
from verifier_grounded_benchmark.task.models import public_task_dict
from verifier_grounded_benchmark.task.schema.common import linear_goal_from_profile
from .config import SOURCE_ROOT

CODE_FENCE = re.compile(r"```(cif|xyz|pdb|sdf|mol|json)\s*\n([\s\S]*?)```", re.I)

def source_revision() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=SOURCE_ROOT.parents[1], text=True).strip()
    except Exception:
        return "working-tree"

def _fingerprint(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()

def split_attachments(task: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    task = deepcopy(task); attachments=[]; prompt=task.get("prompt", "")
    input_values = {str(x.get("value")): x for x in task.get("input_objects", []) if isinstance(x, dict) and isinstance(x.get("value"), str)}
    def replace(match: re.Match[str]) -> str:
        kind, content = match.group(1).lower(), match.group(2)
        if len(content.strip()) < 80 and not any(content.strip() == value.strip() for value in input_values): return match.group(0)
        name = f"{task['task_id']}-{len(attachments)+1}.{kind}"
        attachments.append({"name": name, "media_type": f"text/{kind}", "content": content, "source": "prompt"})
        return f"[附件：{name}]"
    task["prompt"] = CODE_FENCE.sub(replace, prompt)
    for obj in task.get("input_objects", []) or []:
        if isinstance(obj, dict) and isinstance(obj.get("value"), str) and len(obj["value"].strip()) >= 80:
            if not any(obj["value"].strip() == a["content"].strip() for a in attachments):
                kind = str(obj.get("type", "txt")).lower().replace("/", "-")
                name = f"{task['task_id']}-{len(attachments)+1}.{kind}"
                attachments.append({"name": name, "media_type": f"text/{kind}", "content": obj["value"], "source": "input_object", "object_id": obj.get("object_id")})
            obj["value"] = None
            obj["attachment_ref"] = attachments[-1]["name"]
    return task, attachments

def _plain(value: Any) -> Any:
    """Convert immutable task-pack mappings into JSON-safe plain values."""
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return deepcopy(value)


def _score_range(profile: Mapping[str, Any], gold: Mapping[str, Any] | None) -> dict[str, Any] | None:
    profile_type = profile.get("type")
    if profile_type == "window":
        full_score = profile.get("full_score", {})
        return {"kind": "满分区间", "min": full_score.get("min"), "max": full_score.get("max"), "unit": profile.get("unit")}
    if profile_type == "maximize":
        return {"kind": "越高越好", "full_score_target": profile.get("full_score_target"), "zero_score_anchor": profile.get("zero_score_anchor"), "unit": profile.get("unit")}
    if profile_type == "minimize":
        return {"kind": "越低越好", "full_score_target": profile.get("full_score_target"), "zero_score_anchor": profile.get("zero_score_anchor"), "unit": profile.get("unit")}
    if profile_type == "target":
        return {"kind": "目标值", "target": profile.get("full_score_target"), "unit": profile.get("unit")}
    if profile_type == "numeric_gold" and gold is not None and isinstance(gold.get("value"), (int, float)):
        value = float(gold["value"])
        lower = profile.get("lower_tolerance")
        upper = profile.get("upper_tolerance")
        return {"kind": "误差范围", "min": value - lower if isinstance(lower, (int, float)) else None, "max": value + upper if isinstance(upper, (int, float)) else None, "tolerance": {"lower": lower, "upper": upper}, "unit": gold.get("unit") or profile.get("unit")}
    if profile_type == "exact_string" and gold is not None:
        return {"kind": "精确匹配", "expected": gold.get("value")}
    if profile_type == "atom_identity":
        return {"kind": "结构身份匹配", "element_partial_score": profile.get("element_partial_score")}
    return None


def scoring_view(task: dict[str, Any], profiles: Mapping[str, Mapping[str, Any]] | None = None) -> dict[str, Any]:
    scoring = deepcopy(task.get("scoring", {})); constraints = task.get("constraints", []) or []
    profile_map = profiles or task.get("scoring_profiles", {}) or {}
    gold_answers = [_plain(item) for item in task.get("gold_answers", []) or []]
    gold_by_property = {item.get("property"): item for item in gold_answers if isinstance(item, dict)}
    rules=[]
    for constraint in constraints:
        item = _plain(constraint)
        profile = _plain(profile_map.get(constraint.get("scoring_profile"), {}))
        gold = gold_by_property.get(constraint.get("property"))
        item["profile"] = profile
        item["standard_answer"] = gold.get("value") if gold else None
        item["unit"] = (gold or {}).get("unit") or profile.get("unit") or item.get("unit")
        item["score_range"] = _score_range(profile, gold)
        try:
            if profile.get("type") in {"target", "window", "maximize", "minimize", "numeric_gold"}:
                goal = linear_goal_from_profile(profile, gold=(gold or {}).get("value"))
                item["curve"] = {"lower": goal.lower, "upper": goal.upper, "lower_width": goal.lower_width, "upper_width": goal.upper_width}
        except Exception:
            pass
        rules.append(item)
    # Property-calculation tasks express fields through gold_answers rather than constraints.
    # Promote those fields to the same display model so every task has useful scoring detail.
    known_properties = {item.get("property") for item in rules}
    for gold in gold_answers:
        if gold.get("property") in known_properties:
            continue
        profile = _plain(profile_map.get(gold.get("scoring_profile"), {}))
        rules.append({
            "property": gold.get("property"),
            "type": profile.get("type", "gold_answer"),
            "role": "main",
            "scoring_profile": gold.get("scoring_profile"),
            "profile": profile,
            "standard_answer": gold.get("value"),
            "unit": gold.get("unit") or profile.get("unit"),
            "score_range": _score_range(profile, gold),
        })
    return {
        "aggregation": scoring.get("aggregation"),
        "answer_matching": scoring.get("answer_matching"),
        "failure_policy": _plain(task.get("failure_policy", {})),
        "rules": rules,
        "gold_answers": gold_answers,
        "is_multi_field": len(rules) > 1,
        "field_count": len(rules),
    }

def schema_view(task: dict[str, Any]) -> dict[str, Any]:
    keys=["task_id","version","task_type","object_type","difficulty","formal_track","capability_tags","answer_schema","input_objects","requested_properties","structural_domain","structure_identity"]
    return {key: deepcopy(task[key]) for key in keys if key in task}

def load_catalog() -> dict[str, Any]:
    tracks=[]
    for definition in list_tracks(status="formal"):
        track=load_track(definition.name); tasks=[]
        for raw in track._task_pack.tasks_by_id.values():
            view, attachments=split_attachments(raw)
            public=public_task_dict(view)
            full=deepcopy(raw); full.pop("scoring_profiles", None)
            tasks.append({"task_id": raw["task_id"], "version": raw.get("version",1), "data": full, "view": public, "scoring": scoring_view(raw, track._task_pack.scoring_profiles), "schema": schema_view(view), "attachments": attachments, "fingerprint": _fingerprint(full)})
        tracks.append({"name": definition.name, "version": definition.version, "display_name": definition.display_name, "tasks": tasks})
    payload={"commit":source_revision(), "tracks":tracks}
    return {"commit": payload["commit"], "fingerprint": _fingerprint(payload), "tracks": tracks}
