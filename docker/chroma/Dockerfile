FROM chromadb/chroma:1.5.9

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 chroma \
    && mkdir -p /data \
    && chown -R chroma:chroma /data

USER chroma
