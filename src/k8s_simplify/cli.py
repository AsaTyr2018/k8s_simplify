import argparse
from dataclasses import dataclass, field
from typing import List

from .phase1 import Phase1Error, prepare_master
from .phase2 import Phase2Error, init_master
from .phase3 import Phase3Error, verify_master_node
from .phase4 import (
    Phase4Error,
    get_join_command,
    join_worker,
    prepare_worker,
)
from .phase5 import Phase5Error, check_node_health, list_nodes


@dataclass
class ClusterConfig:
    cluster_name: str
    master_ip: str
    worker_ips: List[str] = field(default_factory=list)
    ssh_user: str = ""
    ssh_password: str = ""
    dashboard_token: str = ""


def master_node_preparation(cfg: ClusterConfig):
    print(f"[Phase 1] Preparing master node {cfg.master_ip}")
    try:
        prepare_master(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
    except Phase1Error as exc:
        print(exc)
        raise SystemExit(1)


def install_master(cfg: ClusterConfig):
    print(f"[Phase 2] Installing Kubernetes on master {cfg.master_ip}")
    try:
        cfg.dashboard_token = init_master(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
    except Phase2Error as exc:
        print(exc)
        raise SystemExit(1)


def verify_master(cfg: ClusterConfig):
    print("[Phase 3] Verifying master node setup")
    try:
        verify_master_node(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
    except Phase3Error as exc:
        print(exc)
        raise SystemExit(1)


def deploy_workers(cfg: ClusterConfig):
    if not cfg.worker_ips:
        print("No worker nodes specified, skipping worker deployment")
        return
    print("[Phase 4] Deploying worker nodes")
    try:
        join_cmd = get_join_command(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
    except Phase4Error as exc:
        print(exc)
        raise SystemExit(1)
    for ip in cfg.worker_ips:
        print(f" - Preparing worker {ip}")
        try:
            prepare_worker(ip, cfg.ssh_user, cfg.ssh_password)
            join_worker(ip, cfg.ssh_user, cfg.ssh_password, join_cmd)
        except Phase4Error as exc:
            print(exc)
            raise SystemExit(1)


def check_nodes(cfg: ClusterConfig):
    print("[Phase 5] Checking node health")
    try:
        print("* Current node status:")
        nodes = list_nodes(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
        print(nodes)
        check_node_health(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
    except Phase5Error as exc:
        print(exc)
        raise SystemExit(1)


def finalize_install(cfg: ClusterConfig):
    print("[Phase 6] Finalizing installation")
    if cfg.dashboard_token:
        print(f"Dashboard URL: https://{cfg.master_ip}:32443")
        print(f"Dashboard token: {cfg.dashboard_token}")


def install_cluster(args: argparse.Namespace):
    cfg = ClusterConfig(
        cluster_name=args.name,
        master_ip=args.master,
        worker_ips=args.workers or [],
        ssh_user=args.user,
        ssh_password=args.password,
    )
    master_node_preparation(cfg)
    install_master(cfg)
    verify_master(cfg)
    deploy_workers(cfg)
    check_nodes(cfg)
    finalize_install(cfg)


def update_cluster(args: argparse.Namespace):
    print("Starting cluster update")
    # TODO: implement update workflow


def rollback_cluster(args: argparse.Namespace):
    print("Starting rollback")
    # TODO: implement rollback workflow


def main():
    parser = argparse.ArgumentParser(description="Kubernetes simplify toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install", help="Install a new cluster")
    install.add_argument("--name", required=True, help="Cluster name")
    install.add_argument("--master", required=True, help="Master node IP")
    install.add_argument("--workers", nargs="*", help="Worker node IPs")
    install.add_argument("--user", default="root", help="SSH username")
    install.add_argument("--password", default="", help="SSH password")
    install.set_defaults(func=install_cluster)

    update = sub.add_parser("update", help="Update existing cluster")
    update.add_argument("--target-version", required=True, help="Target kube version")
    update.set_defaults(func=update_cluster)

    rollback = sub.add_parser("rollback", help="Rollback cluster changes")
    rollback.set_defaults(func=rollback_cluster)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
