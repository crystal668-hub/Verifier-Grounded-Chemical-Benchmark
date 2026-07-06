# SolTranNet + MolGpKa Verifier Backend Design

Date: 2026-07-06

## Goal

Deploy SolTranNet and MolGpKa as benchmark-usable verifier backends quickly,
using the already validated local Docker images while preserving the existing
property-level verifier script contract.

The first deployable target is a usable backend and script layer. This round
does not add a benchmark task pack, formal registry entry, calibrated prompt
set, or scoring distribution.

## Scope

This design covers:

- Docker-backed runtime adapters for SolTranNet and MolGpKa.
- Property-level verifier scripts that read JSON from stdin and write the
  repository's standardized verifier result JSON to stdout.
- SolTranNet aqueous solubility prediction as a scalar logS-style property.
- MolGpKa predictions exposed as three scalar scoring properties:
  `molgpka_min_pka`, `molgpka_max_pka`, and `molgpka_pka_count`.
- Domain validation for single-component small-molecule SMILES.
- Environment check scripts for both Docker images.
- Unit tests that do not require Docker by default.
- Explicit live Docker smoke tests behind an opt-in environment variable.
- A migration plan from external Docker calls to local model runtimes inside a
  future single official verifier image.

This design does not cover:

- Adding or registering a new formal benchmark track.
- Adding `tasks/` task packs, `sample_answers.jsonl`, or verifier specs for a
  new public track.
- Repacking SolTranNet or MolGpKa into the final official verifier image during
  this implementation round.
- Docker Compose, a long-running service manager, or public service deployment.
- Training, fine-tuning, recalibration, or changing either model's weights.
- Using public database labels as runtime oracle values.

## Current Repository Context

The benchmark architecture binds each scoring constraint to a property-level
`verification_script`. Each script reads a payload containing `task`,
`constraint`, `verifier_spec`, and `candidate`, then returns a standardized JSON
result. Shared model or tool code lives below `src/verifiers/backends/`.

The current repository already follows this pattern for RDKit descriptors,
RDKit force-field workflows, xTB, ADMET-AI, OPERA, MatGL, and OpenMM/OpenFF
optional backends. Current formal builtin tracks are RDKit and xTB only. Newer
backend work can therefore land as backend modules and property scripts before
being promoted into formal task packs.

This design follows the same layering:

```text
task constraint/property -> verification_script -> shared backend -> model runtime
```

For this round, `model runtime` means an external Docker image that has already
been smoke tested locally. The surrounding verifier contract remains identical
to existing local Python backends.

## Validated Model Runtime Facts

SolTranNet is available through the Ersilia model image
`ersiliaos/eos6oli:v1.0.0`. Local smoke testing confirmed that the service can
be started and queried through HTTP `/run`, with:

- input columns: `["smiles"]`
- output columns: `["solubility"]`
- valid request shape: a raw JSON list such as `["CCO", "c1ccccc1"]`
- observed sample outputs:
  - `CCO -> 2.297180414199829`
  - `c1ccccc1 -> -1.052748203277588`

MolGpKa is available through
`ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d`.
Local smoke testing confirmed that it runs on Docker Desktop via amd64
emulation on the current arm64 host. The default container entrypoint starts a
uWSGI socket, not a normal HTTP endpoint, so the first verifier integration
should call the container's Python API through `micromamba run -n MolGpka`.

The validated Python call is equivalent to:

```bash
micromamba run -n MolGpka python -c \
  "from cts_molgpka import CTSMolgpka; import json; print(json.dumps(CTSMolgpka().main('CC(O)=O')))"
```

Observed sample output:

```json
["CC(O)=O", 1, [8.34]]
```

## Recommended Strategy

Use a Docker-backed adapter layer now, not a production verifier image yet.

The immediate runtime should:

1. Check that Docker is available and that the configured image exists locally
   or can be pulled by the developer.
2. For SolTranNet, either call a configured existing HTTP service or start and
   reuse a named local container exposing `/run`.
3. For MolGpKa, run a one-shot container command that invokes the container's
   Python API and returns JSON.
4. Convert model output into the repository's standard verifier result schema.
5. Keep all model-specific command details inside backend/runtime modules, not
   inside task specs or property scripts.

