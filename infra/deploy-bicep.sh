#!/usr/bin/env bash
set -euo pipefail

# Microsoft Foundry deployment script using Bicep
# Usage: ./deploy-bicep.sh <resource-group> [location]
# Example: ./deploy-bicep.sh rg-browser-agent uksouth

# Check if user is logged in to Azure
if ! az account show &>/dev/null; then
  echo "Error: Not logged in to Azure. Please run 'az login' first."
  exit 1
fi

# Check if jq is installed
if ! command -v jq &>/dev/null; then
  echo "Error: jq is not installed. Please install it first (e.g., 'brew install jq')."
  exit 1
fi

# Parse arguments
RESOURCE_GROUP="${1:?Error: Resource group name required}"
LOCATION="${2:-uksouth}"
API_VERSION="2024-12-01-preview"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Deploying Microsoft Foundry resources using Bicep..."
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Location: ${LOCATION}"
echo ""

# Create resource group (idempotent)
echo "Creating resource group..."
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --output none

# Deploy Bicep template
echo "Deploying Bicep template..."
DEPLOYMENT_OUTPUT=$(az deployment group create \
  --resource-group "${RESOURCE_GROUP}" \
  --template-file "${SCRIPT_DIR}/main.bicep" \
  --parameters "${SCRIPT_DIR}/main.bicepparam" \
  --parameters location="${LOCATION}" \
  --query "properties.outputs" \
  --output json)

# Extract outputs
ENDPOINT=$(echo "${DEPLOYMENT_OUTPUT}" | jq -r '.endpoint.value')
ACCOUNT_NAME=$(echo "${DEPLOYMENT_OUTPUT}" | jq -r '.accountName.value')
DEPLOYMENT_NAME=$(echo "${DEPLOYMENT_OUTPUT}" | jq -r '.deploymentName.value')

# Retrieve API key
echo "Retrieving API key..."
API_KEY=$(az cognitiveservices account keys list \
  --name "${ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "key1" \
  --output tsv)

# Print environment variables
echo ""
echo "Deployment complete! Add these to your .env file:"
echo ""
echo "AZURE_OPENAI_API_KEY=${API_KEY}"
echo "AZURE_OPENAI_ENDPOINT=${ENDPOINT}"
echo "AZURE_OPENAI_DEPLOYMENT_NAME=${DEPLOYMENT_NAME}"
echo "AZURE_OPENAI_API_VERSION=${API_VERSION}"
