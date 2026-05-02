#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

CERT_DIR="$PROJECT_ROOT/Runtime/localprod/certs"
CERT_FILE="$CERT_DIR/faimatrix.localhost.pem"
KEY_FILE="$CERT_DIR/faimatrix.localhost-key.pem"

mkdir -p "$CERT_DIR"

if command -v mkcert >/dev/null 2>&1; then
  mkcert -cert-file "$CERT_FILE" -key-file "$KEY_FILE" \
    faimatrix.localhost localhost 127.0.0.1 ::1
  echo "Generated local production certificate with mkcert."
  exit 0
fi

TMP_CONF="$CERT_DIR/openssl.localprod.cnf"
cat >"$TMP_CONF" <<'EOF'
[req]
default_bits = 4096
prompt = no
default_md = sha256
distinguished_name = dn
x509_extensions = v3_req

[dn]
CN = faimatrix.localhost

[v3_req]
subjectAltName = @alt_names
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = faimatrix.localhost
DNS.2 = localhost
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

openssl req -x509 -nodes -days 825 -newkey rsa:4096 \
  -keyout "$KEY_FILE" \
  -out "$CERT_FILE" \
  -config "$TMP_CONF"

chmod 600 "$KEY_FILE"
rm -f "$TMP_CONF"
echo "Generated local production certificate with OpenSSL."
