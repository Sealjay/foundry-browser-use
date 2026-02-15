---
applyTo: "**"
---

# Project general coding standards

Follow the standards defined in [CLAUDE.md](../../CLAUDE.md) as the single source of truth for this project's conventions, including repository structure, commit conventions, and pre-commit checklist.

## Naming Conventions

### TypeScript/React
- Use PascalCase for component names, interfaces, and type aliases
- Use camelCase for variables, functions, and methods
- Prefix private class members with underscore (\_)
- Use ALL_CAPS for constants

### Python
- Use snake_case for variables, functions, and methods
- Use PascalCase for class names
- Use ALL_CAPS for constants
- Prefix private class members with underscore (\_)
- Use descriptive names for AI agents and plugins

## Error Handling

### General Principles
- Use appropriate exception handling for each language (try/catch in TypeScript, try/except in Python)
- Implement proper error boundaries in React components
- Always log errors with contextual information
- Include correlation IDs for tracing across services
- Use structured error responses for API endpoints

### AI-Specific Error Handling
- Handle AI service timeouts and rate limiting gracefully
- Implement fallback responses for AI failures
- Log AI token usage and costs with errors
- Provide user-friendly error messages for AI-related failures

## Answering Questions

- Answer all questions in the style of a friendly colleague, using informal language.
