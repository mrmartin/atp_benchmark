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

## 1b. Relocate the system **containerd** root to `/mnt/nvme2/containerd`

**Why.** Docker on this host runs against the system containerd (`dockerd ... --containerd=/run/containerd/containerd.sock`). Even with Docker's `data-root` on `/mnt/nvme2`, the **containerd snapshotter** unpacks image layers to `/var/lib/containerd/io.containerd.snapshotter.v1.overlayfs/`. During parallel image builds this filled `/` to 96 % and crashed the session on 2026-05-07. Relocating containerd's root prevents recurrence.

**Steps:**

```bash
# Stop docker + containerd
sudo systemctl stop docker docker.socket containerd

# Create the new root
sudo mkdir -p /mnt/nvme2/containerd

# Patch /etc/containerd/config.toml (or create it if missing)
sudo install -m 0644 /dev/stdin /etc/containerd/config.toml <<'EOF'
version = 2
root = "/mnt/nvme2/containerd"
state = "/run/containerd"
EOF

# Optionally migrate the existing snapshots; otherwise let them be re-pulled.
# sudo rsync -aHAX /var/lib/containerd/ /mnt/nvme2/containerd/ && sudo rm -rf /var/lib/containerd

# Start containerd then docker
sudo systemctl start containerd
sudo systemctl start docker

# Verify: containerd's root in its config
sudo crictl info 2>&1 | grep -i 'root\|state' || ctr version >/dev/null 2>&1 && echo "containerd is up"
ls -la /var/lib/containerd /mnt/nvme2/containerd
```

After this, every `docker build` writes both image layers (Docker `data-root`) and snapshotter layers (containerd `root`) onto `/mnt/nvme2`.

## 2. (Optional) Install `gh` if you ever want me to manage PRs

The current workflow only uses `git push`, so `gh` is not required. If you want it:

```bash
sudo apt-get install -y gh
gh auth login
```

## 3. (Optional) Pin a local `loogle` binary

`lean-interact` can drive `loogle` if it's available on `$PATH`. The version that ships inside `mathlib` works; the harness fetches it transparently. If it doesn't, install the standalone binary from https://github.com/nomeata/loogle.