This is the fastest path to usable verifier services because it reuses the two
images that already passed local smoke tests. It also keeps the code close to
the final architecture because property scripts, property names, result schema,
and scoring behavior will not need to change when these models later move
inside a single official verifier image.

## Components

### Shared Docker Runtime Adapter

Create a small helper module:

- `src/verifiers/backends/docker_model_runtime.py`

Responsibilities:

- Resolve Docker executable from `spec`, environment variables, or `PATH`.
- Run `docker image inspect` for environment diagnostics.
- Run one-shot Docker commands with timeouts and captured stdout/stderr.
- Optionally start and reuse a named HTTP container for SolTranNet.
- Poll HTTP health or `/run/columns` endpoints before prediction.
- Return parsed JSON to model-specific backends.
- Raise narrow exceptions that backends map to existing failure types.

Expected exception classes:

- `DockerRuntimeEnvironmentError`: Docker executable, daemon, image, or service
  is missing or unavailable.
- `DockerRuntimeTimeout`: Docker command or HTTP prediction timed out.
- `DockerRuntimeToolError`: model command exited nonzero, returned malformed
  output, or returned an unexpected schema.

Use only the Python standard library for this adapter: `subprocess`, `json`,
`time`, `urllib.request`, and `urllib.error`. Do not add the Docker SDK as a new
dependency.

### SolTranNet Backend

Create:

- `src/verifiers/backends/soltrannet_properties.py`
- `src/verifiers/physchem/soltrannet_log_s.py`

The property script should call `run_property_script` with:

- `expected_name="soltrannet_log_s"`
- `spec_field="property_name"`
- `mismatch_label="property"`

The backend should:

1. Validate that `spec["property_name"]` matches `constraint["property"]`.
2. Require `candidate["smiles"]`.
3. Reject multi-component SMILES containing `.`.
4. Parse and canonicalize with RDKit.
5. Compute domain properties:
   - `mw`
   - `heavy_atom_count`
   - `formal_charge`
   - `elements`
6. Apply the configured small-molecule domain gate.
7. Call SolTranNet with the canonical SMILES.
8. Parse output field `solubility`.
9. Store it as `properties["soltrannet_log_s"]`.
10. Score with the shared `score_constraint`.

Recommended default domain:

```yaml
domain:
  allowed_elements: [C, N, O, F, P, S, Cl, Br, I]
  heavy_atom_count: [1, 80]
  mw: [1.0, 1000.0]
  formal_charge: [-2, 2]
```

Recommended runtime spec shape:

```yaml
soltrannet:
  runtime: external_docker
  image: ersiliaos/eos6oli:v1.0.0
  container_name: vgb-soltrannet-eos6oli
  host: 127.0.0.1
  port: 18081
  base_url: null
  startup_timeout_seconds: 60
  prediction_timeout_seconds: 30
```

If `base_url` or `SOLTRANNET_BASE_URL` is configured, the backend should use
that URL and should not manage a Docker container. If neither is configured,
the backend should start or reuse the named container on the configured port.

### MolGpKa Backend

Create:

- `src/verifiers/backends/molgpka_properties.py`
- `src/verifiers/physchem/molgpka_min_pka.py`
- `src/verifiers/physchem/molgpka_max_pka.py`
- `src/verifiers/physchem/molgpka_pka_count.py`

Each property script should call `run_property_script` with its own expected
property name:

- `molgpka_min_pka`
- `molgpka_max_pka`
- `molgpka_pka_count`

The backend should:

1. Validate that `spec["property_name"]` matches `constraint["property"]`.
2. Require `candidate["smiles"]`.
3. Reject multi-component SMILES containing `.`.
4. Parse and canonicalize with RDKit.
5. Compute domain properties:
   - `mw`
   - `heavy_atom_count`
   - `formal_charge`
   - `elements`
6. Apply the configured small-molecule domain gate.
7. Run the MolGpKa container entrypoint for the canonical SMILES.
8. Parse output shaped like `[smiles, site_count, pka_values]`.
9. Store diagnostics:
   - `molgpka_pka_values`
   - `molgpka_pka_count`
10. Store the requested scalar property.
11. Score with the shared `score_constraint`.

Recommended runtime spec shape:

