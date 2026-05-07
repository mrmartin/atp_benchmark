# atp-harness base image
# - Python 3.12 + ripgrep + git
# - elan + Lean v4.27.0 (matches harness/lean-project/lean-toolchain)
# - the atp-mcp-lean MCP server (pre-installed from the repo)
#
# All heavy artifacts (.lake/, weights, transcripts) live on /mnt/nvme2 and are
# bind-mounted at runtime, not baked into the image. Build context is the repo
# root: `docker build -t atp-harness:latest -f harness/Dockerfile .`

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates git ripgrep jq build-essential \
    && rm -rf /var/lib/apt/lists/*

# elan + Lean toolchain (cached layer; bumping the pin invalidates this layer)
ENV ELAN_HOME=/root/.elan \
    PATH=/root/.elan/bin:/usr/local/bin:/usr/bin:/bin
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
        | sh -s -- -y --default-toolchain leanprover/lean4:v4.27.0 --no-modify-path \
    && elan toolchain install leanprover/lean4:v4.27.0 \
    && lean --version

# Pre-install the MCP Lean server (lean-interact + Anthropic MCP SDK)
COPY harness/mcp-lean-server /opt/mcp-lean-server
RUN pip install /opt/mcp-lean-server

WORKDIR /workspace
CMD ["bash"]
