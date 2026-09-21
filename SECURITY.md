# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in Intelligent ML Studio, please report it privately:

1. **Email**: security@mlstudio.io
2. **Details to include**:
   - Component affected (`backend/api`, `worker`, `auth`, `storage`, etc.)
   - Steps to reproduce the issue
   - Proof of Concept (PoC) if applicable
   - Potential impact assessment

Please do **NOT** disclose vulnerabilities publicly on GitHub issues or forums until a fix has been released.

## Security Architecture Highlights

- **Server-Side Token Revocation**: Logout instantly hashes and records refresh tokens in the `revoked_tokens` table.
- **HMAC Manifest Signing**: Model artifacts are signed with HMAC-SHA256 upon creation and verified before deserialization.
- **Four-Eyes Governance**: Separation-of-duties (`approved_by != created_by`) is enforced before any model can be deployed.
- **Sliding-Window Rate Limiting**: Production inference endpoints are protected against flood/abuse.
- **Isolated Process Workers**: ML tasks run in isolated worker processes with hard execution timeouts.
