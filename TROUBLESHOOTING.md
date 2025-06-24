# Troubleshooting

This document lists common issues that can occur during the automated setup phases and how to resolve them.

## Phase 1: Preflight
- **Container runtime not running**: verify `containerd` is active with `sudo systemctl status containerd`.
- **Swap still enabled**: the scripts disable swap; if it remains on, manually run `swapoff -a` and remove swap entries from `/etc/fstab`.

## Phase 2: Master installation
- **`kubeadm init` failures**: run `sudo kubeadm reset -f` and try the install again. Check `/var/log/syslog` for detailed errors.
- **Network plugin pods not starting**: use `kubectl -n kube-flannel describe pod <pod>` and `kubectl logs` to inspect why the Flannel daemon set failed. Missing images or kernel modules are common causes.
- **Dashboard not reachable**: ensure the dashboard service is patched to NodePort 32443 and that port is open on the master node.

## Phase 3: Master verification
- **API server unreachable**: verify that `kube-apiserver` is listening on port 6443 with `sudo netstat -tulpn | grep 6443`. Check container logs via `docker ps` or `crictl ps` depending on your runtime.

## Phase 4: Worker deployment
- **Nodes fail to join**: confirm the join token and discovery hash are correct by running `kubeadm token list` and `openssl x509 -pubkey -in /etc/kubernetes/pki/ca.crt | openssl rsa -pubin -outform der 2>/dev/null | openssl dgst -sha256 -hex | sed 's/^.* //'` on the master.
- **CNI errors**: if `kubelet` reports `CNI network not ready`, ensure the network plugin pods are running and the `/etc/cni/net.d` directory contains the flannel configuration.

## Phase 5: Health check
- **Node status not Ready**: run `kubectl describe node <name>` and look for conditions blocking readiness, such as `NetworkUnavailable` or `KubeletNotReady`.

## Phase 6: Finalization
- **Dashboard token missing**: regenerate with `kubectl -n kubernetes-dashboard create token dashboard-admin --duration=8760h`.
- **SSH still allows root login**: check `/etc/ssh/sshd_config` for `PermitRootLogin no` and restart the service with `sudo systemctl restart sshd`.

