"""Utilities for Phase 1: master node preparation."""

from subprocess import CalledProcessError, run
from typing import List


class Phase1Error(Exception):
    """Custom exception for phase 1 failures."""


def _ssh_cmd(ip: str, user: str, password: str, command: str) -> List[str]:
    base = ["ssh", "-o", "StrictHostKeyChecking=no", f"{user}@{ip}", command]
    if password:
        return ["sshpass", "-p", password] + base
    return base


def run_remote(ip: str, user: str, password: str, command: str) -> None:
    """Run a command on a remote host via SSH."""
    try:
        run(_ssh_cmd(ip, user, password, command), check=True)
    except CalledProcessError as exc:
        raise Phase1Error(f"Command failed on {ip}: {command}") from exc


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
        "sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg",
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

