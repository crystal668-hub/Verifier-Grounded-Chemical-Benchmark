# Answer Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement final-answer-line prompts and raw model response extraction so model outputs like `FINAL ANSWER: <SMILES>` can be scored through the existing verifier pipeline.

**Architecture:** Add a small answer extraction module before routing. Keep verifier implementations focused on structured candidate scoring, while `benchmark.evaluate` normalizes either structured `candidates` records or raw `response`/`raw_answer` records into the existing verifier input shape.

**Tech Stack:** Python 3.12, PyYAML, pytest, existing RDKit verifier stack.

---

## File Structure

- `benchmark/answer_extraction.py`: new focused parser for `answer_schema.format: final_answer_line`.
- `benchmark/evaluate.py`: normalize raw answer records before routing and preserve extraction fields in summaries.
- `tasks/rdkit_baseline/tasks.yaml`: convert prompts to the standardized compact structure and replace JSON answer schema with final-answer-line schema.
- `tests/test_answer_extraction.py`: unit tests for extraction behavior.
- `tests/test_evaluate_routing.py`: integration tests for raw response scoring and parse errors.
- `tests/test_small_molecule_rdkit.py`: update prompt/schema assertions to the new format.

## Task 1: Add Final Answer Extraction

**Files:**
- Create: `benchmark/answer_extraction.py`
- Test: `tests/test_answer_extraction.py`

- [x] **Step 1: Write failing extractor tests**

Create `tests/test_answer_extraction.py` with tests for successful extraction, last final answer wins, missing final answer, empty final answer, unsupported schema format, and structured candidates passthrough expectations at the function boundary.

Run: `uv run pytest tests/test_answer_extraction.py -v`

Expected: fail because `benchmark.answer_extraction` does not exist.

- [x] **Step 2: Implement minimal extractor**

Create `benchmark/answer_extraction.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ExtractionResult:
    answer: dict[str, Any] | None
    failure_type: str | None
    message: str | None

    @property
    def ok(self) -> bool:
        return self.answer is not None


def normalize_answer_record(record: dict[str, Any], task: dict[str, Any]) -> ExtractionResult:
    if "candidates" in record:
        return ExtractionResult(record, None, None)

    raw_answer = record.get("response", record.get("raw_answer"))
    if not isinstance(raw_answer, str):
        return ExtractionResult(None, "parse_error", "answer record must include candidates or a raw response string")

    schema = task.get("answer_schema") or {}
    if schema.get("format") != "final_answer_line":
        return ExtractionResult(None, "parse_error", "unsupported answer_schema format")

    prefix = schema.get("final_answer_prefix")
    if not isinstance(prefix, str) or not prefix:
        return ExtractionResult(None, "parse_error", "answer_schema must include final_answer_prefix")

    final_lines = [line for line in raw_answer.splitlines() if line.startswith(prefix)]
    if not final_lines:
        return ExtractionResult(None, "parse_error", f"missing final answer line with prefix {prefix!r}")

    extracted = final_lines[-1][len(prefix) :].strip()
    if not extracted:
        return ExtractionResult(None, "parse_error", "final answer line is empty")

    value_type = schema.get("value_type")
    if value_type != "smiles":
        return ExtractionResult(None, "parse_error", f"unsupported answer_schema value_type: {value_type!r}")

    task_id = record.get("task_id")
    answer = {
        "task_id": task_id,
        "candidates": [{"smiles": extracted}],
        "raw_answer": raw_answer,
        "extracted_answer": extracted,
    }
    return ExtractionResult(answer, None, None)
```

- [x] **Step 3: Verify extractor tests pass**

Run: `uv run pytest tests/test_answer_extraction.py -v`

Expected: pass.

## Task 2: Route Raw Responses Through Extraction

**Files:**
- Modify: `benchmark/evaluate.py`
- Test: `tests/test_evaluate_routing.py`

- [x] **Step 1: Write failing routing tests**

Add integration tests showing:

