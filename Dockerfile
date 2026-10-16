# CATWOMAN deployment wrapper for the unmodified official Nexora binaries.
FROM debian:bookworm-slim AS fetch

ARG NEXORA_VERSION=0.0.4
ARG TARGETARCH=amd64

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    test "$NEXORA_VERSION" = "0.0.4"; \
    case "$TARGETARCH" in \
      amd64) \
        panel_sha='ad7e60b34a93cb3d5dbd28a61ff3e4014c6b8e8be7dac717b68324256b621521'; \
        node_sha='fa36d9601c6d8fd75fe35206652caa193c4981f25689c11e6414d92a3162bc89' ;; \
      arm64) \
        panel_sha='6daeace01be843391c6782b26f098e98be73ed2afee23c99c3125b6d8bb53b9c'; \
        node_sha='48b9547ccb0c041aefaaa231356d43185c28a714d1e3abf9f7468ef5fb8db94a' ;; \
      *) echo "Unsupported architecture: $TARGETARCH (use amd64 or arm64)" >&2; exit 1 ;; \
    esac; \
    curl -fL --retry 4 --retry-all-errors \
      -o /tmp/panel.tar.gz \
      "https://github.com/Nexora-VPN/panel/releases/download/v${NEXORA_VERSION}/nexora-panel-linux-${TARGETARCH}.tar.gz"; \
    curl -fL --retry 4 --retry-all-errors \
      -o /tmp/node.tar.gz \
      "https://github.com/Nexora-VPN/node/releases/download/v${NEXORA_VERSION}/nexora-node-linux-${TARGETARCH}.tar.gz"; \
    echo "${panel_sha}  /tmp/panel.tar.gz" | sha256sum -c -; \
    echo "${node_sha}  /tmp/node.tar.gz" | sha256sum -c -; \
    mkdir -p /tmp/panel /tmp/node /opt/nexora; \
    tar -xzf /tmp/panel.tar.gz -C /tmp/panel; \
    tar -xzf /tmp/node.tar.gz -C /tmp/node; \
    install -m 0755 "$(find /tmp/panel -type f -name nexora-panel -print -quit)" /opt/nexora/nexora-panel; \
    install -m 0755 "$(find /tmp/node -type f -name nexora-node -print -quit)" /opt/nexora/nexora-node; \
    /opt/nexora/nexora-panel --version; \
    /opt/nexora/nexora-node --version

FROM debian:bookworm-slim

LABEL org.opencontainers.image.title="CATWOMAN Nexora Railway Wrapper" \
      org.opencontainers.image.description="Single-service Railway runtime wrapper for official, unmodified Nexora panel and node" \
      org.opencontainers.image.source="https://github.com/catwomanZ/nexora" \
      org.opencontainers.image.version="0.0.4-wrapper1" \
      org.opencontainers.image.licenses="LicenseRef-Nexora-Proprietary"

RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ca-certificates curl gettext-base nginx python3 supervisor tzdata \
 && rm -rf /var/lib/apt/lists/* \
 && rm -f /etc/nginx/sites-enabled/default

COPY --from=fetch /opt/nexora/ /opt/nexora/
COPY app/bootstrap.py /usr/local/lib/catwoman/bootstrap.py
COPY docker-entrypoint.sh /usr/local/bin/catwoman-entrypoint
COPY config/nginx.conf.template /etc/catwoman/nginx.conf.template
COPY config/proxy-common.conf /etc/catwoman/proxy-common.conf
COPY config/supervisord.conf /etc/catwoman/supervisord.conf

RUN chmod 0755 /usr/local/bin/catwoman-entrypoint /usr/local/lib/catwoman/bootstrap.py \
 && mkdir -p /data/panel /data/node/certs /data/bootstrap /run/catwoman

ENV PORT=8080 \
    TZ=Asia/Tehran \
    CATWOMAN_ADMIN_USER=admin \
    CATWOMAN_PANEL_PORT=12095 \
    CATWOMAN_NODE_PORT=62050 \
    CATWOMAN_INBOUND_PORT=10085 \
    CATWOMAN_WS_PATH=/ws \
    CATWOMAN_DATA_DIR=/data \
    PANEL_BIN=/opt/nexora/nexora-panel \
    NODE_BIN=/opt/nexora/nexora-node

# Persistence is provided by a Railway Volume mounted at /data.
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
  CMD curl -fsS "http://127.0.0.1:${PORT:-8080}/healthz" >/dev/null || exit 1

ENTRYPOINT ["/usr/local/bin/catwoman-entrypoint"]
