# Validation record

Validation date: 2026-10-16

## Passed locally

- Built the Dockerfile from scratch on linux/amd64.
- Both downloaded archives passed the pinned SHA-256 checks.
- Executables inside the built image reported:
  - `nexora-panel 0.0.4`
  - `nexora-node 0.0.4`
- Fresh persistent-state bootstrap succeeded through the supported Nexora API.
- The panel and node established mTLS and the node reported connected.
- The wrapper-created template activated the VLESS/WebSocket listener.
- `/healthz` returned HTTP 200.
- `/panel/` returned HTTP 200 through nginx.
- Login cookies received `Secure`, `HttpOnly`, and `SameSite=Lax` at nginx.
- `/ws` completed a WebSocket upgrade with HTTP 101.
- A test user received exactly one wrapper-owned link with:
  - `security=tls`
  - `type=ws`
  - `path=/ws`
  - external port `443`
- The subscription endpoint returned the same TLS link.
- Full local data path passed:

  `Xray client -> local TLS edge simulation -> wrapper nginx -> Nexora Node VLESS/WS -> public internet`

- A stop/start with the same mounted `/data` preserved the test user's UUID, subscription ID, node certificate, and node key.
- Changing the configured public domain reconciled the CATWOMAN resources and regenerated the user's link with the new host while preserving the UUID and node certificate.
- First-run initialization accepts the temporary `admin/admin` login; `CATWOMAN_ADMIN_PASSWORD` overrides it on redeploy.
- A second clean-volume test started with no domain environment variable:
  - `/healthz` became ready while runtime sync waited safely.
  - The first direct `/panel/` request with a `*.up.railway.app` host triggered automatic discovery and returned HTTP 200.
  - Nexora's public address, panel domain, subscription domain, node link address, inbound client host, and TLS front were reconciled to the discovered host.
  - The node connected and both the internal and nginx-routed WebSocket probes returned HTTP 101.
  - The discovered hostname was persisted at `/data/bootstrap/public_domain` and survived a fresh container start with the same mounted `/data`.
- Static checks passed for Python, POSIX shell, nginx configuration, branding, and secret scans.

## Live observation

- A Railway deployment returned HTTP 200 from `/healthz` and the panel opened after an explicit domain override was added.
- The automatic no-variable discovery revision has been validated locally but has not yet been exercised on that live Railway deployment.

## Not yet claimed

- No real phone client has connected through a Railway-generated domain.
- No protocol other than the default VLESS/WebSocket path has been validated by this wrapper.
