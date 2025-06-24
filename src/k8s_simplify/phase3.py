"""Utilities for Phase 3: master node verification."""

from subprocess import CalledProcessError, run

from .phase1 import _ssh_cmd


class Phase3Error(Exception):
    """Custom exception for phase 3 failures."""


def run_remote_capture(ip: str, user: str, password: str, command: str) -> str:
    """Run a remote command via SSH and return its output."""
    cmd = _ssh_cmd(ip, user, password, command)
    try:
        result = run(cmd, check=True, capture_output=True, text=True)
    except CalledProcessError as exc:
        raise Phase3Error(f"Command failed on {ip}: {command}") from exc
    return result.stdout.strip()


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
