"""Utilities for Phase 3: master node verification."""

from subprocess import CalledProcessError, run
from typing import Optional

from .phase1 import _ssh_cmd


class Phase3Error(Exception):
    """Custom exception for phase 3 failures."""


def run_remote_capture(ip: str, user: str, password: str, command: str, retries: int = 2) -> str:
    """Run a remote command via SSH and return its output with retries."""
    cmd = _ssh_cmd(ip, user, password, command)
    last_exc: Optional[CalledProcessError] = None
    for _ in range(retries + 1):
        try:
            result = run(cmd, check=True, capture_output=True, text=True)
            return result.stdout.strip()
        except CalledProcessError as exc:
            last_exc = exc
    stderr = ""
    if last_exc and last_exc.stderr:
        stderr = last_exc.stderr.decode("utf-8", "ignore")
    raise Phase3Error(f"Command failed on {ip}: {command}\n{stderr}") from last_exc


def check_service_active(ip: str, user: str, password: str, service: str) -> None:
    """Ensure a systemd service is active on the remote host."""
    status = run_remote_capture(ip, user, password, f"systemctl is-active {service}")
    if status != "active":
        raise Phase3Error(f"Service {service} not active on {ip}")


def verify_dashboard(ip: str, user: str, password: str) -> None:
    """Verify the Kubernetes dashboard is reachable."""
    run_remote_capture(ip, user, password, f"curl -ks https://{ip}:32443 >/dev/null")


def verify_master_node(ip: str, user: str, password: str) -> None:
    """Verify master node services and dashboard."""
    print("* Checking container runtime")
    check_service_active(ip, user, password, "containerd")
    print("* Checking kubelet service")
    check_service_active(ip, user, password, "kubelet")
    print("* Checking kubectl connectivity")
    run_remote_capture(ip, user, password, "kubectl get nodes")
    print("* Checking dashboard access")
    verify_dashboard(ip, user, password)
    print("Master node verification successful")
