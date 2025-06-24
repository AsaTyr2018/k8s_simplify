# k8s_simplify

This project provides a framework for deploying and managing Kubernetes clusters on Linux.
It follows a phase-based workflow described in `AGENTS.md`.
Phases 1-4 (master preparation, installation, verification and worker
deployment) are implemented and run automatically as part of the `install`
command. Phase 5 performs a health check to ensure all nodes report `Ready`
status after joining the cluster. Phase 6 prints final access information and
can optionally export it to a file using the `--export-file` option.

## Usage

```bash
# Install a new cluster
python -m k8s_simplify install --name mycluster --master 192.168.1.10 --workers 192.168.1.11 192.168.1.12 \
    --export-file cluster_info.txt

# Update cluster
python -m k8s_simplify update --master 192.168.1.10 \
    --workers 192.168.1.11 192.168.1.12 \
    --user root --password mypass \
    --target-version v1.33.0

# Rollback cluster
python -m k8s_simplify rollback --master 192.168.1.10 \
    --workers 192.168.1.11 192.168.1.12 \
    --user root --password mypass
```

The `suplement/` directory contains old helper scripts kept for reference only.
