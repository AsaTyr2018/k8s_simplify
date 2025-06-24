#!/bin/bash

set -e

# Automated Kubernetes installer with web dashboard
# Installs a single control plane node and joins additional worker nodes via SSH
# Exposes the Dashboard via NodePort and stores the admin token under
# /root/dashboard_token. Works on Debian/Ubuntu systems and requires
# root privileges.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (e.g. with sudo)" >&2
  exit 1
fi

read -rp "Is this the first control plane node? [y/N]: " FIRST_NODE

check_service() {
  if ! systemctl is-active --quiet "$1"; then
    echo "Service $1 is not running" >&2
    return 1
  fi
}

pre_install_check() {
  echo "Running pre-install validation..."
  check_service containerd || return 1
  if systemctl is-active --quiet kubelet; then
    echo "A Kubernetes cluster appears to be running. Aborting." >&2
    return 1
  fi
  echo "Pre-install validation successful."
}

post_install_check() {
  echo "Running post-install validation..."
  check_service containerd
  check_service kubelet
  if ! kubectl cluster-info >/dev/null 2>&1; then
    echo "kubectl cannot reach the cluster" >&2
    return 1
  fi
  kubectl wait --for=condition=Ready nodes --all --timeout=120s >/dev/null
  kubectl wait --for=condition=Ready pods -n kube-system --all --timeout=120s >/dev/null
  echo "Post-install validation successful."
}

install_prereqs() {
  if ! command -v containerd >/dev/null 2>&1; then
    apt-get update
    apt-get install -y containerd
  fi

  if [ ! -f /etc/containerd/config.toml ]; then
    mkdir -p /etc/containerd
    containerd config default >/etc/containerd/config.toml
    systemctl restart containerd
  fi

  if ! command -v kubeadm >/dev/null 2>&1; then
    apt-get update
    apt-get install -y apt-transport-https curl gpg
    if [ ! -d /etc/apt/keyrings ]; then
      mkdir -p -m 755 /etc/apt/keyrings
    fi
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key \
      | gpg --batch --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    cat <<'REPO' >/etc/apt/sources.list.d/kubernetes.list
deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /
REPO
    apt-get update
    apt-get install -y kubelet kubeadm kubectl
    apt-mark hold kubelet kubeadm kubectl
fi

  if ! command -v sshpass >/dev/null 2>&1; then
    apt-get update
    apt-get install -y sshpass
  fi

  swapoff -a
  sed -i '/ swap / s/^/#/' /etc/fstab

  # Ensure IPv4 forwarding is enabled for Kubernetes networking
  sysctl -w net.ipv4.ip_forward=1
  if ! grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf; then
    echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
  fi
}

init_cluster() {
  kubeadm init --pod-network-cidr=10.244.0.0/16
  mkdir -p "$HOME/.kube"
  cp -i /etc/kubernetes/admin.conf "$HOME/.kube/config"
  chown "$(id -u)":"$(id -g)" "$HOME/.kube/config"
  kubectl apply -f https://raw.githubusercontent.com/coreos/flannel/master/Documentation/kube-flannel.yml
  kubectl apply -f https://raw.githubusercontent.com/kubernetes/dashboard/v2.7.0/aio/deploy/recommended.yaml
  kubectl create serviceaccount dashboard-admin -n kubernetes-dashboard
  kubectl create clusterrolebinding dashboard-admin --clusterrole=cluster-admin --serviceaccount=kubernetes-dashboard:dashboard-admin
  kubectl -n kubernetes-dashboard patch svc kubernetes-dashboard --type='json' \
    -p='[{"op":"replace","path":"/spec/type","value":"NodePort"},{"op":"add","path":"/spec/ports/0/nodePort","value":32443}]'
  NODE_PORT=32443
  TOKEN=$(kubectl -n kubernetes-dashboard create token dashboard-admin --duration=8760h)
  echo "Dashboard token: $TOKEN" > /root/dashboard_token
  echo "Dashboard node port: $NODE_PORT" >> /root/dashboard_token
  if command -v ufw >/dev/null 2>&1 && ufw status | grep -q active; then
    ufw allow 32443/tcp
  fi
}

