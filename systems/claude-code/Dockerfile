# Claude Code system runner.
# Auth via host-mounted ~/.claude/ + ~/.claude.json (subscription, not API key).

FROM atp-harness:latest

USER root
ENV DEBIAN_FRONTEND=noninteractive \
    NODE_VERSION=20
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/* \
    && npm install -g @anthropic-ai/claude-code

USER agent
WORKDIR /workspace
CMD ["bash"]
