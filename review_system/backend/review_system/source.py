import hashlib, json, re, subprocess
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

def scoring_view(task: dict[str, Any]) -> dict[str, Any]:
    scoring = deepcopy(task.get("scoring", {})); constraints = task.get("constraints", [])
    profiles = task.get("scoring_profiles", {})
    rules=[]
    for constraint in constraints:
        item=deepcopy(constraint); profile=profiles.get(constraint.get("scoring_profile"), {})
        item["profile"] = profile
        try:
            if profile.get("type") in {"target", "window", "maximize", "minimize", "numeric_gold"}:
                goal=linear_goal_from_profile(profile, gold=next((x.get("value") for x in task.get("gold_answers", []) if x.get("property")==constraint.get("property")), None))
                item["curve"]={"lower":goal.lower,"upper":goal.upper,"lower_width":goal.lower_width,"upper_width":goal.upper_width}
        except Exception: pass
        rules.append(item)
    return {"aggregation": scoring.get("aggregation"), "answer_matching": scoring.get("answer_matching"), "failure_policy": task.get("failure_policy"), "rules": rules, "gold_answers": task.get("gold_answers", [])}

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
            tasks.append({"task_id": raw["task_id"], "version": raw.get("version",1), "data": full, "view": public, "scoring": scoring_view(raw), "schema": schema_view(raw), "attachments": attachments, "fingerprint": _fingerprint(full)})
        tracks.append({"name": definition.name, "version": definition.version, "display_name": definition.display_name, "tasks": tasks})
    payload={"commit":source_revision(), "tracks":tracks}
    return {"commit": payload["commit"], "fingerprint": _fingerprint(payload), "tracks": tracks}
