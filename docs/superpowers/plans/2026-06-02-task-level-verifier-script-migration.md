# Deprecated Task-Level Verifier Script Migration Plan

This plan is intentionally deprecated.

The task-level RDKit script design was superseded by the descriptor-level verifier design. Do not implement or revive the old shape where each task points to a task-specific script such as `verifiers/tasks/rdkit_logp_window_003.py`, and do not route formal RDKit scoring through `verifiers/tasks/rdkit_common.py` or a Python verifier registry.

The active design is:

```text
task constraint/property -> verification_script -> shared backend/tool environment
```

Formal RDKit baseline tasks bind `verifier_id` at the constraint level. Tasks that compute the same descriptor share the same script, for example all QED constraints call `verifiers/descriptors/rdkit_qed.py`. Multi-objective tasks call multiple descriptor scripts and let the runner aggregate the returned constraint scores.

The Python verifier registry is also obsolete. Formal benchmark routing must come from verifier specs and `verification_script` entries, not from registry branches.
