# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| Latest  | :white_check_mark: |

## Reporting a Vulnerability

We take security vulnerabilities seriously. If you discover a security issue, please report it responsibly.

### How to Report

1. **Do not** open a public GitHub issue for security vulnerabilities
2. Email security concerns to: [your-email@example.com]
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgement**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability and determine its severity
- **Resolution**: We aim to resolve critical issues within 7 days
- **Disclosure**: We will coordinate with you on public disclosure timing

### Scope

This security policy applies to:
- The main codebase
- Dependencies managed in this repository
- Configuration and deployment scripts

### Out of Scope

- Vulnerabilities in third-party dependencies (report these to the maintainers)
- Social engineering attacks
- Physical security issues

## Security Best Practices

When contributing to this project:

1. **Never commit secrets** - Use environment variables and `.env` files
2. **Keep dependencies updated** - Regularly run security audits
3. **Follow secure coding practices** - Validate inputs, sanitize outputs
4. **Use HTTPS** - All external communications should be encrypted
5. **Review changes** - Security-sensitive changes require additional review

## Security Features

This template includes:
- `.gitignore` configured to exclude sensitive files
- Environment variable exclusions (`.env` files in `.gitignore`)
- Dependabot configuration for automated security updates

---

*Replace `[your-email@example.com]` with your actual security contact email.*