join_workers() {
  JOIN_CMD=$(kubeadm token create --print-join-command)
  read -rp "Enter space separated IP addresses of worker nodes: " WORKERS
  for ip in $WORKERS; do
    read -rp "SSH user for $ip: " SSH_USER
    read -rsp "SSH password for $ip: " SSH_PASS
    echo

    cat >worker_setup.sh <<'EOS'
#!/bin/bash
set -e
USERNAME=k8sadmin
if ! id "$USERNAME" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "$USERNAME"
fi
usermod -aG sudo "$USERNAME"
echo "$USERNAME ALL=(ALL) NOPASSWD:ALL" >/etc/sudoers.d/$USERNAME
install_prereqs() {
  if ! command -v containerd >/dev/null 2>&1; then
    apt-get update
    apt-get install -y containerd
  fi
  if [ ! -f /etc/containerd/config.toml ]; then
    mkdir -p /etc/containerd
    containerd config default >/etc/containerd/config.toml
    systemctl restart containerd
  fi
  if ! command -v kubeadm >/dev/null 2>&1; then
    apt-get update
    apt-get install -y apt-transport-https curl gpg
    if [ ! -d /etc/apt/keyrings ]; then
      mkdir -p -m 755 /etc/apt/keyrings
    fi
    curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.33/deb/Release.key \
      | gpg --batch --yes --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
    cat <<'REPO' >/etc/apt/sources.list.d/kubernetes.list
deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.33/deb/ /
REPO
    apt-get update
    apt-get install -y kubelet kubeadm kubectl
    apt-mark hold kubelet kubeadm kubectl
  fi
  if ! command -v sshpass >/dev/null 2>&1; then
    apt-get update
    apt-get install -y sshpass
  fi
  swapoff -a
  sed -i '/ swap / s/^/#/' /etc/fstab
  sysctl -w net.ipv4.ip_forward=1
  if ! grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf; then
    echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
  fi
}
install_prereqs
su - "$USERNAME" -c "ssh-keygen -t rsa -N '' -f ~/.ssh/id_rsa"
cat /home/$USERNAME/.ssh/id_rsa.pub >>/home/$USERNAME/.ssh/authorized_keys
chown $USERNAME:$USERNAME /home/$USERNAME/.ssh/authorized_keys
chmod 600 /home/$USERNAME/.ssh/authorized_keys
SETUP_USER=${SUDO_USER:-root}
cp /home/$USERNAME/.ssh/id_rsa /home/$SETUP_USER/k8s_admin_id_rsa
cp /home/$USERNAME/.ssh/id_rsa.pub /home/$SETUP_USER/k8s_admin_id_rsa.pub
chown $SETUP_USER:$SETUP_USER /home/$SETUP_USER/k8s_admin_id_rsa*
chmod 600 /home/$SETUP_USER/k8s_admin_id_rsa
JOIN_PASS=$(tr -dc A-Za-z0-9 </dev/urandom | head -c 12)
echo "$JOIN_PASS" >/home/$SETUP_USER/node_join_pass
chown $SETUP_USER:$SETUP_USER /home/$SETUP_USER/node_join_pass
chmod 600 /home/$SETUP_USER/node_join_pass
echo "Join password: $JOIN_PASS"
echo 'Node preparation complete.'
EOS

    sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no worker_setup.sh "$SSH_USER@$ip:~/worker_setup.sh"
    sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$ip" "chmod +x ~/worker_setup.sh"
    echo "On node $ip run: sudo bash ~/worker_setup.sh"

    while ! sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no "$SSH_USER@$ip:~/k8s_admin_id_rsa" "key_$ip" 2>/dev/null; do
      sleep 5
    done
    sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no "$SSH_USER@$ip:~/k8s_admin_id_rsa.pub" "key_$ip.pub" >/dev/null 2>&1
    sshpass -p "$SSH_PASS" scp -o StrictHostKeyChecking=no "$SSH_USER@$ip:~/node_join_pass" "pass_$ip" >/dev/null 2>&1
    chmod 600 "key_$ip"

    read -rp "Enter join password from node $ip: " ENTERED_PASS
    NODE_PASS=$(cat "pass_$ip" 2>/dev/null)
    if [ "$ENTERED_PASS" != "$NODE_PASS" ]; then
      echo "Password mismatch for node $ip" >&2
      rm -f "key_$ip" "key_$ip.pub" "pass_$ip"
      continue
    fi

    mkdir -p ~/.ssh
    ssh-keygen -R "$ip" >/dev/null 2>&1 || true
    ssh-keyscan -H "$ip" >>~/.ssh/known_hosts 2>/dev/null
    ssh -i "key_$ip" k8sadmin@"$ip" sudo "$JOIN_CMD"
    rm -f "key_$ip" "key_$ip.pub" "pass_$ip"
  done
}

pre_install_check
install_prereqs
if [[ "$FIRST_NODE" =~ ^[Yy]$ ]]; then
  init_cluster
  join_workers
fi

post_install_check

printf '\nInstallation complete.'
