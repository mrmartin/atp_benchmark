# Goedel-Prover-V2 system runner — CPU-only, full bf16 (no quantization).
# 32B bf16 weights ~64 GB; container needs 96+ GB mem_limit at compose time.

FROM atp-harness:latest

USER root
# Torch CPU build (no CUDA needed)
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        torch==2.6.0 \
    && pip install \
        transformers==4.46.0 \
        accelerate \
        sentencepiece \
        tqdm \
        safetensors

# Clone Goedel-Prover-V2 at pinned commit
ARG GOEDEL_COMMIT=2e9036e118464aa96a8bebaf9f5b9d091aa3585c
RUN git clone https://github.com/Goedel-LM/Goedel-Prover-V2.git /opt/goedel-prover-v2 \
    && cd /opt/goedel-prover-v2 \
    && git checkout ${GOEDEL_COMMIT} \
    && chown -R agent:agent /opt/goedel-prover-v2

ENV GOEDEL_HOME=/opt/goedel-prover-v2 \
    HF_HOME=/mnt/nvme2/atp_runs/goedel-v2/hf-cache

USER agent
WORKDIR /workspace
CMD ["bash"]
