"""Utilities for rolling back a Kubernetes cluster."""

from typing import List

from .phase1 import run_remote
from .phase3 import verify_master_node
from .phase4 import get_join_command, join_worker, prepare_worker
from .phase5 import check_node_health


class RollbackError(Exception):
    """Custom exception for rollback failures."""


def reset_node(ip: str, user: str, password: str) -> None:
    """Reset Kubernetes state on a node."""
    try:
        run_remote(ip, user, password, "sudo kubeadm reset -f")
        run_remote(ip, user, password, "sudo systemctl restart containerd")
    except Exception as exc:
        raise RollbackError(f"Failed to reset node {ip}") from exc


def rollback_master(ip: str, user: str, password: str) -> None:
    """Rollback master node."""
    reset_node(ip, user, password)


def rollback_workers(worker_ips: List[str], user: str, password: str) -> None:
    """Rollback worker nodes."""
    for ip in worker_ips:
        reset_node(ip, user, password)


def rejoin_workers(master_ip: str, worker_ips: List[str], user: str, password: str) -> None:
    """Rejoin workers to the cluster."""
    join_cmd = get_join_command(master_ip, user, password)
    for ip in worker_ips:
        prepare_worker(ip, user, password)
        join_worker(ip, user, password, join_cmd)


def post_rollback_validation(master_ip: str, user: str, password: str) -> None:
    """Validate cluster health after rollback."""
    verify_master_node(master_ip, user, password)
    check_node_health(master_ip, user, password)
