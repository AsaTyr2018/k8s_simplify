"""Utilities for upgrading a Kubernetes cluster."""

from subprocess import CalledProcessError, run
from typing import Dict, List

from .phase1 import _ssh_cmd, run_remote
from .phase3 import verify_master_node
from .phase5 import check_node_health


class UpdateError(Exception):
    """Custom exception for update failures."""


def _get_version(ip: str, user: str, password: str) -> str:
    cmd = _ssh_cmd(ip, user, password, "kubelet --version")
    try:
        result = run(cmd, check=True, capture_output=True, text=True)
    except CalledProcessError as exc:
        raise UpdateError(f"Failed to query version on {ip}") from exc
    parts = result.stdout.strip().split()
    return parts[-1] if parts else "unknown"


def pre_update_check(
    master_ip: str, worker_ips: List[str], user: str, password: str
) -> Dict[str, str]:
    """Return current kubelet versions for all nodes."""
    versions: Dict[str, str] = {}
    for ip in [master_ip] + worker_ips:
        versions[ip] = _get_version(ip, user, password)
    return versions


def update_master(ip: str, user: str, password: str, version: str) -> None:
    """Upgrade Kubernetes control plane on the master node."""
    try:
        run_remote(ip, user, password, f"sudo kubeadm upgrade apply -y {version}")
        run_remote(ip, user, password, "sudo apt-get install -y kubelet kubeadm kubectl")
        run_remote(ip, user, password, "sudo systemctl restart kubelet")
    except Exception as exc:  # broad but acceptable for CLI
        raise UpdateError(f"Failed to update master {ip}") from exc


def update_worker(ip: str, user: str, password: str, version: str) -> None:
    """Upgrade Kubernetes components on a worker node."""
    try:
        run_remote(ip, user, password, "sudo kubeadm upgrade node")
        run_remote(ip, user, password, "sudo apt-get install -y kubelet kubeadm kubectl")
        run_remote(ip, user, password, "sudo systemctl restart kubelet")
    except Exception as exc:
        raise UpdateError(f"Failed to update worker {ip}") from exc


def update_workers(worker_ips: List[str], user: str, password: str, version: str) -> None:
    """Perform rolling update of worker nodes."""
    for ip in worker_ips:
        update_worker(ip, user, password, version)


def post_update_validation(master_ip: str, worker_ips: List[str], user: str, password: str) -> None:
    """Validate cluster health after upgrade."""
    verify_master_node(master_ip, user, password)
    check_node_health(master_ip, user, password)
