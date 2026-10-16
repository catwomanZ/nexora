#!/usr/bin/env python3
"""Bootstrap only CATWOMAN-owned Nexora resources through Nexora's public API."""

from __future__ import annotations

import base64
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


PANEL_PORT = int(os.getenv("CATWOMAN_PANEL_PORT", "12095"))
NODE_PORT = int(os.getenv("CATWOMAN_NODE_PORT", "62050"))
INBOUND_PORT = int(os.getenv("CATWOMAN_INBOUND_PORT", "10085"))
WS_PATH = os.getenv("CATWOMAN_WS_PATH", "/ws")
DOMAIN = os.getenv("CATWOMAN_DOMAIN_RESOLVED", "localhost")
ADMIN_USER = os.getenv("CATWOMAN_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("CATWOMAN_ADMIN_PASSWORD", "admin")
DATA_DIR = Path(os.getenv("CATWOMAN_DATA_DIR", "/data"))
NODE_BIN = os.getenv("NODE_BIN", "/opt/nexora/nexora-node")
PANEL_BASEPATH = "panel"
API_ROOT = f"http://127.0.0.1:{PANEL_PORT}/{PANEL_BASEPATH}/api"

NODE_NAME = "CATWOMAN"
INBOUND_TAG = "catwoman-ws"
TEMPLATE_NAME = "CATWOMAN"
FRONT_LABEL = "CATWOMAN Railway TLS"


class APIError(RuntimeError):
    pass


class API:
    def __init__(self) -> None:
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        timeout: float = 15,
    ) -> Any:
        data = None
        headers = {"Host": DOMAIN, "Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload, separators=(",", ":")).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            API_ROOT + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with self.opener.open(req, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise APIError(f"{method} {path}: HTTP {exc.code}: {body[:500]}") from exc
        except OSError as exc:
            raise APIError(f"{method} {path}: {exc}") from exc
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw.decode("utf-8", "replace")

    def get(self, path: str) -> Any:
        return self.request("GET", path)

    def post(self, path: str, payload: dict[str, Any] | None = None) -> Any:
        return self.request("POST", path, payload)

    def put(self, path: str, payload: dict[str, Any]) -> Any:
        return self.request("PUT", path, payload)

    def login(self) -> None:
        self.post("/login", {"username": ADMIN_USER, "password": ADMIN_PASSWORD})


def log(message: str) -> None:
    print(f"[catwoman] {message}", flush=True)


def atomic_write(path: Path, content: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content)
    os.chmod(temporary, mode)
    temporary.replace(path)


def wait_for_panel(seconds: int = 90) -> API:
    deadline = time.monotonic() + seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        api = API()
        try:
            api.login()
            return api
        except Exception as exc:  # readiness includes authentication and schema availability
            last_error = exc
            time.sleep(1)
    raise APIError(f"panel did not become ready: {last_error}")


def update_node(api: API, node: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "name": NODE_NAME,
        "address": "127.0.0.1",
        "port": NODE_PORT,
        "remark": "CATWOMAN Railway",
        "linkAddress": DOMAIN,
        "templateId": node.get("templateId"),
        "multiplier": node.get("multiplier") or 1,
        "limitBytes": node.get("limitBytes") or 0,
        "limitPeriod": node.get("limitPeriod") or "",
        "limitStartDay": node.get("limitStartDay") or 1,
        "limitStartMonth": node.get("limitStartMonth") or 1,
        "fallbackCertMode": node.get("fallbackCertMode") or "",
        "fallbackCertId": node.get("fallbackCertId"),
    }
    return api.put(f"/nodes/{node['id']}", payload)


def ensure_node(api: API) -> dict[str, Any]:
    nodes = api.get("/nodes") or []
    node = next((item for item in nodes if item.get("name") == NODE_NAME), None)
    if node is None:
        payload = {
            "name": NODE_NAME,
            "address": "127.0.0.1",
            "port": NODE_PORT,
            "remark": "CATWOMAN Railway",
            "linkAddress": DOMAIN,
            "templateId": None,
            "multiplier": 1,
            "limitBytes": 0,
            "limitPeriod": "",
            "limitStartDay": 1,
            "limitStartMonth": 1,
            "fallbackCertMode": "",
            "fallbackCertId": None,
        }
        node = api.post("/nodes", payload)
        log(f"created Nexora node {node['id']}")
    else:
        node = update_node(api, node)
        log(f"reconciled Nexora node {node['id']}")
    api.post(f"/nodes/{node['id']}/enabled", {"enabled": True})
    return node


def ensure_node_certificates(api: API) -> None:
    response = api.get("/mtls/certificate")
    certificate = response.get("certificate") if isinstance(response, dict) else None
    if not certificate:
        raise APIError("panel did not return its mTLS CA certificate")

    cert_dir = DATA_DIR / "node" / "certs"
    cert_dir.mkdir(parents=True, exist_ok=True)
    atomic_write(cert_dir / "panel_ca.pem", certificate.rstrip() + "\n", 0o600)

    cert_path = cert_dir / "ssl_cert.pem"
    key_path = cert_dir / "ssl_key.pem"
    if cert_path.is_file() and key_path.is_file():
        return
    cert_path.unlink(missing_ok=True)
    key_path.unlink(missing_ok=True)
    subprocess.run([NODE_BIN, "gencerts", "-dir", str(cert_dir)], check=True)
    if not cert_path.is_file() or not key_path.is_file():
        raise RuntimeError("nexora-node gencerts did not create both certificate files")
    os.chmod(cert_path, 0o600)
    os.chmod(key_path, 0o600)
    log("generated official Nexora node certificate pair")


def desired_inbound() -> dict[str, Any]:
    return {
        "tag": INBOUND_TAG,
        "type": "vless",
        "remark": "CATWOMAN Railway",
        "config": {
            "type": "vless",
            "listen": "127.0.0.1",
            "listen_port": INBOUND_PORT,
            "transport": {"type": "ws", "path": WS_PATH},
        },
        "useNodeCert": False,
        "certificateId": None,
        "clientConfig": {
            "server": DOMAIN,
            "server_port": 443,
            "transport": {
                "type": "ws",
                "path": WS_PATH,
                "headers": {"Host": DOMAIN},
            },
        },
        # Railway terminates TLS. Only publish the TLS front link, never the plain internal link.
        "frontedOnly": True,
    }


def ensure_inbound(api: API) -> dict[str, Any]:
    inbounds = api.get("/inbounds") or []
    inbound = next((item for item in inbounds if item.get("tag") == INBOUND_TAG), None)
    payload = desired_inbound()
    if inbound is None:
        inbound = api.post("/inbounds", payload)
        log(f"created VLESS/WebSocket inbound {inbound['id']}")
    else:
        inbound = api.put(f"/inbounds/{inbound['id']}", payload)
        log(f"reconciled VLESS/WebSocket inbound {inbound['id']}")
    return inbound


def ensure_front(api: API, node: dict[str, Any], inbound: dict[str, Any]) -> dict[str, Any]:
    fronts = api.get("/fronts") or []
    front = next((item for item in fronts if item.get("label") == FRONT_LABEL), None)
    payload = {
        "label": FRONT_LABEL,
        "address": DOMAIN,
        "port": 443,
        "sni": DOMAIN,
        "hostHeader": DOMAIN,
        "alpn": ["http/1.1"],
        "fingerprint": "chrome",
        "allowInsecure": False,
        "clientIpHeader": "X-Forwarded-For",
        "originNodeId": node["id"],
        "enabled": True,
        "sort": 0,
        "inboundIds": [inbound["id"]],
    }
    if front is None:
        front = api.post("/fronts", payload)
        log(f"created Railway TLS front {front['id']}")
    else:
        front = api.put(f"/fronts/{front['id']}", payload)
        log(f"reconciled Railway TLS front {front['id']}")
    for warning in front.get("warnings") or []:
        log(f"front warning: {warning}")
    return front


def template_payload(template: dict[str, Any] | None, inbound_id: int) -> dict[str, Any]:
    template = template or {}

    def ids(key: str) -> list[int]:
        values = template.get(key) or []
        return [item["id"] for item in values if isinstance(item, dict) and "id" in item]

    inbound_ids = ids("inbounds")
    if inbound_id not in inbound_ids:
        inbound_ids.append(inbound_id)
    return {
        "name": TEMPLATE_NAME,
        "remark": template.get("remark") or "CATWOMAN Railway",
        "route": template.get("route"),
        "core": template.get("core"),
        "inboundIds": inbound_ids,
        "outboundIds": ids("outbounds"),
        "endpointIds": ids("endpoints"),
        "ruleSetIds": ids("ruleSets"),
    }


def ensure_template(api: API, inbound: dict[str, Any]) -> dict[str, Any]:
    templates = api.get("/templates") or []
    template = next((item for item in templates if item.get("name") == TEMPLATE_NAME), None)
    payload = template_payload(template, inbound["id"])
    if template is None:
        template = api.post("/templates", payload)
        log(f"created node template {template['id']}")
    else:
        template = api.put(f"/templates/{template['id']}", payload)
        log(f"reconciled node template {template['id']}")
    return template


def setup() -> None:
    api = wait_for_panel()
    node = ensure_node(api)
    ensure_node_certificates(api)
    inbound = ensure_inbound(api)
    template = ensure_template(api, inbound)
    api.put(f"/nodes/{node['id']}/template", {"templateId": template["id"]})
    ensure_front(api, node, inbound)

    marker = {
        "version": 1,
        "domain": DOMAIN,
        "nodeId": node["id"],
        "inboundId": inbound["id"],
        "templateId": template["id"],
        "wsPath": WS_PATH,
    }
    atomic_write(DATA_DIR / "bootstrap" / "state.json", json.dumps(marker, indent=2) + "\n")
    log("Nexora API bootstrap completed")


def websocket_probe(seconds: int = 60) -> None:
    deadline = time.monotonic() + seconds
    key = base64.b64encode(os.urandom(16)).decode()
    request = (
        f"GET {WS_PATH} HTTP/1.1\r\n"
        f"Host: {DOMAIN}\r\n"
        "Connection: Upgrade\r\n"
        "Upgrade: websocket\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Sec-WebSocket-Key: {key}\r\n\r\n"
    ).encode()
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", INBOUND_PORT), timeout=3) as sock:
                sock.sendall(request)
                response = sock.recv(512)
            if response.startswith(b"HTTP/1.1 101"):
                return
            last_error = RuntimeError(response.decode("latin1", "replace")[:200])
        except OSError as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError(f"WebSocket inbound probe failed: {last_error}")


def sync() -> None:
    deadline = time.monotonic() + 120
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            api = wait_for_panel(15)
            nodes = api.get("/nodes") or []
            node = next(item for item in nodes if item.get("name") == NODE_NAME)
            if node.get("status") != "connected":
                raise RuntimeError(f"node status is {node.get('status') or 'unknown'}")
            api.post(f"/nodes/{node['id']}/sync")
            websocket_probe(60)
            log("node connected; VLESS/WebSocket listener returned HTTP 101")
            return
        except Exception as exc:
            last_error = exc
            time.sleep(2)
    raise RuntimeError(f"runtime sync failed: {last_error}")


def main() -> None:
    if not ADMIN_PASSWORD:
        raise SystemExit("CATWOMAN_ADMIN_PASSWORD is required")
    mode = sys.argv[1] if len(sys.argv) > 1 else "setup"
    if mode == "setup":
        setup()
    elif mode == "sync":
        sync()
    else:
        raise SystemExit(f"unknown mode: {mode}")


if __name__ == "__main__":
    main()
