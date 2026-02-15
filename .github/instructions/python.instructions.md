---
applyTo: "**/*.py"
---

# Python Project Coding Standards

Follow [CLAUDE.md](../../CLAUDE.md) for core Python standards (UV, Ruff, async/await, Pydantic, type hints) and [general coding guidelines](./general-coding.instructions.md) for naming and error handling.

## Agent Communication

- Use Agent Framework's native messaging patterns.
- Ensure proper (de)serialization of agent data.
- Include correlation IDs in all agent requests/responses.
- Use event-driven patterns to decouple agents.

## Testing

### Test Structure

- Unit tests for agents and plugins.
- Integration tests for inter-agent workflows.
- End-to-end tests for full pipelines.
- Mock all external systems (Azure OpenAI, DBs, etc.).

### AI Testing Patterns

- Use deterministic outputs for reproducibility.
- Include failure scenarios and edge cases.
- Validate prompt outputs.
- Benchmark agent response latency.

## Security and Configuration

### Environment Management

- Store sensitive data in environment variables.
- Never commit secrets or API keys.
- Use Azure Key Vault for production secrets.
- Secure all API endpoints with authentication.

### API Security

- Validate all inputs using Pydantic.
- Apply rate limiting to AI endpoints.
- Log requests for auditing.
- Enforce HTTPS on all external traffic.

## Documentation

### Agent Documentation

- Describe agent roles and capabilities.
- Provide prompt engineering guidance.
- Document inter-agent communication.
- Include troubleshooting steps for known issues.
