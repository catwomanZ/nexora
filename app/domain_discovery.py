#!/usr/bin/env python3
"""Learn the generated Railway hostname from the first public request."""

from __future__ import annotations

import http.server
import os
import re
import subprocess
import threading
from pathlib import Path
from urllib.parse import urlsplit


LISTEN_PORT = int(os.getenv("CATWOMAN_DISCOVERY_PORT", "18090"))
DATA_DIR = Path(os.getenv("CATWOMAN_DATA_DIR", "/data"))
DOMAIN_FILE = Path(os.getenv("CATWOMAN_DOMAIN_FILE", str(DATA_DIR / "bootstrap/public_domain")))
PANEL_BIN = os.getenv("PANEL_BIN", "/opt/nexora/nexora-panel")
PANEL_DIR = os.getenv("CATWOMAN_PANEL_DIR", str(DATA_DIR / "panel"))
DB_PATH = os.getenv("CATWOMAN_DB_PATH", str(DATA_DIR / "panel/nexora.db"))
SUPERVISOR_CONFIG = "/etc/catwoman/supervisord.conf"
BOOTSTRAP = "/usr/local/lib/catwoman/bootstrap.py"

DOMAIN_RE = re.compile(r"[a-z0-9.-]+")
LOCK = threading.Lock()


def log(message: str) -> None:
    print(f"[catwoman-domain] {message}", flush=True)


def normalize_host(raw: str) -> str:
    parsed = urlsplit(raw if "://" in raw else "//" + raw.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if not DOMAIN_RE.fullmatch(host):
        raise ValueError("invalid host")
    return host


def is_railway_domain(host: str) -> bool:
    return host.endswith(".up.railway.app") or host.endswith(".railway.app")


def saved_domain() -> str:
    try:
        return normalize_host(DOMAIN_FILE.read_text().strip())
    except (OSError, ValueError):
        return ""


def run(command: list[str], *, env: dict[str, str] | None = None, timeout: int = 180) -> None:
    subprocess.run(command, env=env, check=True, timeout=timeout)


def supervisor(action: str) -> None:
    run(["/usr/bin/supervisorctl", "-c", SUPERVISOR_CONFIG, action, "nexora-panel"], timeout=45)


def panel_cli(*args: str) -> None:
    env = os.environ.copy()
    env.update(
        {
            "NEXORA_STATE_DIR": PANEL_DIR,
            "NEXORA_DB_DRIVER": "sqlite",
            "NEXORA_DB_DSN": DB_PATH,
        }
    )
    run([PANEL_BIN, *args], env=env, timeout=45)


def atomic_save(host: str) -> None:
    DOMAIN_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = DOMAIN_FILE.with_name(DOMAIN_FILE.name + ".tmp")
    temporary.write_text(host + "\n")
    os.chmod(temporary, 0o600)
    temporary.replace(DOMAIN_FILE)


def configure(host: str) -> None:
    current = saved_domain()
    if current == host:
        return
    if current and current != host:
        # First generated Railway domain wins. A custom-domain change remains an explicit override.
        log(f"ignoring alternate host {host}; active domain is {current}")
        return
    if not is_railway_domain(host):
        log(f"ignoring non-Railway host {host}")
        return

    with LOCK:
        current = saved_domain()
        if current == host:
            return
        if current and current != host:
            return

        log(f"discovered https://{host}; reconciling official Nexora settings")
        stopped = False
        try:
            supervisor("stop")
            stopped = True
            panel_cli("config", "set", "public_address", f"https://{host}")
            panel_cli("config", "set", "web_domain", host)
            panel_cli("config", "set", "sub_domain", host)
            supervisor("start")
            stopped = False

            env = os.environ.copy()
            env.update(
                {
                    "CATWOMAN_DOMAIN_RESOLVED": host,
                    "CATWOMAN_DOMAIN_DISCOVERY_PENDING": "0",
                }
            )
            run(["/usr/bin/python3", BOOTSTRAP, "setup"], env=env)
            run(["/usr/bin/python3", BOOTSTRAP, "sync"], env=env)
            atomic_save(host)
            log(f"automatic domain setup completed for {host}")
        except Exception:
            if stopped:
                try:
                    supervisor("start")
                except Exception:
                    pass
            raise


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CATWOMAN-domain/1"

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        try:
            host = normalize_host(self.headers.get("X-Catwoman-Host", ""))
            configure(host)
        except Exception as exc:
            log(f"domain setup failed: {exc}")
            self.send_response(503)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Retry-After", "3")
            self.end_headers()
            self.wfile.write(b"CATWOMAN domain setup is retrying. Refresh in a few seconds.\n")
            return

        if self.path.startswith("/entry"):
            self.send_response(302)
            self.send_header("Location", "/panel/")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
        else:
            self.send_response(204)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> None:
    server = http.server.ThreadingHTTPServer(("127.0.0.1", LISTEN_PORT), Handler)
    server.daemon_threads = True
    log(f"automatic Railway domain discovery listening on 127.0.0.1:{LISTEN_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
