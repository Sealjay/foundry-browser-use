// Microsoft Foundry deployment using Bicep

@description('Name of the Microsoft Foundry account')
param accountName string = 'oai-foundry-browser'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Name of the model deployment')
param deploymentName string = 'gpt-41-mini'

@description('SKU capacity for the deployment')
param skuCapacity int = 150

// Microsoft Foundry account
resource foundryAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    customSubDomainName: accountName
    disableLocalAuth: false
    publicNetworkAccess: 'Enabled'
    allowProjectManagement: true
  }
}

// GPT-4.1-mini deployment
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: foundryAccount
  name: deploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: skuCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2025-04-14'
    }
  }
}

// Outputs
@description('The endpoint of the Microsoft Foundry account')
output endpoint string = foundryAccount.properties.endpoint

@description('The name of the Microsoft Foundry account')
output accountName string = foundryAccount.name

@description('The name of the model deployment')
output deploymentName string = modelDeployment.name