- a record with `response: "Reasoning...\nFINAL ANSWER: <SMILES>"` scores successfully;
- a record missing the final answer line returns `failure_type: parse_error`;
- `summarize_row` includes `raw_answer` and `extracted_answer` when present.

Run: `uv run pytest tests/test_evaluate_routing.py -v`

Expected: fail because `evaluate_one` currently passes raw records directly to the verifier.

- [x] **Step 2: Normalize before verifier routing**

Modify `benchmark/evaluate.py` so `evaluate_one`:

1. resolves `task_id` and task as it already does;
2. calls `normalize_answer_record(answer, task)`;
3. returns a routing-style parse error if extraction fails;
4. passes the normalized answer to the selected verifier;
5. copies `raw_answer` and `extracted_answer` from the normalized answer into the result if present.

Update `summarize_row` to include `raw_answer` and `extracted_answer` when those fields exist on the result.

- [x] **Step 3: Verify routing tests pass**

Run: `uv run pytest tests/test_evaluate_routing.py -v`

Expected: pass.

## Task 3: Standardize RDKit Task Prompts And Schema

**Files:**
- Modify: `tasks/rdkit_baseline/tasks.yaml`
- Modify: `tests/test_small_molecule_rdkit.py`

- [x] **Step 1: Write/update failing task-card tests**

Update `test_task_cards_bind_to_verifier_spec` to assert:

```python
assert task["answer_schema"]["format"] == "final_answer_line"
assert task["answer_schema"]["final_answer_prefix"] == "FINAL ANSWER:"
assert task["answer_schema"]["value_type"] == "smiles"
assert task["answer_schema"]["cardinality"] == "one"
```

Update `test_prompts_expose_targets_without_verifier_internals` to assert each prompt:

- starts with `Propose one valid single-component small-molecule SMILES.`;
- contains `The molecule must satisfy:`;
- contains the exact final output instruction;
- ends with `FINAL ANSWER: <SMILES>`.

Run: `uv run pytest tests/test_small_molecule_rdkit.py -v`

Expected: fail because current task cards still use JSON schema and prose prompts.

- [x] **Step 2: Update task YAML**

For every RDKit task:

- use the same first sentence;
- list objective conditions under `The molecule must satisfy:`;
- end with:

```text
Your final answer must appear on its own line exactly in this format:
FINAL ANSWER: <SMILES>
```

Replace the schema anchor with:

```yaml
answer_schema: &answer_schema
  format: final_answer_line
  final_answer_prefix: "FINAL ANSWER:"
  value_type: smiles
  cardinality: one
  example: "FINAL ANSWER: CC(=O)Oc1ccccc1C(=O)O"
```

- [x] **Step 3: Verify task-card tests pass**

Run: `uv run pytest tests/test_small_molecule_rdkit.py -v`

Expected: pass.

## Task 4: Full Verification And Commit

**Files:**
- All modified files from Tasks 1-3.

- [x] **Step 1: Run the full suite**

Run: `uv run pytest`

Expected: all tests pass.

- [x] **Step 2: Review git diff**

Run: `git diff --stat && git diff --check`

Expected: only intended files changed and no whitespace errors.

- [ ] **Step 3: Commit implementation**

Run:

```bash
git add benchmark/answer_extraction.py benchmark/evaluate.py tests/test_answer_extraction.py tests/test_evaluate_routing.py tests/test_small_molecule_rdkit.py tasks/rdkit_baseline/tasks.yaml docs/superpowers/plans/2026-05-29-answer-extraction-implementation.md
git commit -m "Implement final answer extraction"
```

Expected: a commit containing the implementation, tests, prompt/schema updates, and implementation plan.

## Self-Review

- Spec coverage: covered prompt standardization, final-answer-line schema, extraction, routing, parse errors, raw response JSONL compatibility, and structured candidate compatibility.
- Placeholder scan: no TBD/TODO/fill-in placeholders are present.
- Type consistency: the extractor returns normalized dictionaries compatible with existing verifier input, and routing errors reuse existing `routing_error` shape.
