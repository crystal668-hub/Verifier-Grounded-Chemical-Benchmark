# Release Consistency Validation for v0.1.1

## Decision

Version `0.1.0` was not treated as a formal release. Git history contained no
`v0.1.0` tag, release commit, release manifest, or checksums. The ignored local
artifacts also disagreed with one another, so none of them can identify a
canonical historical task pack.

Current `main` commit `201009d` was selected as the content baseline because it
contains the complete formal inventories: RDKit 11, xTB 18, and
property_calculation 2. Release preparation was committed separately as
`ae481b5ed8eab4207510b9027ad9c24e22839cf5`; this is the unique canonical source
commit for version `0.1.1` and the commit referenced by annotated tag `v0.1.1`.

## Rejected Local Artifacts

The following ignored artifacts existed before the release repair and were
removed. Their differing SHA256 values demonstrate that the local `0.1.0` name
did not identify one release:

| Path | SHA256 |
| --- | --- |
| `dist/verifier_grounded_benchmark-0.1.0-py3-none-any.whl` | `9f7bb96413d8a31f9892cf91f8a1fcba102bbc0d73a73c4b3ed54f04908f0162` |
| `dist/verifier_grounded_benchmark-0.1.0.tar.gz` | `4dc1ab9764ec43a2b6e656a35de4db4e940e6f57f5554bb99ffcbf75287848f1` |
| `build/release-dist/verifier_grounded_benchmark-0.1.0-py3-none-any.whl` | `c100cf5c253acfca3dc61bb5708982cc49c654284bda5b06c7501ba467e911ed` |
| `build/release-dist/verifier_grounded_benchmark-0.1.0.tar.gz` | `084d5a2d0015ed0bbf0e2bc5fcd5a559aabb28cf8c1aab03d982eb3758a2d571` |

## Canonical Artifacts

The release builder sets `SOURCE_DATE_EPOCH` from the canonical commit, builds
wheel and sdist from a clean worktree, and compares every packaged source,
formal task, verifier, and package README byte for byte after normalizing archive
paths. The signed-off artifact hashes, task IDs, source commit, source tree, and
normalized payload hash are stored under `releases/v0.1.1/`.

Validation covers the full source test suite, package build tests, checksum
verification, archive payload equality, and an installed-wheel smoke test run
outside the repository working directory.
