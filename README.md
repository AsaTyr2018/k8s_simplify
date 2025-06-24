# k8s_simplify

This project provides a framework for deploying and managing Kubernetes clusters on Linux.
It follows a phase-based workflow described in `AGENTS.md`.
The first phase (master node preparation) is now implemented and automatically
runs as part of the `install` command.

## Usage

```bash
# Install a new cluster
python -m k8s_simplify install --name mycluster --master 192.168.1.10 --workers 192.168.1.11 192.168.1.12

# Update cluster
python -m k8s_simplify update --target-version v1.33.0

# Rollback cluster
python -m k8s_simplify rollback
```

The `suplement/` directory contains old helper scripts kept for reference only.
