#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
review_dir=$(dirname "$script_dir")
root_dir=$(dirname "$review_dir")
compose_file="$review_dir/compose.production.yml"
tag=${REVIEW_IMAGE_TAG:-}
python_bin=${PYTHON_BIN:-}
[ -n "$python_bin" ] || { [ -x "$root_dir/.venv/bin/python" ] && python_bin="$root_dir/.venv/bin/python" || python_bin=python3; }
compose() { docker compose --project-directory "$review_dir" -f "$compose_file" "$@"; }
die() { echo "pipeline: $*" >&2; exit 1; }

current_tag() { git -C "$root_dir" rev-parse --short=12 HEAD; }
require_tag() { [ -n "$tag" ] || tag=$(current_tag); case "$tag" in *[!A-Za-z0-9_.-]*) die "invalid image tag: $tag";; esac; export REVIEW_IMAGE_TAG="$tag"; }
clean_tree() { [ -z "$(git -C "$root_dir" status --porcelain)" ] || die "worktree must be clean for release"; }

test_pipeline() {
  cd "$root_dir"
  command -v "$python_bin" >/dev/null 2>&1 || die "Python executable not found: $python_bin"
  PYTHONPATH="$review_dir/backend${PYTHONPATH:+:$PYTHONPATH}" "$python_bin" -m pytest review_system/tests
  if [ -d "$review_dir/frontend/node_modules" ]; then (cd "$review_dir/frontend" && npm run build); else echo "pipeline: frontend dependencies absent; skipping frontend build"; fi
}
build_image() { require_tag; echo "pipeline: building vgb-review-system:$REVIEW_IMAGE_TAG (commit $(git -C "$root_dir" rev-parse HEAD))"; compose build --pull review-system; }
verify() {
  compose ps --status running --services | grep -qx review-system || die "review-system is not running"
  curl --fail --silent --show-error http://127.0.0.1:8000/healthz >/dev/null
  curl --fail --silent --show-error http://127.0.0.1:8000/ >/dev/null
  compose port review-system 8000 | grep -Eq '^127\.0\.0\.1:' || die "port is not bound to loopback"
  echo "pipeline: verification passed for $REVIEW_IMAGE_TAG"
}
deploy() {
  require_tag
  [ -f "$review_dir/.env.production" ] || die "missing review_system/.env.production"
  [ -x "$script_dir/backup.sh" ] && "$script_dir/backup.sh" >/dev/null || die "backup failed"
  compose up -d --no-build review-system
  i=0; while [ "$i" -lt 30 ]; do if verify >/dev/null 2>&1; then return; fi; i=$((i+1)); sleep 2; done
  die "health check timed out"
}
rollback() { require_tag; [ -n "${REVIEW_ROLLBACK_TAG:-}" ] || die "set REVIEW_ROLLBACK_TAG"; export REVIEW_IMAGE_TAG="$REVIEW_ROLLBACK_TAG"; compose up -d --no-build review-system; verify; }

cmd=${1:-help}; [ "$cmd" = help ] && { echo "usage: $0 {test|build|deploy|verify|rollback|release} [--tag TAG]"; exit 0; }
shift || true
while [ "$#" -gt 0 ]; do case "$1" in --tag) [ "$#" -ge 2 ] || die "--tag requires a value"; tag=$2; shift 2;; *) die "unknown option: $1";; esac; done
case "$cmd" in test) test_pipeline;; build) clean_tree; build_image;; deploy) clean_tree; deploy;; verify) require_tag; verify;; rollback) rollback;; release) clean_tree; test_pipeline; build_image; deploy;; *) die "unknown command: $cmd";; esac
