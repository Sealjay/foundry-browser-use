---
applyTo: "**/*.ts,**/*.tsx"
---

# TypeScript & React Coding Standards

Follow [CLAUDE.md](../../CLAUDE.md) for core TypeScript standards (Bun, Biome, functional components, CSS modules) and [general coding guidelines](./general-coding.instructions.md) for naming and error handling.

## React Guidelines

- Follow the React hooks rules (no conditional hooks)
- Keep components small and focused
- Develop reusable components when possible

## Test-Coverage Guidelines

### Tools

- Use **`bun test`** for unit tests (Bun's native Jest-compatible test runner)
- Use **@testing-library/react** for component tests (optional - only if using React)
- Use **Playwright** for browser end-to-end tests (optional - only for automated E2E)

### Test-Writing Rules

- Unit/component tests: put files in `__tests__/` or end with `.test.ts[x]`
- Playwright specs: place in `e2e/` and end with `.spec.ts`
- Prefer behavioral assertions; avoid snapshots unless output is static
- Mock external services and side-effects, not the unit under test
- Use **msw** for HTTP mocks in unit/component tests
- Do not commit `.only`, `.skip`, or focused tests
- Keep tests deterministic; avoid real time, randomness, and live network calls

### Reporting

- Generate coverage in both `lcov` and `html` formats
- Upload the `lcov` report to the coverage service
- Exclude `coverage/` artifacts via `.gitignore`

## UI Theming Guidelines

### General Practices

- Use CSS variables for consistent and flexible theming across all components.
- Ensure responsiveness across all UI components to support various screen sizes and devices.
