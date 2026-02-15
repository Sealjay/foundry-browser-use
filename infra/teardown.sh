#!/usr/bin/env bash
set -euo pipefail

# Azure resource group teardown script
# Usage: ./teardown.sh <resource-group>
# Example: ./teardown.sh rg-browser-agent

# Check if user is logged in to Azure
if ! az account show &>/dev/null; then
  echo "Error: Not logged in to Azure. Please run 'az login' first."
  exit 1
fi

# Parse arguments
RESOURCE_GROUP="${1:?Error: Resource group name required}"

# Prompt for confirmation
echo "WARNING: This will permanently delete the resource group '${RESOURCE_GROUP}' and all its resources."
read -p "Are you sure you want to continue? (yes/no): " CONFIRMATION

if [[ "${CONFIRMATION,,}" != "yes" ]]; then
  echo "Teardown cancelled."
  exit 0
fi

# Delete resource group
echo "Deleting resource group '${RESOURCE_GROUP}'..."
az group delete \
  --name "${RESOURCE_GROUP}" \
  --yes \
  --no-wait

echo "Resource group deletion initiated. This will complete in the background."
