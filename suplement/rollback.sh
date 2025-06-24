#!/bin/bash

set -e

# Rolls back the install_k8s_cluster.sh changes by removing Kubernetes and related configuration.
# Requires root privileges.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. with sudo)" >&2
  exit 1
fi

# Reset cluster state if kubeadm is present
if command -v kubeadm >/dev/null 2>&1; then
  kubeadm reset -f
fi

# Stop kubelet if running
if systemctl is-active --quiet kubelet; then
  systemctl stop kubelet
fi

# Remove packages
apt-get purge -y kubelet kubeadm kubectl containerd || true
apt-get autoremove -y

# Remove Kubernetes files and keys
rm -rf /etc/kubernetes /var/lib/etcd /var/lib/kubelet
rm -f /etc/apt/sources.list.d/kubernetes.list
rm -f /etc/apt/keyrings/kubernetes-apt-keyring.gpg
rm -f /root/dashboard_token

# Re-enable swap if it was disabled
sed -i '/ swap / s/^#//' /etc/fstab
swapon -a || true

# Disable IPv4 forwarding that was enabled for Kubernetes
sysctl -w net.ipv4.ip_forward=0
sed -i '/^net.ipv4.ip_forward=1/d' /etc/sysctl.conf

printf '\nKubernetes removal complete.\n'
