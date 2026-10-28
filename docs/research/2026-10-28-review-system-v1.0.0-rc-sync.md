# Review system v1.0.0-rc synchronization

Date: 2026-10-28 (Asia/Shanghai).

## Deployment

- Benchmark release: `v1.0.0-rc` / Python package version `1.0.0rc1`.
- Canonical benchmark source: `c4a705a06f8e5e7310a8ac40e81b7612caead055`.
- Review deployment source: `333198d6972b165663e5f764852a53304e8f56df`.
- Production image: `vgb-review-system:v1.0.0-rc-333198d`.
- Retained rollback image: `vgb-review-system:v0.10.0-20260922`.
- Release command: `REVIEW_ROLLBACK_TAG=v0.10.0-20260922 ./review_system/scripts/pipeline.sh release --tag v1.0.0-rc-333198d`.
- Pre-deployment encrypted backup: `review_system/backups/vgb-review-20261028T153330Z.tar.gz.enc`, with adjacent SHA-256 file. Neither backup nor credentials are committed.

Both distribution archives match `releases/v1.0.0-rc/manifest.json`.
All 158 package payload files in the wheel match the deployed checkout's
`src/verifier_grounded_benchmark/` files byte for byte. The benchmark source
does not differ from the release tag. The only deployment fix updates an
obsolete review test's expected version from `0.10.0` to `1.0.0rc1`.

The latest accepted local release was used. A remote tag query failed because
the GitHub TLS connection could not be established; remote freshness was not
verified. No GitHub/PyPI publication or Git merge was performed.

## Database update

The container startup applied the existing Alembic migration `0003 -> 0004`.
This removes the redundant track `display_name` column. The migration was
also verified on a temporary copy of the production database before the
deployment completed.

The existing `sync_catalog` application function created snapshot **9** and
the application's active-snapshot selection now returns it. Repeating the
sync returns the same snapshot without creating a duplicate.

Fingerprint: `995eb1e05e8ba67d653abb7c0e35b62277a99ad2af2242d5c14a90dffa3952b4`.

| Track | Version | Tasks |
| --- | --- | ---: |
| open_generation_rdkit | 1.0.0rc1 | 10 |
| open_generation_xtb | 1.0.0rc1 | 20 |
| property_calculation_advanced | 1.0.0rc1 | 19 |
| property_calculation_basic | 1.0.0rc1 | 51 |
| Total | | 100 |

The previous snapshot remains stored with its 105 tasks. Historical snapshots
and review records were not rewritten to match the new release. The existing
comment targets an unchanged task ID; shared files have no task-specific links.

## Verification

- Review pipeline: 32 tests passed; frontend production build passed.
- All 100 stored task fingerprints and JSON fields (`data`, `view`, `scoring`,
  `schema`, `attachments`) match the running image's catalog.
- Track endpoint function returns snapshot 9 and the counts above.
- SQLite integrity check: `ok`; foreign-key check: no violations.
- Pre/post row hashes match for 4 users, 1 comment, 7 shared files, 8 historical
  snapshots and 840 historical snapshot tasks. Draft, draft revision,
  attachment and review event tables remain empty.
- Pipeline verification passed: live HTTP health and frontend root return
  successfully; port 8000 remains bound to `127.0.0.1`.
- Docker reports the new container healthy; startup logs confirm migration
  completion without application errors.

## Rollback considerations

Retain the old image and encrypted pre-deployment backup together. The old
application expects the `display_name` column removed by migration 0004, so an
image-only rollback is insufficient. A full rollback must coordinate the old
image with the pre-deployment database, or separately verify a schema downgrade
and snapshot selection. Back up any new review activity before restoring an
older database. No rollback or restoration was executed during this update.
