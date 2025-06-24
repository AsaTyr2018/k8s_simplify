Tool Concept: Automated Kubernetes Deployment and Management Framework for Linux

This tool is designed to streamline the installation, update, and rollback processes of Kubernetes on Linux systems. It acts as a modular automation framework consisting of multiple key components that handle both master and worker (node) setup tasks with minimal user interaction.
Some old Supplementary files are located under suplement/ (ONLY for Supplement and not Production)

Core Objectives
Simplify Kubernetes lifecycle operations (install, update, rollback)

Support multi-node cluster setups

Automate configuration, networking, and joining procedures

Provide a persistent, user-friendly access layer (e.g., dashboard)

Ensure modularity and transparency of each step

Framework Components
Master Installer – Initializes and configures the Kubernetes master node.

Node Installer – Prepares and adds additional nodes to the cluster.

Auto Join Mechanism – Securely connects worker nodes to the master.

Preparation Utility – Checks and installs required packages, system settings, and user configurations.

Workflow Overview
After launching the tool, a minimal set of user inputs will be requested:

Cluster name

IP addresses and usernames of the master and node systems

Login method: default is user/password (with a brief preparation guide for enabling passwordless sudo for the initial remote user)

Once the basic data is collected, the tool proceeds through a phase-based automation workflow:

Phase 1: Master Node Preparation
Validate and install required packages and kernel modules

Set up system settings (e.g., swap off, sysctl tuning)

Create a dedicated k8s user with appropriate permissions

Prepare the environment for Kubernetes initialization

Phase 2: Kubernetes Master Installation
Install Kubernetes components (kubeadm, kubelet, kubectl)

Initialize the master node

Deploy a web-based Kubernetes dashboard with persistent access

Fixed external port

External IP accessibility configured

Persistent admin access token generated

Phase 3: Master Node Verification
Validate successful initialization

Ensure essential Kubernetes services are running

Test dashboard accessibility and API responsiveness

Phase 4: Worker Node Deployment
Connect to each listed node via SSH

Perform the same requirement checks as on the master

Install Kubernetes components on each node

Automatically join each node to the cluster using the token and CA hash provided by the master

Phase 5: Node Health Check
Validate all worker nodes are visible and healthy within the cluster

Run status checks to ensure pod scheduling and communication are functional

Phase 6: Finalization and Handover
Display all relevant access information to the user:

Cluster access URL (dashboard)

Admin token or kubeconfig file

Node and service health summaries

Provide optional export of connection details to file


Update & Rollback Mechanism
The tool includes built-in support for safe and reversible updates of Kubernetes clusters, as well as targeted rollbacks in case of failure or incompatibility. The update and rollback processes follow the same modular, phase-based architecture as the installation routine, ensuring consistency, reliability, and minimal disruption.

Update Workflow
The update routine is structured to ensure controlled, step-by-step upgrades with automated pre-checks and fallbacks.

Phase 0: Pre-Update Checks
Detect current Kubernetes version on all nodes

Compare against target version (provided manually or fetched automatically)

Perform compatibility and changelog checks

Create full system snapshots (optional, with integration support for tools like Timeshift or Btrfs/ZFS snapshots)

Phase 1: Master Node Update
Cordon and drain the master node (if applicable)

Upgrade Kubernetes components (kubeadm, kubelet, kubectl)

Apply control plane upgrades using kubeadm upgrade

Restart necessary services and validate version consistency

Uncordon the master

Phase 2: Node Update (Rolling Upgrade)
Iterate through each worker node:

Cordon and drain

Upgrade node components

Restart and re-join the node

Run post-upgrade health checks

Uncordon after validation

Nodes are updated one at a time to avoid service disruption

Phase 3: Post-Update Validation
Verify overall cluster health

Check pod scheduling and networking

Validate dashboard and API server functionality

Notify user of upgrade success with version summary

Rollback Workflow
If a failure is detected during the update process or if the user initiates a manual rollback, the tool triggers a structured reversion path.

Phase 1: Detect Rollback Point
Load saved state and snapshot (if available)

Identify the last known working version for master and nodes

Prepare downgrade or restoration targets

Phase 2: Master Node Rollback
Downgrade control plane components to previous version

Revert configuration files and manifests

Restore dashboard and network settings (if altered)

Phase 3: Node Rollback
Sequentially downgrade node components

Restore container runtime settings if changed

Rejoin nodes to the previous version of the cluster

Phase 4: Cluster Revalidation
Ensure cluster is back in operational state

Confirm dashboard and user access are restored

Provide report to user including rollback details and recommendations

Safety Mechanisms
All updates and rollbacks are non-destructive by default

The system maintains audit logs for every change

Optional integration with backup solutions (etcd, config files, kube manifests)

Users are prompted before applying critical version jumps (e.g., major version changes)




