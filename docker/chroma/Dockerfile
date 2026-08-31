# Refresh: pull chromadb/chroma:1.5.9, inspect its RepoDigests, then review this digest.
FROM chromadb/chroma:1.5.9@sha256:1e0b73a187a28757c572acba508c46f48c9e8b0acaf5c20e6d95cdedce1acdf6

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 chroma \
    && install -d -o chroma -g chroma /data

USER chroma