```yaml
molgpka:
  runtime: external_docker
  image: ghcr.io/quanted/cts-molgpka:dev-acafcb3fb93dbf8dcf6c952cbf3b12161e7f468d
  platform: linux/amd64
  timeout_seconds: 120
```

Property semantics:

- `molgpka_pka_count`: number of predicted ionizable sites.
- `molgpka_min_pka`: minimum value in the predicted pKa list.
- `molgpka_max_pka`: maximum value in the predicted pKa list.

If MolGpKa returns zero predicted sites:

- `molgpka_pka_count` should return `status: ok` with value `0`.
- `molgpka_min_pka` and `molgpka_max_pka` should return `domain_error` with a
  message that no ionizable pKa values were predicted. This avoids inventing a
  sentinel numeric pKa value.

## Result Schema

Successful SolTranNet result properties should include:

```json
{
  "mw": 46.069,
  "heavy_atom_count": 3,
  "formal_charge": 0,
  "elements": ["C", "O"],
  "soltrannet_log_s": 2.297180414199829
}
```

Successful MolGpKa result properties should include:

```json
{
  "mw": 60.052,
  "heavy_atom_count": 4,
  "formal_charge": 0,
  "elements": ["C", "O"],
  "molgpka_pka_values": [8.34],
  "molgpka_pka_count": 1,
  "molgpka_min_pka": 8.34
}
```

For `molgpka_max_pka`, the scalar key should be `molgpka_max_pka`. For
`molgpka_pka_count`, the scalar key should be `molgpka_pka_count`; the pKa list
should still be retained for diagnostics.

All result objects should keep the existing fields:

- `task_id`
- `verifier_id`
- `status`
- `canonical_smiles`
- `properties`
- `scores`
- `failure_type`
- `message`
- `versions`

## Failure Mapping

Use the repository's existing failure taxonomy:

| Condition | Failure type |
|---|---|
| Missing or non-string SMILES | `parse_error` |
| RDKit parse failure | `parse_error` |
| Multi-component SMILES | `validity_error` |
| Domain gate failure | `domain_error` |
| Property mismatch between script/spec/constraint | `verifier_spec_error` |
| Docker executable, daemon, image, or configured service missing | `verifier_environment_error` |
| Docker command or model service timeout | `verifier_timeout` |
| Nonzero Docker exit, malformed JSON, missing output field, unexpected model schema | `verifier_tool_error` |
| Constraint scoring exception | `verifier_spec_error` |

When a model runtime error happens after SMILES parsing and domain property
computation, include the domain properties in the error result where practical.
This matches the existing OPERA/OpenMM style and helps diagnose whether failures
are chemical-domain issues or runtime issues.

## Environment Check Scripts

Create:

- `scripts/check_soltrannet_env.py`
- `scripts/check_molgpka_env.py`

Both scripts should print structured JSON to stdout and exit nonzero only when
the check itself cannot produce JSON.

`check_soltrannet_env.py` should:

1. Report Docker availability.
2. Report the configured or default image.
3. Report whether the image is locally inspectable.
4. Optionally start or use the configured service.
5. Read `/run/columns/input` and `/run/columns/output`.
6. Run a prediction for `CCO`.
7. Return observed property value and version/runtime metadata.

`check_molgpka_env.py` should:

1. Report Docker availability.
2. Report the configured or default image.
3. Report whether the image is locally inspectable.
4. Report configured platform.
5. Run `CTSMolgpka().main("CC(O)=O")`.
6. Return observed site count and pKa list.

The check scripts should accept flags for image, platform, timeout, and sample
SMILES. They should be documented as developer diagnostics, not as formal
benchmark tasks.

## Testing Strategy

Default tests must not require Docker Desktop, registry access, or the model
images. They should use monkeypatches and fake runtime functions.

Required unit tests:

- SolTranNet backend scores a mocked numeric prediction.
- SolTranNet backend maps missing image/service to `verifier_environment_error`.
- SolTranNet backend maps timeout to `verifier_timeout`.
- SolTranNet parser rejects missing `solubility`.
- MolGpKa backend scores mocked `min_pka`, `max_pka`, and `pka_count`.
- MolGpKa backend returns `domain_error` for min/max when no pKa values are
  predicted.
