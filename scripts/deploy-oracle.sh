#!/usr/bin/env bash
# One-shot setup script for deploying Dispatch to Oracle Cloud Free Tier.
#
# Prerequisites:
#   - An Oracle Cloud account (https://cloud.oracle.com)
#   - An ARM VM created (VM.Standard.A1.Flex, 4 OCPU, 24 GB RAM)
#   - SSH access to the VM configured
#   - A domain pointing to the VM's public IP (optional but recommended)
#
# Usage:
#   export VM_IP=your.vm.ip.address
#   export SSH_KEY=~/.ssh/your-key
#   ./scripts/deploy-oracle.sh

set -euo pipefail

VM_IP="${VM_IP:-}"
SSH_KEY="${SSH_KEY:-~/.ssh/id_rsa}"
REPO_URL="${REPO_URL:-https://github.com/markdavidgan/dispatch.git}"

if [[ -z "$VM_IP" ]]; then
  echo "ERROR: Set VM_IP to your Oracle Cloud VM's public IP address."
  exit 1
fi

echo "=== Deploying Dispatch to Oracle Cloud VM: $VM_IP ==="

# Copy local .env to the VM (if it exists)
if [[ -f .env ]]; then
  echo "→ Uploading .env …"
  scp -i "$SSH_KEY" -o StrictHostKeyChecking=no .env "ubuntu@$VM_IP:/tmp/dispatch.env"
fi

# Remote setup and deploy
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "ubuntu@$VM_IP" << 'REMOTE'
set -euo pipefail

# Install Docker if missing
if ! command -v docker &> /dev/null; then
  echo "→ Installing Docker …"
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER"
  newgrp docker || true
fi

# Clone or update repo
if [[ -d ~/dispatch ]]; then
  echo "→ Updating existing repo …"
  cd ~/dispatch && git pull
else
  echo "→ Cloning repo …"
  git clone "${REPO_URL:-https://github.com/markdavidgan/dispatch.git}" ~/dispatch
  cd ~/dispatch
fi

# Copy env file into place
if [[ -f /tmp/dispatch.env ]]; then
  mv /tmp/dispatch.env .env
fi

# Ensure DISPATCH_MASTER_KEY is set
if ! grep -q "DISPATCH_MASTER_KEY=" .env 2>/dev/null; then
  echo "ERROR: DISPATCH_MASTER_KEY must be set in .env"
  exit 1
fi

# Start the stack
echo "→ Starting Dispatch …"
docker compose up -d

echo ""
echo "=== Dispatch is running ==="
echo "Health check: curl http://$VM_IP/health"
echo "Setup wizard: http://$VM_IP/setup"
REMOTE

echo ""
echo "=== Done ==="
echo "Visit http://$VM_IP/setup to complete first-boot configuration."
