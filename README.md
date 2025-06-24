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

## Requirements

The CLI relies on `ssh` being installed locally. If you supply a password via
the `--password` option, `sshpass` must also be available. Each remote host must
provide `sudo` access for the user supplied to the tool.

Outbound internet access is required during installation because the scripts
download Kubernetes manifests and packages. On hosts without access or with a
different package manager, manual preparation may be required. The automation
expects an apt-based system with passwordless `sudo` available for the chosen
user; other environments may need manual adjustments.

## Limitations

Password authentication over SSH is supported but may be disabled in some
environments. Using key-based authentication is recommended. All remote commands
run under the provided user account using `sudo`; if that user lacks the
necessary privileges or home directory setup, some steps such as copying
`admin.conf` could fail.
