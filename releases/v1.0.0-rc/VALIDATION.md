# v1.0.0-rc local release acceptance

Date: 2026-10-28. Scope: local Benchmark Python artifacts and Git tag only.
Source: c4a705a06f8e5e7310a8ac40e81b7612caead055. Python version: 1.0.0rc1; tag: v1.0.0-rc.
Source tree: 53bc6992ad1be7d60e0513e858fc6d076ad35399.

## Outcome

Accepted for the owner-authorized local delivery. No upload, public licensing
decision, review-system change, or production deployment was performed.
All four tracks provide no public sample answers. Sample files and the
Track.sample_answers() / TrackDefinition.sample_answers_path API are removed.
Development regression inputs are not included in wheel or sdist.

## Executed evidence

| Check | Result |
| --- | --- |
| Core suite | 710 passed, 15 skipped, one existing CIF formula-key warning; 70.28 seconds. |
| Focused removal checks | 67 passed, including exclusions, installed-wheel execution and explicit xTB input. |
| Ruff / lock / whitespace | Passed for src, tests and scripts; lock checked offline. |
| Clean Python 3.12 core environment | 65 packages; dependency consistency and core check passed without optional ASE/materials groups. |
| Installed exact wheel | Ran outside checkout; four tracks loaded with 100 tasks and no sample API/resources. |
| User-owned answer workflow | Executed documented prompt export; supplied regression inputs as the caller; report check passed. |
| Property evaluator | All 51 Basic and 19 Advanced gold round trips scored 1.0; not independent scientific recalculation. |
| RDKit evaluator | All 10 development regression inputs scored with complete coverage and no evaluator errors. |
| CLI failures | Actual missing module and forced timeout returned 2 and retained JSON reports. |
| Overflow handling | One huge integer scored 0; the other 50 valid rows remained full credit. |
| Advanced 002 | Field scores [1,1,0] produced 0.5 as documented. |
| Scientific resources | 52 SMILES, six pairs, eight CIFs and one XYZ passed relevant checks; inputs present in prompts. |
| Numeric boundaries | 69 numeric fields checked at gold, upper half-width and upper zero boundary. |
| xTB / CREST | Nine explicit regression inputs passed; exact wheel also passed one xTB input. |
| Construction | Two builds from identical source/epoch produced identical archive SHA-256. |
| Distribution boundary | No public sample files, regression JSONL, review_system, retirement backups or calibration directory in either archive. |
| Frozen base | Scientific YAML unchanged except pack version; v0.10.0 artifacts match their manifest. |

## Artifacts

| Artifact | SHA-256 |
| --- | --- |
| verifier_grounded_benchmark-1.0.0rc1-py3-none-any.whl | 51e39ef4a50f47c5a5686042d0ef8924c0c44c752f43e15bb3199b07552dd56d |
| verifier_grounded_benchmark-1.0.0rc1.tar.gz | a48782e260fc88b325c3bbb1b3e06aba3435b1e2ee99ec7997933fdbc72b4444 |

The archives contain 159 matching package
payload files. Payload digest: 27cd251ce62448cdaea4f32f8dd6a0f8c6af02e93641d870267007df6b9cd21f.
The tag identifies source; these post-build acceptance materials are committed
separately, following the repository release workflow.

## Reproduction commands

```bash
.venv/bin/python -m pytest tests -q -ra --durations=15
.venv/bin/ruff check src tests scripts
uv lock --check --offline
.venv/bin/python scripts/validation/check_xtb_xyz_samples.py --answers tests/fixtures/open_generation_xtb_regression_answers.jsonl
uv pip install --no-deps --python /path/to/isolated/python dist/verifier_grounded_benchmark-1.0.0rc1-py3-none-any.whl
```

The live regression command is for development checkouts; those inputs are not
distributed. Consumers provide their own answers. The README describes prompt
export and scoring. Build preflight refuses occupied release paths; use fresh
destinations for reproducibility checks rather than overwriting this release.

## Limits and historical observations

The nine xTB inputs do not cover eleven other formal tasks. Independent gold
recalculation, repeated CREST stability and cross-platform equivalence are not
established. Seven optional live tests and eight private calibration tests were
skipped. Licensing remains outside the owner's local-build request.

Older local dist files for v0.5.0, v0.6.0 and v0.8.0 do not match their manifests.
They were not modified by this work; the observation is recorded separately.
It does not apply to the verified v0.10.0 base.

The preliminary task-created RC with samples was archived before rebuilding,
under ignored build/rc-before-public-sample-removal, retaining its Git object in
refs/archive/v1.0.0-rc-with-samples. It was not published. Historical release tags
were not moved.
