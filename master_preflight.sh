#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. with sudo)" >&2
  exit 1
fi

echo "== Master node preflight =="

# Grant passwordless sudo to the user that invoked this script via sudo
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
  echo "$SUDO_USER ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/$SUDO_USER
fi

apt-get update -y
apt-get install -y containerd apt-transport-https curl gpg

mkdir -p /etc/containerd
if [ ! -f /etc/containerd/config.toml ]; then
  containerd config default >/etc/containerd/config.toml
fi
systemctl restart containerd

if [ ! -d /etc/apt/keyrings ]; then
  mkdir -p -m 755 /etc/apt/keyrings
fi
if [ ! -f /etc/apt/keyrings/kubernetes-apt-keyring.gpg ]; then
  curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key \
    | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
fi
cat <<'REPO' >/etc/apt/sources.list.d/kubernetes.list
deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /
REPO
apt-get update -y
apt-get install -y kubelet kubeadm kubectl
apt-mark hold kubelet kubeadm kubectl

swapoff -a
sed -i '/ swap / s/^/#/' /etc/fstab

sysctl -w net.ipv4.ip_forward=1
if ! grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf; then
  echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
fi

if ! id k8sadmin >/dev/null 2>&1; then
  useradd -m -s /bin/bash k8sadmin
fi
echo 'k8sadmin ALL=(ALL) NOPASSWD:ALL' >/etc/sudoers.d/k8sadmin

cat <<'EOM'
Preflight complete.
Next steps:
  1. Run the installer from your management machine:
     python -m k8s_simplify install --name <cluster> --master <this_ip> --user k8sadmin
  2. Run the node_preflight.sh script on each worker node before installation.
EOM
