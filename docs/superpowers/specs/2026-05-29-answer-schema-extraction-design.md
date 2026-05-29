# Answer Schema And Extraction Design

## Context

The benchmark currently stores RDKit baseline tasks with a JSON-oriented
`answer_schema`, and the scoring path expects structured answer dictionaries
containing `task_id` and `candidates`. That is convenient for samples and tests,
but it does not describe how a participating model's raw text response should be
rendered, extracted, and converted into the verifier input.

This design standardizes two related boundaries:

- the prompt content shown to participating models;
- the verifier-side extraction layer that converts raw model text into the
  existing structured verifier input.

The verifier implementation should continue to score structured candidates and
should not need to parse free-form model text directly.

## Model-Facing Prompt Format

Each task prompt should use a compact, consistent structure:

1. First sentence: state the primary objective, including what kind of object the
   model should propose, such as a small molecule, catalyst, material, or drug.
2. Next section: list the conditions the answer must satisfy as bullets.
3. Final section: state the output-format requirement exactly.

For the RDKit small-molecule tasks, the canonical pattern is:

```text
Propose one valid single-component small-molecule SMILES.

The molecule must satisfy:
- <condition 1>
- <condition 2, if any>

Your final answer must appear on its own line exactly in this format:
FINAL ANSWER: <SMILES>
```

The prompt may allow the model to include reasoning or explanation before the
final answer. The only machine-read answer is the final answer line.

The prompt must avoid exposing verifier internals such as verifier names,
implementation libraries, aggregation formulas, or hidden domain checks. It may
show user-relevant target ranges and objectives, because those define the task.

## Answer Schema

Task cards should describe the response contract with a final-answer-line
schema instead of a JSON object schema:

```yaml
answer_schema:
  format: final_answer_line
  final_answer_prefix: "FINAL ANSWER:"
  value_type: smiles
  cardinality: one
  example: "FINAL ANSWER: CC(=O)Oc1ccccc1C(=O)O"
```

Field meanings:

- `format`: identifies that the extractor should parse a marked final answer
  line rather than JSON.
- `final_answer_prefix`: the exact prefix that starts the answer line.
- `value_type`: the extracted value's semantic type. For RDKit baseline tasks,
  this is `smiles`.
- `cardinality`: only one final candidate is accepted for these tasks.
- `example`: model-facing example of the exact required final line.

## Extraction Contract

Add a small extraction layer before verifier routing. It should accept a raw
model response and a task card, then return either a structured answer or a
structured parse error.

The extractor should:

1. Read `task["answer_schema"]`.
2. For `format: final_answer_line`, find the last non-empty line that starts
   with the exact `final_answer_prefix`.
3. Extract the text after the prefix and trim surrounding whitespace.
4. Reject an empty value.
5. Reject values that clearly contain more than a single candidate, such as
   newline-separated values after extraction or comma/semicolon-separated
   candidates where the whole value is not a plausible single answer.
6. Return the existing verifier input shape:

```python
{
    "task_id": task_id,
    "candidates": [{"smiles": extracted_value}],
    "raw_answer": original_response,
    "extracted_answer": extracted_value,
}
```

The exact prefix match should be case-sensitive for the first implementation.
This keeps the benchmark contract simple and reduces ambiguity. If future runs
need a more forgiving policy, that should be an explicit schema option rather
than an implicit parser behavior.

## Scoring Flow

The scoring pipeline should support both current structured answer JSONL and raw
model response JSONL:

- If an answer record already contains `candidates`, route it through the
  existing verifier path unchanged. This preserves sample answers and existing
  tests.
- If an answer record contains `response` or `raw_answer`, extract the final
  answer line first, then route the normalized answer through the existing
  verifier path.
- If extraction fails, return a normal benchmark row with `status: error`,
  `failure_type: parse_error`, zero score, and a message explaining the missing
  or malformed final answer line.

Recommended raw response JSONL shape:

```json
{"task_id": "rdkit_qed_max_001", "response": "Reasoning text...\nFINAL ANSWER: CCO"}
```

The extraction layer owns raw-text parse failures. The RDKit verifier continues
to own chemical parse failures, validity failures, domain failures, descriptor
calculation, and property scoring.

## Error Handling

Parse errors should be deterministic and auditable:

- missing `FINAL ANSWER:` line -> `parse_error`;
- empty final answer value -> `parse_error`;
- malformed raw answer record with no `task_id` -> existing task routing error;
- extracted value present but invalid SMILES -> verifier-level `parse_error`;
- extracted value with multiple components such as `CCO.O` -> verifier-level
  `validity_error`, because it is a parsed candidate that violates chemistry
  validity rules.

Rows should preserve `raw_answer` and `extracted_answer` where available in the
detailed result or an optional debug view, so extraction behavior can be audited
without changing the public score fields.

## Tests

Add focused coverage for:

- task cards use `answer_schema.format: final_answer_line`;
- prompts follow the standardized structure and end with the exact final-answer
  instruction;
- raw responses with reasoning plus a valid final answer score successfully;
- multiple `FINAL ANSWER:` lines use the last one;
- missing final answer line returns `parse_error`;
- empty final answer line returns `parse_error`;
- structured `candidates` answers still score through the existing path.

## Implementation Notes

Keep the extraction layer separate from individual verifiers. This avoids
copying parser logic into every verifier and makes future schemas possible for
non-SMILES tasks, such as catalysts, materials, reaction conditions, or tabular
answers.

The first implementation should stay conservative: one extracted value, exact
prefix, no hidden fallback to regex-based SMILES extraction. That preserves the
distinction between following the benchmark output contract and satisfying the
scientific objective.
