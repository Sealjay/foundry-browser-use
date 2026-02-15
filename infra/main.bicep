// Azure OpenAI deployment using Bicep

@description('Name of the Azure OpenAI account')
param accountName string = 'oai-foundry-browser'

@description('Location for all resources')
param location string = resourceGroup().location

@description('Name of the model deployment')
param deploymentName string = 'gpt-41-mini'

@description('SKU capacity for the deployment')
param skuCapacity int = 150

// Azure OpenAI account
resource openAIAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: 'Enabled'
  }
}

// GPT-4.1-mini deployment
resource modelDeployment 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: openAIAccount
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
@description('The endpoint of the Azure OpenAI account')
output endpoint string = openAIAccount.properties.endpoint

@description('The name of the Azure OpenAI account')
output accountName string = openAIAccount.name

@description('The name of the model deployment')
output deploymentName string = modelDeployment.name
