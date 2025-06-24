"""Utilities for Phase 1: master node preparation."""

from subprocess import CalledProcessError, run
import shutil
from typing import Optional
from typing import List


class Phase1Error(Exception):
    """Custom exception for phase 1 failures."""


def _ssh_cmd(ip: str, user: str, password: str, command: str) -> List[str]:
    base = ["ssh", "-o", "StrictHostKeyChecking=no", f"{user}@{ip}", command]
    if password:
        if shutil.which("sshpass") is None:
            raise Phase1Error("sshpass is required for password authentication")
        return ["sshpass", "-p", password] + base
    return base


def run_remote(ip: str, user: str, password: str, command: str, retries: int = 2) -> None:
    """Run a command on a remote host via SSH with simple retries."""
    last_exc: Optional[CalledProcessError] = None
    for _ in range(retries + 1):
        try:
            run(
                _ssh_cmd(ip, user, password, command),
                check=True,
                capture_output=True,
                text=True,
            )
            return
        except CalledProcessError as exc:
            last_exc = exc
    stderr = last_exc.stderr or ""
    stdout = last_exc.stdout or ""
    raise Phase1Error(
        f"Command failed on {ip}: {command}\nSTDOUT: {stdout}\nSTDERR: {stderr}"
    ) from last_exc


def prepare_master(ip: str, user: str, password: str) -> None:
    """Execute master node preparation steps."""
    print("* Installing required packages on master")
    run_remote(ip, user, password, "sudo apt-get update -y")
    run_remote(
        ip,
        user,
        password,
        "sudo apt-get install -y containerd apt-transport-https curl gpg",
    )

    print("* Configuring containerd")
    run_remote(ip, user, password, "sudo mkdir -p /etc/containerd")
    run_remote(
        ip,
        user,
        password,
        "sudo sh -c 'containerd config default >/etc/containerd/config.toml'",
    )
    run_remote(ip, user, password, "sudo systemctl restart containerd")

    print("* Installing kubeadm, kubelet and kubectl")
    run_remote(
        ip,
        user,
        password,
        "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | "
        "sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
    )
    run_remote(
        ip,
        user,
        password,
        "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] "
        "https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | "
        "sudo tee /etc/apt/sources.list.d/kubernetes.list",
    )
    run_remote(ip, user, password, "sudo apt-get update -y")
    run_remote(
        ip,
        user,
        password,
        "sudo apt-get install -y kubelet kubeadm kubectl && "
        "sudo apt-mark hold kubelet kubeadm kubectl",
    )

    print("* Disabling swap")
    run_remote(ip, user, password, "sudo swapoff -a")
    run_remote(
        ip,
        user,
        password,
        "sudo sed -i '/ swap / s/^/#/' /etc/fstab",
    )

    print("* Enabling IPv4 forwarding")
    run_remote(ip, user, password, "sudo sysctl -w net.ipv4.ip_forward=1")
    run_remote(
        ip,
        user,
        password,
        "grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf || "
        "echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf",
    )

    print("* Creating k8sadmin user")
    run_remote(
        ip,
        user,
        password,
        "id k8sadmin >/dev/null 2>&1 || sudo useradd -m -s /bin/bash k8sadmin",
    )
    run_remote(
        ip,
        user,
        password,
        "echo 'k8sadmin ALL=(ALL) NOPASSWD:ALL' | sudo tee /etc/sudoers.d/k8sadmin",
    )
    print("Master node preparation complete")

