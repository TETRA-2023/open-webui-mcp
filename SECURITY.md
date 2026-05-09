# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability:

1. **DO NOT** open a public GitHub issue.
2. Email the maintainers directly with details and reproduction steps.

We aim to acknowledge within 48 hours and patch critical issues within 7 days. For vulnerabilities in the underlying wrapper logic (anything under `src/openwebui_mcp/`), please also report upstream to https://github.com/stephanschielke/open-webui-mcp-server — we vendor that source verbatim.

## Security considerations

- **API keys**: Never commit `.env` files or `WEBUI_API_KEY` values. Inject them through your platform's secrets-management mechanism (Docker secrets, Kubernetes secrets, your orchestrator's env-injection, etc).
- **Tool surface**: this image exposes 317 OpenWebUI admin operations (150 POST · 143 GET · 24 DELETE) — including destructive ones — by design. Gate it with deployment-time controls (gateway team-scope + bearer middleware, an mTLS proxy, or equivalent). Do not run this image with `WEBUI_URL` pointing at a multi-tenant or production OWUI without those controls in place.
- **Transport**: when deploying with `MCP_TRANSPORT=http`, place the server behind an authenticating gateway (bearer / mTLS / equivalent). Do not expose port 7999 directly to untrusted networks.
- **Bearer rotation**: rotate `WEBUI_API_KEY` on a regular cadence (annual rotation is a reasonable default). Record rotations in your secrets-management audit trail.
- **Spec drift**: the bundled OpenAPI snapshot governs which tools the wrapper advertises. If it drifts from the running OpenWebUI's actual API, tool calls can fail in surprising ways (advertised schemas no longer match live endpoints). Run `scripts/check-spec-drift.sh` before every OWUI bump and re-pin the wrapper as needed (see CONTRIBUTING.md).
