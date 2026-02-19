# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by creating a private security advisory on GitHub or contacting the repository maintainers directly.

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

Do NOT open a public GitHub issue for security vulnerabilities.

---

## Security Best Practices

### 1. API Key Management

**CRITICAL**: Never commit API keys to version control.

```bash
# Store in config file with restricted permissions
chmod 600 ~/.hive/config.json
```

- Store API keys in `~/.hive/config.json` with permissions `0600`
- Use separate API keys for development and production
- Rotate API keys regularly
- Set spending limits on LLM API providers

### 2. Channel Access Control

Always configure `allowFrom` for all enabled channels.

```json
{
  "channels": {
    "telegram": {
      "enabled": true,
      "token": "YOUR_BOT_TOKEN",
      "allowFrom": ["123456789"]
    }
  }
}
```

- Empty `allowFrom` allows **all** users — only safe for local testing
- The Telegram bot is allowlisted to the owner only by default

### 3. Shell Command Execution

The `exec` tool executes host shell commands as root. This is intentional for VPS management.

- Review all tool usage in `gateway.log`
- The Queen has `exec` (host shell, root) — Workers do NOT
- Workers are sandboxed via Docker (`docker_exec`): no host filesystem access, no spawning

### 4. Docker Sandbox (S3)

Code execution via `docker_exec` is isolated:

- Ephemeral containers — destroyed after each run
- Non-root user inside container (`worker`, uid 1000)
- Resource limits: `--memory 512m --cpus 1.0`
- AST filter catches sandbox-escape attempts before container starts
- `--security-opt no-new-privileges`
- Host filesystem not mounted (only `/sandbox`)

### 5. WhatsApp Bridge

- Bridge binds to `127.0.0.1:3001` (localhost only)
- Set `bridgeToken` in config to enable shared-secret auth between Python and Node.js
- Auth data stored in `~/.hive/whatsapp-auth` (keep at mode 0700)
- WhatsApp channel is deprioritized — do not enable in production without review

### 6. Data Privacy

- Chat history stored locally in `~/.hive/sessions/`
- LLM providers see prompts — review their privacy policies
- PII stays on server — never pass personal data to external web tools or spawn calls
- Logs may contain sensitive content — secure `gateway.log` appropriately

### 7. Secrets Audit

```bash
# Check for accidentally committed secrets
git log --all -p | grep -E '(AIzaSy|bot[0-9]+:|github_pat_)'
```

Never commit secrets — not even in commit messages.

### 8. Dependency Security

```bash
# Python
pip install pip-audit && pip-audit

# Node.js (WhatsApp bridge)
cd bridge && npm audit
```

Keep `litellm` updated — it wraps all LLM provider calls.

---

## Known Limitations

- **Runs as root** — intentional for VPS self-management; mitigated by Docker sandboxing for code
- **No rate limiting** — single-user deployment; add if exposing to multiple users
- **Plain text config** — `~/.hive/config.json` is plain text; protect the file with OS permissions
- **No session expiry** — sessions persist indefinitely; manage manually if needed

---

## Security Checklist

Before going live:

- [ ] `~/.hive/config.json` permissions: `chmod 600 ~/.hive/config.json`
- [ ] `allowFrom` configured for all enabled channels
- [ ] Telegram bot token not committed to git
- [ ] LLM provider API key not committed to git
- [ ] `bridgeToken` set if WhatsApp bridge is running
- [ ] `gateway.log` not world-readable
- [ ] Dependencies audited: `pip-audit` + `npm audit`

---

**Last Updated:** 2026-02-19
