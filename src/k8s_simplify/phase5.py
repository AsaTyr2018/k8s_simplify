"""Utilities for Phase 5: node health checks."""

from .phase2 import run_remote_capture


class Phase5Error(Exception):
    """Custom exception for phase 5 failures."""


def list_nodes(ip: str, user: str, password: str) -> str:
    """Return the output of `kubectl get nodes` from the master node."""
    try:
        return run_remote_capture(ip, user, password, "kubectl get nodes --no-headers -o wide")
    except Exception as exc:  # broad but fine for CLI tool
        raise Phase5Error(f"Failed to retrieve node list from {ip}") from exc


def check_node_health(ip: str, user: str, password: str) -> None:
    """Validate that all nodes report Ready status."""
    output = list_nodes(ip, user, password)
    unhealthy = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, status = parts[0], parts[1]
        if status != "Ready":
            unhealthy.append(f"{name} ({status})")
    if unhealthy:
        raise Phase5Error("Unhealthy nodes detected: " + ", ".join(unhealthy))

