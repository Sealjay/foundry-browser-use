#!/usr/bin/env bash
set -euo pipefail

# Microsoft Foundry deployment script using Azure CLI
# Usage: ./deploy.sh <resource-group> [location] [account-name]
# Example: ./deploy.sh rg-browser-agent uksouth oai-foundry-browser

# Check if user is logged in to Azure
if ! az account show &>/dev/null; then
  echo "Error: Not logged in to Azure. Please run 'az login' first."
  exit 1
fi

# Parse arguments
RESOURCE_GROUP="${1:?Error: Resource group name required}"
LOCATION="${2:-uksouth}"
ACCOUNT_NAME="${3:-oai-foundry-browser}"
DEPLOYMENT_NAME="gpt-41-mini"
MODEL_NAME="gpt-4.1-mini"
MODEL_VERSION="2025-04-14"
API_VERSION="2024-12-01-preview"

echo "Deploying Microsoft Foundry resources..."
echo "Resource Group: ${RESOURCE_GROUP}"
echo "Location: ${LOCATION}"
echo "Account Name: ${ACCOUNT_NAME}"
echo "Deployment Name: ${DEPLOYMENT_NAME}"
echo ""

# Create resource group (idempotent)
echo "Creating resource group..."
az group create \
  --name "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --output none

# Create Microsoft Foundry account (idempotent)
echo "Creating Microsoft Foundry account..."
az cognitiveservices account create \
  --name "${ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --location "${LOCATION}" \
  --kind AIServices \
  --sku S0 \
  --custom-domain "${ACCOUNT_NAME}" \
  --identity-type SystemAssigned \
  --yes \
  --output none

# Deploy GPT-4.1-mini model (idempotent)
echo "Deploying ${MODEL_NAME} model..."
az cognitiveservices account deployment create \
  --name "${ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --deployment-name "${DEPLOYMENT_NAME}" \
  --model-name "${MODEL_NAME}" \
  --model-version "${MODEL_VERSION}" \
  --model-format OpenAI \
  --sku-capacity 150 \
  --sku-name "GlobalStandard" \
  --output none

# Retrieve endpoint
echo "Retrieving endpoint..."
ENDPOINT=$(az cognitiveservices account show \
  --name "${ACCOUNT_NAME}" \
  --resource-group "${RESOURCE_GROUP}" \
  --query "properties.endpoint" \
  --output tsv)

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
