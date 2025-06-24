"""Utilities for Phase 6: finalization and handover."""

from typing import Dict, List

from .phase2 import run_remote_capture
from .phase5 import list_nodes


class Phase6Error(Exception):
    """Custom exception for phase 6 failures."""


def _service_status(ip: str, user: str, password: str, service: str) -> str:
    """Return the systemd service status on the remote host."""
    try:
        return run_remote_capture(ip, user, password, f"systemctl is-active {service}")
    except Exception:
        return "unknown"


def gather_cluster_summary(
    master_ip: str, worker_ips: List[str], user: str, password: str
) -> Dict[str, Dict[str, str]]:
    """Return service status summary for all nodes."""
    summary: Dict[str, Dict[str, str]] = {}
    all_ips = [master_ip] + worker_ips
    for ip in all_ips:
        summary[ip] = {
            "containerd": _service_status(ip, user, password, "containerd"),
            "kubelet": _service_status(ip, user, password, "kubelet"),
        }
    return summary


def finalize_cluster(
    master_ip: str,
    worker_ips: List[str],
    user: str,
    password: str,
    token: str,
    export_file: str | None = None,
) -> None:
    """Display final cluster information and optionally write to a file."""
    try:
        nodes = list_nodes(master_ip, user, password)
        services = gather_cluster_summary(master_ip, worker_ips, user, password)
    except Exception as exc:  # broad but acceptable for CLI
        raise Phase6Error("Failed to gather cluster information") from exc

    lines = [
        f"Dashboard URL: https://{master_ip}:32443",
        f"Dashboard token: {token}",
        "",
        "Node status:",
        nodes,
        "",
        "Service status:",
    ]
    for ip, svc in services.items():
        lines.append(f"{ip}:")
        lines.append(f"  containerd: {svc['containerd']}")
        lines.append(f"  kubelet: {svc['kubelet']}")
    summary = "\n".join(lines)
    print(summary)

    if export_file:
        try:
            with open(export_file, "w", encoding="utf-8") as f:
                f.write(summary)
        except OSError as exc:
            raise Phase6Error(f"Failed to write summary to {export_file}") from exc
        print(f"Details exported to {export_file}")
