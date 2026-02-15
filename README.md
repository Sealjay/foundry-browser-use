# [Your Project Name]

> [Brief description of your project - replace this placeholder]
<!-- Lang badges -->
[![Python](https://img.shields.io/badge/--3178C6?logo=python&logoColor=ffffff)](https://www.python.org/)
[![TypeScript](https://img.shields.io/badge/--3178C6?logo=typescript&logoColor=ffffff)](https://www.typescriptlang.org/)
[![Bun](https://img.shields.io/badge/--3178C6?logo=bun&logoColor=ffffff)](https://bun.sh/)

<!-- Cloud badges -->
[![Azure](https://img.shields.io/badge/--3178C6?logo=microsoftazure&logoColor=ffffff)](https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/?WT.mc_id=AI-MVP-5004204)

![GitHub issues](https://img.shields.io/github/issues/your-username/your-repo-name)
![GitHub](https://img.shields.io/github/license/your-username/your-repo-name)
![GitHub Repo stars](https://img.shields.io/github/stars/your-username/your-repo-name?style=social)

## Overview
Describe the project in more detail.

This repository is designed to be compiled and deployed to [Azure Static Web Apps](https://docs.microsoft.com/en-us/azure/static-web-apps/deploy-nextjs?WT.mc_id=AI-MVP-5004204).

## Template Setup

This template includes configuration for Python and TypeScript. After creating a project from this template, **remove what you don't need**:

| If not using... | Remove these files |
|-----------------|-------------------|
| Python | `pyproject.toml` |
| TypeScript/JavaScript | `package.json`, `biome.json` |

### Tech Stack

| Language | Package Manager | Linter/Formatter | Test Runner |
|----------|-----------------|------------------|-------------|
| Python | [UV](https://github.com/astral-sh/uv) | [Ruff](https://github.com/astral-sh/ruff) | pytest |
| TypeScript | [Bun](https://bun.sh/) | [Biome](https://biomejs.dev/) | `bun test` |

## Getting Started

Install the required tools (Bun, UV) and run the commands below.

### TypeScript/JavaScript

```bash
# Install dependencies
bun install

# Run tests
bun test

# Lint and format
bun run format
```

### Python

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Lint and format
uv run ruff check . --fix
uv run ruff format .
```

## Licensing

[Your Project Name] is available under the [MIT License](./LICENSE) and is freely available to End Users.

## Solutions Referenced

<!-- Add links to components you have used, or delete this section -->
- [Infrastructure as code in Bicep](https://docs.microsoft.com/en-us/azure/azure-resource-manager/bicep/overview?WT.mc_id=AI-MVP-5004204)

## Documentation
The `docs` folder contains [more detailed documentation](./docs/start-here.md), along with setup instructions.

## Contact

Feel free to contact me [on LinkedIn](https://linkedin.com/in/your-linkedin-username/). For bugs, please [raise an issue on GitHub](https://github.com/your-username/your-repo-name/issues).

## Contributing

Contributions are more than welcome! This repository uses [GitHub flow](https://guides.github.com/introduction/flow/) with conventional commits.
