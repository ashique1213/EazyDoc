#!/usr/bin/env bash
# Generates self-signed SSL certificates for Staging HTTPS testing
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERTS_DIR="${SCRIPT_DIR}/../docker/nginx/certs"
mkdir -p "${CERTS_DIR}"

CRT_PATH="${CERTS_DIR}/staging.crt"
KEY_PATH="${CERTS_DIR}/staging.key"

if [ -f "${CRT_PATH}" ] && [ -f "${KEY_PATH}" ]; then
  echo "Staging SSL certificates already exist in ${CERTS_DIR}."
  exit 0
fi

if command -v openssl >/dev/null 2>&1; then
  echo "Generating self-signed SSL certificates for staging with OpenSSL..."
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout "${KEY_PATH}" \
    -out "${CRT_PATH}" \
    -subj "/C=IN/ST=Karnataka/L=Bangalore/O=EazyDoc Healthcare/OU=Staging/CN=staging.eazydoc.internal"
else
  echo "OpenSSL not found. Generating self-signed SSL certificates with Python cryptography..."
  python "${SCRIPT_DIR}/generate_staging_certs.py"
fi

echo "Staging certificates successfully created:"
echo "  Certificate: ${CRT_PATH}"
echo "  Private Key: ${KEY_PATH}"
