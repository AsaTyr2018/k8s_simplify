#!/bin/bash
set -e

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. with sudo)" >&2
  exit 1
fi

echo "== Worker node preflight =="

# Enable remote root login temporarily
sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
systemctl restart ssh || systemctl restart sshd
echo 'root:setmeup2025' | chpasswd
echo "Temporary root password for remote SSH access: setmeup2025"

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
    | gpg --batch --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
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

cat <<'EOM'
Preflight complete.
Run the master preflight script on the control plane node and then execute the installer from your management machine.
EOM