- MolGpKa backend returns count `0` for no predicted pKa values.
- MolGpKa parser rejects malformed output and nonnumeric pKa values.
- Each property script rejects property mismatch through `run_property_script`.
- Each property script returns a standard JSON result on a mocked happy path.
- Docker runtime adapter forms the expected `docker` commands and maps nonzero
  exits, missing executable, and timeouts into narrow exceptions.
- Environment check scripts return structured JSON when runtime functions are
  monkeypatched.

Live Docker smoke tests should be opt-in only:

```bash
VGB_RUN_DOCKER_SMOKE=1 pytest tests/test_soltrannet_molgpka_docker_smoke.py -v
```

The live smoke should verify:

- `ersiliaos/eos6oli:v1.0.0` can predict `CCO` and benzene.
- `cts-molgpka` can predict acetic acid.
- Each live prediction can flow through the backend scoring path.

The normal verification command after implementation should remain:

```bash
pytest
```

## Documentation

Create or update:

- `docs/tracks/SolTranNet-MolGpKa.md`

The track document should state that this is a backend capability document, not
a registered formal benchmark track. It should include:

- Model provenance and image references.
- Supported properties and units/semantics.
- Runtime modes.
- Environment check commands.
- Live Docker smoke command.
- Known limitations:
  - SolTranNet is a single logS-style aqueous solubility model.
  - MolGpKa predicts a list of pKa values without an acidic/basic split in this
    first wrapper.
  - MolGpKa currently uses an amd64 image and may run through emulation on
    arm64 Docker Desktop.
  - External Docker runtime is a development deployment path, not the final
    official release shape.

## Migration To A Single Official Verifier Image

The project's final design calls for a single official verifier image. This
implementation should therefore isolate external Docker details behind runtime
interfaces so the migration does not require changing property scripts or task
specs.

The current implementation should support this runtime boundary:

```text
backend evaluator
  -> model runtime interface
    -> external_docker implementation
    -> future local implementation
```

The future local implementation should:

1. Keep property scripts unchanged.
2. Keep property names unchanged:
   - `soltrannet_log_s`
   - `molgpka_min_pka`
   - `molgpka_max_pka`
   - `molgpka_pka_count`
3. Keep the result schema unchanged.
4. Add `runtime: local` to model-specific spec blocks.
5. Dispatch SolTranNet prediction to a Python module, CLI, or local HTTP process
   installed inside the official verifier image.
6. Dispatch MolGpKa prediction to the installed MolGpKa Python environment
   inside the official verifier image.
7. Remove any dependency on host Docker for formal published specs.
8. Keep `external_docker` as a developer fallback where useful.

Recommended future official-image spec shape:

```yaml
soltrannet:
  runtime: local
  model_id: eos6oli_soltrannet_v1
  model_asset_hash: recorded-at-image-build
  prediction_timeout_seconds: 30

molgpka:
  runtime: local
  model_id: molgpka_gcn_ghcr_acafcb3
  model_asset_hash: recorded-at-image-build
  prediction_timeout_seconds: 60
```

Migration steps:

1. Add the external Docker runtime and tests in this implementation round.
2. Add an official verifier image Dockerfile in a later image-focused round.
3. During image build, install or copy SolTranNet and MolGpKa runtimes into the
   image and record model asset hashes.
4. Add local runtime implementations beside the external Docker implementations.
5. Run the same backend tests against both runtime implementations with mocked
   model calls.
6. Add live image smoke tests that execute property scripts inside the official
   image with stdin JSON payloads.
7. Switch published verifier specs from `runtime: external_docker` to
   `runtime: local`.
8. Document `external_docker` as a development-only fallback after official
   image support is stable.

## Acceptance Criteria

The implementation plan that follows this design should be considered complete
when:

- SolTranNet and MolGpKa backend modules exist under `src/verifiers/backends/`.
- Four property scripts exist under `src/verifiers/physchem/`.
- The property scripts can be executed through `run_verification_script`.
- Default unit tests pass without Docker Desktop or registry access.
- Opt-in live Docker smoke tests pass on a machine with the two validated images
  available.
- Environment check scripts print structured JSON diagnostics.
- Documentation describes the runtime requirements and migration path.
- No new formal track is registered.
- No new task pack is added.
