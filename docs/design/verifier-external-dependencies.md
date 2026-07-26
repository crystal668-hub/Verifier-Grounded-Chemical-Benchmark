# Verifier external dependency preflight

Verifier Python modules may depend on native executables that are not installed by the VGB wheel. Each affected verifier declares those commands in `external_dependencies`:

```yaml
external_dependencies:
- executable: crest
  version: '2.12'
  conda_environment: vgb-crest
```

`executable` and `version` are required. `conda_environment` is optional and names the environment that VGB may discover when the command is absent from `PATH` or has the wrong version. Unknown fields and duplicate executable declarations are rejected while loading the verifier spec.

Before scoring, `vgb-score` maps submitted task IDs to their normal and hard constraints, deduplicates the referenced verifier specs, and checks only their declared dependencies. This prevents an xTB-only submission from requiring CREST while ensuring the conformer-search task checks both tools.

Resolution follows this order:

1. Check the current `PATH` and run `<executable> --version`.
2. If the command is missing or has the wrong version, locate `conda_environment` through the active `CONDA_PREFIX` or `conda env list --json`.
3. Prepend that environment's executable directories to the verifier process `PATH` and repeat the version check.
4. Stop before launching any affected verifier when resolution or version validation fails.

The subprocess verifier runner repeats the same check for direct Python API use. A failure is infrastructure-scoped `verifier_environment_error`; it is not converted into a candidate score.
