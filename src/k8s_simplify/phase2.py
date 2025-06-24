"""Utilities for Phase 2: Kubernetes master installation."""

from subprocess import CalledProcessError, run

from .phase1 import _ssh_cmd


class Phase2Error(Exception):
    """Custom exception for phase 2 failures."""


def run_remote_capture(ip: str, user: str, password: str, command: str) -> str:
    """Run a remote command via SSH and return its output."""
    cmd = _ssh_cmd(ip, user, password, command)
    try:
        result = run(cmd, check=True, capture_output=True, text=True)
    except CalledProcessError as exc:
        raise Phase2Error(f"Command failed on {ip}: {command}") from exc
    return result.stdout.strip()


def init_master(ip: str, user: str, password: str) -> str:
    """Initialize Kubernetes control plane and dashboard."""
    print("* Initializing Kubernetes control plane")
    run_remote_capture(ip, user, password, "sudo kubeadm init --pod-network-cidr=10.244.0.0/16")

    print("* Configuring kubeconfig")
    run_remote_capture(ip, user, password, "mkdir -p $HOME/.kube")
    run_remote_capture(ip, user, password, "sudo cp /etc/kubernetes/admin.conf $HOME/.kube/config")
    run_remote_capture(ip, user, password, "sudo chown $(id -u):$(id -g) $HOME/.kube/config")

    print("* Deploying Flannel networking")
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml",
    )

    print("* Installing Kubernetes dashboard")
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml",
    )
    run_remote_capture(ip, user, password, "kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard")
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin --serviceaccount=kubernetes-dashboard:dashboard-admin",
    )
    run_remote_capture(
        ip,
        user,
        password,
        "kubectl -n kubernetes-dashboard patch svc kubernetes-dashboard --type='json' -p='[{\"op\":\"replace\",\"path\":\"/spec/type\",\"value\":\"NodePort\"},{\"op\":\"add\",\"path\":\"/spec/ports/0/nodePort\",\"value\":32443}]'",
    )
    token = run_remote_capture(
        ip,
        user,
        password,
        "kubectl -n kubernetes-dashboard create token dashboard-admin --duration=8760h",
    )
    print(f"Dashboard URL: https://{ip}:32443")
    print(f"Dashboard token: {token}")
    return token
