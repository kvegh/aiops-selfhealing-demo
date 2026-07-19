# Inconsistencies

Cross-referencing all docs, code, and config files in the repo.

---

## 1. ✅ linux-mcp container image and config (doc 02 vs doc 04)

Doc 02 uses `quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest` with SSH config mount, env vars (`LINUX_MCP_USER=mcp`), and log directory volume. Doc 04 uses `ghcr.io/rhel-lightspeed/linux-mcp:latest` with `--host`/`--user`/`--key` CLI args and key at `/opt/tra/keys/target-key`. These are incompatible configurations for the same server.

## 2. ✅ Rulebook condition: doc 06 vs actual file vs troubleshooting

Three-way mismatch:

| Aspect | Doc 06 | Actual rulebook file | Troubleshooting doc |
|--------|--------|---------------------|---------------------|
| Field name | `event.payload.alert_name` | `event.payload.event_name` | says `event_name` is correct |
| Operator | `==` (exact match) | `is search(...)` | says use `is search()` |
| Match string | `"Linux: Zabbix agent is not available"` | `"Zabbix agent is not available"` | — |

Doc 06 is wrong on all three counts by the repo's own troubleshooting guidance and the actual deployed rulebook.

## 3. ✅ Claude CLI permission flag (doc 04 vs playbook / doc 06)

Doc 04 uses `--permission-mode bypassPermissions`. The actual playbook and doc 06 use `--dangerously-skip-permissions`. Different flags for the same purpose.

## 4. AAP PAT creation UI navigation (doc 01 vs doc 04)

| Step | Doc 01 | Doc 04 |
|------|--------|--------|
| OAuth2 App | Administration → Applications → Add | Administration → OAuth2 Applications → Add |
| PAT | Users → your user → Tokens → Add | Authorization → Personal Access Tokens → Add |

Same operation, different navigation paths described.

## 5. Heading / filename mismatches

- `04-claude-agent.md` heading says "02 – Set up Claude agent" (should be 04)
- `05-cloudcli-web-ui.md` heading says "07 – CloudCLI Web UI" (should be 05)

## 6. Inference backend (doc 04 vs doc 05)

Doc 04 uses Anthropic API direct (`ANTHROPIC_API_KEY`). Doc 05 uses Google Vertex AI (`CLAUDE_CODE_USE_VERTEX=1`). Doc 00's network table shows Anthropic API. These are mutually exclusive setups with no note explaining the difference.

## 7. Port 8448 protocol label (doc 00 vs doc 01)

Doc 00 network table labels port 8448 as "HTTP/SSE". Doc 01 uses `https://YOUR_AAP_SERVER:8448` — it is HTTPS.

## 8. Node.js version requirement (doc 04 vs doc 05)

Doc 04 says Node.js 18+. Doc 05 says Node.js v22+. Both run on the same TRA VM, so v22 satisfies both, but the stated requirement in doc 04 is misleadingly low if doc 05 components are also installed.

## 9. Doc 06 intro contradicts its own content

The intro says "No custom scripts or JavaScript required" but section 7 requires editing the media type JavaScript to add Basic Auth. The intro likely means no custom webhook scripts (vs the old approach), but the wording is misleading.

## 10. CLAUDE.md: repo file vs doc 04 template

`AI_Instructions_Guardrails/CLAUDE.md` is the battle-tested version (6 sections, ~90 lines, phase discipline, SSH alias rules, RHEL prerequisites). Doc 04 section 6 contains a completely different simplified template (4 sections, ~30 lines). The doc says "This is a starting point" but never references the actual refined version that exists in the repo.

## 11. Playbook invocation: doc 04 section 9 vs actual playbook

Doc 04 shows `${ALERT_PAYLOAD}` being interpolated into the prompt, plus `--allowedTools` and `--max-turns 25`. The actual playbook has a generic hardcoded prompt with no payload injection, no `--allowedTools`, and no `--max-turns`.
