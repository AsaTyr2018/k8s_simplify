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
from .phase6 import Phase6Error, finalize_cluster
from .utils import check_local_tools
from .update import (
    UpdateError,
    post_update_validation,
    pre_update_check,
    update_master,
    update_workers,
)
from .rollback import (
    RollbackError,
    post_rollback_validation,
    rejoin_workers,
    rollback_master,
    rollback_workers,
)


@dataclass
class ClusterConfig:
    cluster_name: str
    master_ip: str
    worker_ips: List[str] = field(default_factory=list)
    ssh_user: str = ""
    ssh_password: str = ""
    dashboard_token: str = ""
    export_file: str = ""


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
        try:
            finalize_cluster(
                cfg.master_ip,
                cfg.worker_ips,
                cfg.ssh_user,
                cfg.ssh_password,
                cfg.dashboard_token,
                cfg.export_file or None,
            )
        except Phase6Error as exc:
            print(exc)
            raise SystemExit(1)


def install_cluster(args: argparse.Namespace):
    cfg = ClusterConfig(
        cluster_name=args.name,
        master_ip=args.master,
        worker_ips=args.workers or [],
        ssh_user=args.user,
        ssh_password=args.password,
        export_file=args.export_file or "",
    )
    master_node_preparation(cfg)
    install_master(cfg)
    verify_master(cfg)
    deploy_workers(cfg)
    check_nodes(cfg)
    finalize_install(cfg)


def update_cluster(args: argparse.Namespace):
    cfg = ClusterConfig(
        cluster_name="",
        master_ip=args.master,
        worker_ips=args.workers or [],
        ssh_user=args.user,
        ssh_password=args.password,
    )
    print("Starting cluster update")
    try:
        versions = pre_update_check(
            cfg.master_ip, cfg.worker_ips, cfg.ssh_user, cfg.ssh_password
        )
        for ip, ver in versions.items():
            print(f"Current version on {ip}: {ver}")
        update_master(cfg.master_ip, cfg.ssh_user, cfg.ssh_password, args.target_version)
        update_workers(cfg.worker_ips, cfg.ssh_user, cfg.ssh_password, args.target_version)
        post_update_validation(
            cfg.master_ip, cfg.worker_ips, cfg.ssh_user, cfg.ssh_password
        )
        print("Update complete")
    except UpdateError as exc:
        print(exc)
        raise SystemExit(1)


def rollback_cluster(args: argparse.Namespace):
    cfg = ClusterConfig(
        cluster_name="",
        master_ip=args.master,
        worker_ips=args.workers or [],
        ssh_user=args.user,
        ssh_password=args.password,
    )
    print("Starting rollback")
    try:
        rollback_master(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
        rollback_workers(cfg.worker_ips, cfg.ssh_user, cfg.ssh_password)
        rejoin_workers(cfg.master_ip, cfg.worker_ips, cfg.ssh_user, cfg.ssh_password)
        post_rollback_validation(cfg.master_ip, cfg.ssh_user, cfg.ssh_password)
        print("Rollback complete")
    except RollbackError as exc:
        print(exc)
        raise SystemExit(1)


def main():
    parser = argparse.ArgumentParser(description="Kubernetes simplify toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    install = sub.add_parser("install", help="Install a new cluster")
    install.add_argument("--name", required=True, help="Cluster name")
    install.add_argument("--master", required=True, help="Master node IP")
    install.add_argument("--workers", nargs="*", help="Worker node IPs")
    install.add_argument("--user", default="root", help="SSH username")
    install.add_argument("--password", default="", help="SSH password")
    install.add_argument(
        "--export-file",
        help="Write final cluster information to file",
    )
    install.set_defaults(func=install_cluster)

    update = sub.add_parser("update", help="Update existing cluster")
    update.add_argument("--master", required=True, help="Master node IP")
    update.add_argument("--workers", nargs="*", help="Worker node IPs")
    update.add_argument("--user", default="root", help="SSH username")
    update.add_argument("--password", default="", help="SSH password")
    update.add_argument("--target-version", required=True, help="Target kube version")
    update.set_defaults(func=update_cluster)

    rollback = sub.add_parser("rollback", help="Rollback cluster changes")
    rollback.add_argument("--master", required=True, help="Master node IP")
    rollback.add_argument("--workers", nargs="*", help="Worker node IPs")
    rollback.add_argument("--user", default="root", help="SSH username")
    rollback.add_argument("--password", default="", help="SSH password")
    rollback.set_defaults(func=rollback_cluster)

    args = parser.parse_args()
    check_local_tools(bool(getattr(args, "password", "")))
    args.func(args)


if __name__ == "__main__":
    main()
