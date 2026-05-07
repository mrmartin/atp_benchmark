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

# Non-root user matching the host's martin (uid 1000) so bind-mount writes
# (e.g. .lake build artifacts on /mnt/nvme2/atp_runs/lean-build) stay
# owned by the host user. Override at build time with --build-arg if needed.
ARG HOST_UID=1000
ARG HOST_GID=1000
RUN groupadd -g ${HOST_GID} agent || true \
 && useradd  -u ${HOST_UID} -g ${HOST_GID} -m -s /bin/bash agent \
 && mkdir -p /workspace && chown agent:agent /workspace

# Pre-install the MCP Lean server (lean-interact + Anthropic MCP SDK).
COPY harness/mcp-lean-server /opt/mcp-lean-server
RUN pip install /opt/mcp-lean-server

# elan + Lean toolchain installed as the agent user so its toolchain dir is
# under /home/agent/.elan and lean-interact's REPL cache stays writable.
USER agent
ENV ELAN_HOME=/home/agent/.elan \
    PATH=/home/agent/.elan/bin:/usr/local/bin:/usr/bin:/bin
RUN curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh \
        | sh -s -- -y --default-toolchain leanprover/lean4:v4.27.0 --no-modify-path \
    && elan toolchain install leanprover/lean4:v4.27.0 \
    && lean --version

WORKDIR /workspace
CMD ["bash"]
