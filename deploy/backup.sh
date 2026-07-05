#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="${APP_DIR:-/srv/nishimuraya/app}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/nishimuraya}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
PYTHON_BIN="${PYTHON_BIN:-${APP_DIR}/.venv/bin/python}"

timestamp="$(date '+%Y%m%d-%H%M%S')"
database_path="${APP_DIR}/db.sqlite3"
database_backup="${BACKUP_DIR}/db-${timestamp}.sqlite3"
media_backup="${BACKUP_DIR}/media-${timestamp}.tar.gz"
checksum_file="${BACKUP_DIR}/SHA256SUMS-${timestamp}"

if [[ ! -f "${database_path}" ]]; then
    echo "Database not found: ${database_path}" >&2
    exit 1
fi

install -d -m 0750 "${BACKUP_DIR}"

"${PYTHON_BIN}" - "${database_path}" "${database_backup}" <<'PY'
import sqlite3
import sys

source_path, destination_path = sys.argv[1:3]
source = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
destination = sqlite3.connect(destination_path)
try:
    source.backup(destination)
finally:
    destination.close()
    source.close()
PY

chmod 0600 "${database_backup}"
checksum_targets=("${database_backup}")

if [[ -d "${APP_DIR}/media" ]]; then
    tar -C "${APP_DIR}" -czf "${media_backup}" media
    chmod 0600 "${media_backup}"
    checksum_targets+=("${media_backup}")
fi

sha256sum "${checksum_targets[@]}" > "${checksum_file}"
chmod 0600 "${checksum_file}"

find "${BACKUP_DIR}" -maxdepth 1 -type f \
    \( -name 'db-*.sqlite3' -o -name 'media-*.tar.gz' -o -name 'SHA256SUMS-*' \) \
    -mtime "+${RETENTION_DAYS}" -delete

echo "Backup completed: ${timestamp}"
