"""Utilities for Phase 2: Kubernetes master installation."""

from subprocess import CalledProcessError, run
from typing import Optional
import time

from .phase1 import _ssh_cmd


class Phase2Error(Exception):
    """Custom exception for phase 2 failures."""


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
    stderr = last_exc.stderr if last_exc and last_exc.stderr else ""
    raise Phase2Error(
        f"Command failed on {ip}: {command}\n{stderr}"
    ) from last_exc


def _wait_for_apiserver(ip: str, user: str, password: str, timeout: int = 60) -> None:
    """Wait until the API server on the master node becomes reachable."""
    end_time = time.time() + timeout
    while time.time() < end_time:
        try:
            run_remote_capture(
                ip,
                user,
                password,
                f"curl -kfs https://{ip}:6443/healthz >/dev/null",
            )
            return
        except Phase2Error:
            time.sleep(5)
    raise Phase2Error(f"API server on {ip} did not become ready")


def init_master(ip: str, user: str, password: str) -> str:
    """Initialize Kubernetes control plane and dashboard."""
    print("* Initializing Kubernetes control plane")
    run_remote_capture(ip, user, password, "sudo kubeadm init --pod-network-cidr=10.244.0.0/16")
    time.sleep(10)
    _wait_for_apiserver(ip, user, password)

    print("* Configuring kubeconfig")
    run_remote_capture(ip, user, password, "mkdir -p $HOME/.kube")
    time.sleep(10)
    run_remote_capture(ip, user, password, "sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config")
    time.sleep(10)
    run_remote_capture(ip, user, password, "sudo chown $(id -u):$(id -g) $HOME/.kube/config")
    time.sleep(10)

    print("* Deploying Flannel networking")
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml",
    )
    time.sleep(10)

    print("* Installing Kubernetes dashboard")
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml",
    )
    time.sleep(10)
    run_remote_capture(ip, user, password, "kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard")
    time.sleep(10)
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin --serviceaccount=kubernetes-dashboard:dashboard-admin",
    )
    time.sleep(10)
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl -n kubernetes-dashboard patch svc kubernetes-dashboard --type='json' -p='[{\"op\":\"replace\",\"path\":\"/spec/type\",\"value\":\"NodePort\"},{\"op\":\"add\",\"path\":\"/spec/ports/0/nodePort\",\"value\":32443}]'",
    )
    time.sleep(10)
    token = run_remote_capture(
        ip,
        user,
        password,
        "kubectl -n kubernetes-dashboard create token dashboard-admin --duration=8760h",
    )
    time.sleep(10)
    print(f"Dashboard URL: https://{ip}:32443")
    print(f"Dashboard token: {token}")
    return token
