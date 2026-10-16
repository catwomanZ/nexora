#!/bin/sh
set -eu

umask 077

log() {
  printf '%s\n' "[catwoman] $*"
}

PANEL_BIN="${PANEL_BIN:-/opt/nexora/nexora-panel}"
NODE_BIN="${NODE_BIN:-/opt/nexora/nexora-node}"
DATA_DIR="${CATWOMAN_DATA_DIR:-/data}"
PANEL_PORT="${CATWOMAN_PANEL_PORT:-12095}"
NODE_PORT="${CATWOMAN_NODE_PORT:-62050}"
INBOUND_PORT="${CATWOMAN_INBOUND_PORT:-10085}"
ADMIN_USER="${CATWOMAN_ADMIN_USER:-admin}"
ADMIN_PASSWORD="${CATWOMAN_ADMIN_PASSWORD:-admin}"
PORT="${PORT:-8080}"
TZ="${TZ:-Asia/Tehran}"

if [ "$ADMIN_USER" = "admin" ] && [ "$ADMIN_PASSWORD" = "admin" ]; then
  log "WARNING: using temporary default login admin/admin; change CATWOMAN_ADMIN_PASSWORD in Railway immediately."
fi

raw_domain="${CATWOMAN_DOMAIN:-${RAILWAY_PUBLIC_DOMAIN:-localhost}}"
DOMAIN="$(python3 - "$raw_domain" <<'PY'
import re, sys
from urllib.parse import urlsplit
raw = sys.argv[1].strip()
parsed = urlsplit(raw if "://" in raw else "//" + raw)
host = parsed.hostname or ""
if not host or not re.fullmatch(r"[A-Za-z0-9.-]+", host):
    raise SystemExit("invalid CATWOMAN_DOMAIN/RAILWAY_PUBLIC_DOMAIN")
print(host.lower().rstrip("."))
PY
)"
if [ "$DOMAIN" = "localhost" ]; then
  log "WARNING: no Railway public domain is available yet; generate a domain and redeploy."
fi

export TZ PORT PANEL_BIN NODE_BIN
export CATWOMAN_DATA_DIR="$DATA_DIR"
export CATWOMAN_PANEL_PORT="$PANEL_PORT"
export CATWOMAN_NODE_PORT="$NODE_PORT"
export CATWOMAN_INBOUND_PORT="$INBOUND_PORT"
export CATWOMAN_WS_PATH="${CATWOMAN_WS_PATH:-/ws}"
export CATWOMAN_ADMIN_USER="$ADMIN_USER"
export CATWOMAN_ADMIN_PASSWORD="$ADMIN_PASSWORD"
export CATWOMAN_DOMAIN_RESOLVED="$DOMAIN"

PANEL_DIR="$DATA_DIR/panel"
NODE_DIR="$DATA_DIR/node"
CERT_DIR="$NODE_DIR/certs"
DB_PATH="$PANEL_DIR/nexora.db"
mkdir -p "$PANEL_DIR" "$CERT_DIR" "$DATA_DIR/bootstrap" /run/catwoman
chmod 0700 "$PANEL_DIR" "$NODE_DIR" "$CERT_DIR" "$DATA_DIR/bootstrap" || true

panel_env() {
  env \
    NEXORA_STATE_DIR="$PANEL_DIR" \
    NEXORA_DB_DRIVER=sqlite \
    NEXORA_DB_DSN="$DB_PATH" \
    NEXORA_WEB_LISTEN="127.0.0.1:$PANEL_PORT" \
    "$@"
}

if [ ! -s "$DB_PATH" ]; then
  log "initializing official Nexora panel database"
  panel_env "$PANEL_BIN" migrate -user "$ADMIN_USER" -pass "$ADMIN_PASSWORD"
else
  log "applying official Nexora panel migrations"
  panel_env "$PANEL_BIN" migrate
  # Railway variables are the source of truth for this wrapper's owner login.
  panel_env "$PANEL_BIN" admin reset-password -user "$ADMIN_USER" -pass "$ADMIN_PASSWORD"
fi

set_config() {
  panel_env "$PANEL_BIN" config set "$1" "$2" >/dev/null
}

log "configuring panel origin https://$DOMAIN"
set_config public_address "https://$DOMAIN"
set_config web_basepath panel
set_config web_domain "$DOMAIN"
set_config web_tls_mode none
set_config sub_basepath sub
set_config sub_domain "$DOMAIN"
set_config timezone "$TZ"
set_config trusted_proxies "127.0.0.1/32"

TEMP_PANEL_PID=""
cleanup_temp_panel() {
  if [ -n "$TEMP_PANEL_PID" ] && kill -0 "$TEMP_PANEL_PID" 2>/dev/null; then
    kill "$TEMP_PANEL_PID" 2>/dev/null || true
    wait "$TEMP_PANEL_PID" 2>/dev/null || true
  fi
}
trap 'cleanup_temp_panel; exit 143' INT TERM HUP

log "starting temporary panel for supported API bootstrap"
env \
  NEXORA_STATE_DIR="$PANEL_DIR" \
  NEXORA_DB_DRIVER=sqlite \
  NEXORA_DB_DSN="$DB_PATH" \
  NEXORA_WEB_LISTEN="127.0.0.1:$PANEL_PORT" \
  "$PANEL_BIN" run &
TEMP_PANEL_PID=$!

if ! python3 /usr/local/lib/catwoman/bootstrap.py setup; then
  cleanup_temp_panel
  exit 1
fi

cleanup_temp_panel
TEMP_PANEL_PID=""
trap - INT TERM HUP

export CATWOMAN_PANEL_UPSTREAM_PORT="$PANEL_PORT"
export CATWOMAN_INBOUND_UPSTREAM_PORT="$INBOUND_PORT"
envsubst '${PORT} ${CATWOMAN_PANEL_UPSTREAM_PORT} ${CATWOMAN_INBOUND_UPSTREAM_PORT}' \
  < /etc/catwoman/nginx.conf.template \
  > /run/catwoman/nginx.conf
/usr/sbin/nginx -t -c /run/catwoman/nginx.conf

# Supervisor supports environment expansion for paths and ports through ENV_* values.
export CATWOMAN_PANEL_DIR="$PANEL_DIR"
export CATWOMAN_NODE_DIR="$NODE_DIR"
export CATWOMAN_CERT_DIR="$CERT_DIR"
export CATWOMAN_DB_PATH="$DB_PATH"

log "starting Nexora panel + node behind the CATWOMAN Railway gateway"
exec /usr/bin/supervisord -n -c /etc/catwoman/supervisord.conf
