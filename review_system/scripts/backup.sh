#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
review_dir=$(dirname "$script_dir")
data_dir=${REVIEW_HOST_DATA_DIR:-"$review_dir/data"}
backup_dir=${REVIEW_BACKUP_DIR:-"$review_dir/backups"}
database="$data_dir/review.db"

if [ ! -f "$database" ]; then
  echo "Review database not found: $database" >&2
  exit 1
fi

mkdir -p "$backup_dir"
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
work_dir=$(mktemp -d "${TMPDIR:-/tmp}/vgb-review-backup.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT INT TERM

sqlite3 "$database" ".timeout 5000" ".backup '$work_dir/review.db'"
sqlite3 "$work_dir/review.db" "PRAGMA integrity_check;" | grep -qx ok
if [ -d "$data_dir/attachments" ]; then
  cp -R "$data_dir/attachments" "$work_dir/attachments"
fi

archive="$backup_dir/vgb-review-$timestamp.tar.gz"
tar -C "$work_dir" -czf "$archive" .
passphrase=${REVIEW_BACKUP_PASSPHRASE:-}
if [ -z "$passphrase" ] && command -v security >/dev/null 2>&1; then
  passphrase=$(security find-generic-password -a "$(id -un)" -s vgb-review-backup -w 2>/dev/null || true)
fi
if [ -z "$passphrase" ]; then
  echo "Set REVIEW_BACKUP_PASSPHRASE or create the vgb-review-backup Keychain entry" >&2
  rm -f "$archive"
  exit 1
fi
export REVIEW_BACKUP_PASSPHRASE="$passphrase"
encrypted="$archive.enc"
openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -in "$archive" -out "$encrypted" -pass env:REVIEW_BACKUP_PASSPHRASE
rm -f "$archive"
shasum -a 256 "$encrypted" > "$encrypted.sha256"
find "$backup_dir" -type f -name 'vgb-review-*' -mtime +7 -delete
echo "$encrypted"
