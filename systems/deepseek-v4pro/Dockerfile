# DeepSeek V4 Pro via OpenCode (OpenRouter backend).
# Auth via env_file (.env) at compose runtime.

FROM atp-harness:latest

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    NODE_VERSION=20
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    # Pin to v1.14.24 per the experiment design.
    && npm install -g opencode-ai@1.14.24

USER agent
WORKDIR /workspace
CMD ["bash"]
