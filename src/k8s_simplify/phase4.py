"""Utilities for Phase 4: worker node deployment."""

from subprocess import CalledProcessError, run

from .phase1 import Phase1Error, run_remote
from .phase2 import run_remote_capture


class Phase4Error(Exception):
    """Custom exception for phase 4 failures."""


def get_join_command(ip: str, user: str, password: str) -> str:
    """Retrieve the kubeadm join command from the master node."""
    try:
        return run_remote_capture(
            ip,
            user,
            password,
            "kubeadm token create --print-join-command",
        )
    except Exception as exc:  # broad but fine for CLI tool
        raise Phase4Error(f"Failed to get join command from {ip}") from exc


def prepare_worker(ip: str, user: str, password: str) -> None:
    """Install prerequisites on the worker node."""
    steps = [
        "sudo apt-get update -y",
        "sudo apt-get install -y containerd apt-transport-https curl gpg",
        "sudo mkdir -p /etc/containerd",
        "sudo sh -c 'containerd config default >/etc/containerd/config.toml'",
        "sudo systemctl restart containerd",
        (
            "curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key | "
            "sudo gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg"
        ),
        (
            "echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] "
            "https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /' | "
            "sudo tee /etc/apt/sources.list.d/kubernetes.list"
        ),
        "sudo apt-get update -y",
        (
            "sudo apt-get install -y kubelet kubeadm kubectl && "
            "sudo apt-mark hold kubelet kubeadm kubectl"
        ),
        "sudo swapoff -a",
        "sudo sed -i '/ swap / s/^/#/' /etc/fstab",
        "sudo sysctl -w net.ipv4.ip_forward=1",
        (
            "grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf || "
            "echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf"
        ),
    ]
    for cmd in steps:
        try:
            run_remote(ip, user, password, cmd)
        except Phase1Error as exc:
            raise Phase4Error(str(exc)) from exc


def join_worker(ip: str, user: str, password: str, join_cmd: str) -> None:
    """Join the worker node to the Kubernetes cluster."""
    try:
        run_remote(ip, user, password, f"sudo {join_cmd}")
    except Phase1Error as exc:
        raise Phase4Error(str(exc)) from exc

