#!/bin/sh
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
review_dir=$(dirname "$script_dir")
production_env="$review_dir/.env.production"
sealtun_env="$review_dir/.env.sealtun"

if [ -e "$production_env" ] || [ -e "$sealtun_env" ]; then
  echo "Secret files already exist; refusing to overwrite them" >&2
  exit 1
fi

admin_password=$(openssl rand -hex 16)
secret_key=$(openssl rand -hex 32)
gateway_password=$(openssl rand -hex 16)
backup_password=$(openssl rand -hex 32)

umask 077
{
  printf '%s\n' 'REVIEW_ENVIRONMENT=production'
  printf '%s\n' 'REVIEW_ADMIN_USER=admin'
  printf 'REVIEW_ADMIN_PASSWORD=%s\n' "$admin_password"
  printf 'REVIEW_SECRET_KEY=%s\n' "$secret_key"
  printf '%s\n' 'REVIEW_COOKIE_SECURE=true'
  printf '%s\n' 'REVIEW_AUTO_CREATE_DB=false'
  printf '%s\n' 'REVIEW_DATA_DIR=/app/review_system/data'
  printf '%s\n' 'REVIEW_ALLOWED_ORIGINS='
  printf '%s\n' 'REVIEW_LOGIN_FAILURE_LIMIT=5'
  printf '%s\n' 'REVIEW_LOGIN_WINDOW_MINUTES=15'
  printf 'REVIEW_IMAGE_TAG=%s\n' "$(git -C "$review_dir/.." rev-parse --short HEAD)"
} > "$production_env"
printf 'SEALTUN_BASIC_AUTH_PASSWORD=%s\n' "$gateway_password" > "$sealtun_env"

if command -v security >/dev/null 2>&1; then
  security add-generic-password -U -a "$(id -un)" -s vgb-review-backup -w "$backup_password" >/dev/null
else
  echo "macOS Keychain is required to store the backup passphrase" >&2
  exit 1
fi

echo "Created protected production, Sealtun, and backup secrets."
echo "Read the two .env files locally when distributing credentials; do not commit them."
