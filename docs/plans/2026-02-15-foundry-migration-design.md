# Migrate IaC and docs from Azure OpenAI to Microsoft Foundry

**Date:** 2026-02-15
**Status:** Approved

## Summary

Update all infrastructure-as-code and documentation to deploy a Microsoft Foundry resource (`kind: AIServices`) instead of a standalone Azure OpenAI resource (`kind: OpenAI`). No Python code changes required - the existing Azure OpenAI endpoint and API key auth continue to work with a Foundry resource.

## Changes

### IaC

**`infra/main.bicep`**
- Change `kind` from `'OpenAI'` to `'AIServices'`
- Add `allowProjectManagement: true` to properties
- Add `identity: { type: 'SystemAssigned' }`
- Add `customSubDomainName` to properties

**`infra/deploy.sh`**
- Change `--kind OpenAI` to `--kind AIServices`
- Add `--custom-domain` parameter
- Add `--identity-type SystemAssigned`
- Update comments and echo text

**`infra/deploy-bicep.sh`**
- Update comments and echo text from "Azure OpenAI" to "Microsoft Foundry"

### Documentation

**`CLAUDE.md`**
- Update project description to reference Foundry
- Update architecture section references

**`README.md`**
- Update "Deploy Azure infrastructure" section wording
- Update prerequisites to mention Foundry
- Keep `.env` variable names unchanged

### Unchanged files
- `.env.example` - variable names still work with Foundry
- `agent.py`, `browse.py`, `run_task.py` - no code changes
- `infra/teardown.sh` - still deletes a resource group
- `infra/main.bicepparam` - no changes

## Key decisions

- Keep `disableLocalAuth` as `false` so API key auth continues to work
- The `*.openai.azure.com` endpoint format still works post-upgrade
- Add managed identity even though Entra-only auth is not required - it is a prerequisite for Foundry features
- Full replacement, no parameterised OpenAI/Foundry toggle - rollback is supported via Azure portal

## References

- [Upgrade from Azure OpenAI to Microsoft Foundry](https://learn.microsoft.com/azure/ai-foundry/how-to/upgrade-azure-openai?view=foundry-classic)
- [Deploy models using Azure CLI and Bicep](https://learn.microsoft.com/azure/ai-foundry/foundry-models/how-to/create-model-deployments?view=foundry-classic)
- [Create a Foundry resource using Bicep](https://learn.microsoft.com/azure/ai-foundry/how-to/create-resource-template?view=foundry-classic)
