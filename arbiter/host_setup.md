# Host setup (requires sudo — user runs these)

This document lists host-level changes the experiment depends on. The arbiter does **not** apply them automatically; the user runs them after reading.

## 1. Relocate Docker `data-root` to `/mnt/nvme2/docker`

**Why.** Root partition is at 91 % (45 GB free). Docker images for the four services (harness base + three system images) plus build caches will exceed that. `/mnt/nvme2` has 975 GB free.

**Risk.** Restarting `dockerd` stops all running containers. Existing images at `/var/lib/docker` are abandoned (not migrated) — re-pull as needed. Do this **before** building any harness images, so the switch is clean.

**Steps:**

```bash
# Stop docker
sudo systemctl stop docker docker.socket containerd

# Create the new data-root
sudo mkdir -p /mnt/nvme2/docker

# Patch the daemon config (preserves nvidia runtime entry)
sudo install -m 0644 /dev/stdin /etc/docker/daemon.json <<'EOF'
{
  "data-root": "/mnt/nvme2/docker",
  "runtimes": {
    "nvidia": {
      "args": [],
      "path": "nvidia-container-runtime"
    }
  }
}
EOF

# Start docker
sudo systemctl start docker

# Verify
docker info | grep "Docker Root Dir"
# Expect: Docker Root Dir: /mnt/nvme2/docker
```

## 2. (Optional) Install `gh` if you ever want me to manage PRs

The current workflow only uses `git push`, so `gh` is not required. If you want it:

```bash
sudo apt-get install -y gh
gh auth login
```

## 3. (Optional) Pin a local `loogle` binary

`lean-interact` can drive `loogle` if it's available on `$PATH`. The version that ships inside `mathlib` works; the harness fetches it transparently. If it doesn't, install the standalone binary from https://github.com/nomeata/loogle.
