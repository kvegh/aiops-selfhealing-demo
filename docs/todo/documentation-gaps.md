# Documentation Gaps — aiops-selfhealing-demo

Identified by cross-referencing 3-4 days of Claude Code session transcripts (Jul 14-18, 2026) against the current state of `github.com/kvegh/aiops-selfhealing-demo`.

---

## 1. ✅ Demo scenarios / walkthrough (README says TBD)

*Added Demo scenarios section to README after the core-idea diagram. Stage 1 flow documented, Stage 2 marked TBD. Removed old TBD section.*

The self-healing demo was run successfully multiple times with a well-established flow:

1. Break testserver1 (remove `zabbix-agent2` package)
2. Zabbix detects agent unavailability after `{$AGENT.NODATA_TIMEOUT}`
3. Zabbix fires alert via Event-Driven Ansible media type to EDA Event Stream
4. EDA rulebook matches trigger name, runs AAP job template
5. AAP job template invokes Claude Code CLI in headless mode
6. Claude investigates via Phase 1-4 (Zabbix MCP, linux-mcp, AAP MCP)
7. Claude launches "Deploy Zabbix Agent" via AAP MCP
8. Zabbix confirms recovery after retry backoff expires

This is fully proven but nowhere documented as a runnable scenario. The README Stage 1 / Stage 2 sections are still TBD.

## 2. ✅ AAP API token creation (doc 01 sections 6-7 say TBD)

*Backfilled section 6 in docs/01-aap-mcp.md: OAuth2 Application + PAT creation steps, RBAC note.*

The procedure was worked out during sessions: create an OAuth2 Application in AAP, then create a Personal Access Token (Write scope). Never backfilled into `docs/01-aap-mcp.md`.

## 3. ✅ Connecting Claude Code CLI to AAP MCP (doc 01 says TBD)

*Section 7 in docs/01-aap-mcp.md: cross-reference to docs/04-claude-agent.md section 3 (config lives there).*

The full `~/.claude.json` MCP config with HTTP transport and bearer token is covered in `docs/04-claude-agent.md`, but `docs/01-aap-mcp.md` sections 6-7 remain TBD. Either backfill or add a cross-reference.

## 4. ✅ Troubleshooting catalog

*Created docs/troubleshooting.md with all 10 items, grouped by component.*

Significant troubleshooting knowledge accumulated across sessions, not captured anywhere:

- **Rulebook path**: must be `extensions/eda/rulebooks/`, not `eda/` -- project scanner won't find them otherwise.
- **YAML quoting**: colon-space in rulebook condition strings causes parse errors -- must single-quote.
- **Rulebook condition matching**: use `is search()` not `==` for Zabbix trigger names (dynamic `(for 3m)` suffix).
- **Zabbix payload field name**: `event_name`, not `alert_name`.
- **Event Stream "Forward events"**: toggle must be enabled or Event Stream appears grayed out.
- **AAP 2.7 API path**: `/api/controller/v2/` not `/api/v2/` -- wrong path causes 404.
- **Zabbix media type URL split**: Send-to field = hostname only, endpoint parameter = path. The media type JavaScript concatenates them.
- **Activation source mapping is hash-based**: changing the rulebook requires deleting and recreating the activation.
- **Systemd unit files persist after `dnf remove`**: never trust systemd `loaded` state to mean the package is installed. Always verify the binary exists.
- **AAP MCP write limitations**: no `projects_create`, no `inventories_create`, no EDA-specific endpoints. Many setup steps cannot be done autonomously.

## 5. Zabbix host/trigger/template setup for the target VM

Nowhere documented how testserver1 was added to Zabbix, which templates are linked, or what triggers are configured. The demo assumes this exists but doesn't explain how to set it up.

## 6. Fault injection method ("break" script)

Multiple sessions reference packages being removed from testserver1 to trigger the demo. The actual mechanism (cron, manual `dnf remove`, or a dedicated script) is never documented. A reproducible demo needs this.

## 7. Incident memory MCP (`@modelcontextprotocol/server-memory`)

Listed in the architecture and in `docs/04-claude-agent.md` MCP config, but no dedicated setup doc exists. The doc series goes 00-06 with no memory MCP doc.

## 8. AAP credential security model

Sessions discussed how AAP never exposes credentials post-creation (`$encrypted$` returned for all sensitive fields), `no_log` protection at max verbosity, and runtime-only injection into the execution environment. Relevant for the "Trusted Execution Layer" narrative but undocumented.

## 9. EDA concept mapping for AAP users

Sessions established clear equivalences useful as orientation content:

| EDA concept | AAP Controller equivalent |
|---|---|
| Rulebook Activations | Job Templates |
| Decision Environments | Execution Environments |
| Rule Audit | Jobs overview |
| Projects | Projects (1:1) |

## 10. Autonomous setup feasibility / MCP tool coverage gaps

Sessions explicitly assessed what Claude cannot do autonomously today:

- Zabbix MCP is read-only (no media type, user, or action creation)
- AAP MCP lacks EDA-specific endpoints (Event Streams, Rulebook Activations, source mappings)
- Several AAP EDA steps are UI-only (source mapping gear icon, Forward events toggle)

This is architecturally significant -- it defines the boundary of what the demo can self-configure vs what requires human setup. Undocumented.

## 11. Level 0 vs Level 1 EDA routing

The four-level escalation model is documented in the README, but the actual EDA routing logic to differentiate Level 0 (deterministic fix, no AI) from Level 1+ (AI-driven) is not implemented or documented. How does the rulebook decide whether a known issue gets a direct `run_job_template` fix vs escalation to Claude? This is an open design question that should at least be captured.

## 12. Zabbix media type Basic Auth JavaScript modification

The stock Zabbix "Event-Driven Ansible" media type ships without authentication headers. To work with AAP Event Streams (which require Basic Auth), a specific JS line must be added to the media type script:

```javascript
request.addHeader('Authorization: Basic ' + btoa(Eda.params.eda_username + ':' + Eda.params.eda_password));
```

This was a hard-won troubleshooting finding. `docs/06-eda-zabbix-integration.md` may already cover this, but it should be verified as a prominently called-out step, not buried.

## 13. Playbook design rationale (`run_claude_analyse_fix.yml`)

The playbook uses specific patterns that are non-obvious and worth documenting:

- **`ansible.builtin.shell`** (not `command` or `script`): `command` doesn't handle quoted arguments in the Claude CLI invocation correctly. `script` is overkill for a single command.
- **`become: true` / `become_user: aaptra`**: Controller connects to the host as the `ansible` user, but Claude Code must run as `aaptra` (owns the `~/.claude` config, API keys, MCP wiring, and working directory).
- **`chdir: /home/aaptra/claude-wd`**: Claude Code needs a working directory with `CLAUDE.md` guardrails and project context.

## 14. Claude headless transcript behavior

When Claude Code runs in pipe mode (`claude -p`), it creates a JSONL transcript file with a UUID under `~/.claude/projects/.../`, but these sessions are **not** listed by `claude --resume`. This is expected behavior (not a bug) but important operational knowledge when debugging AAP-triggered runs or reviewing what the agent did.

## 15. Zabbix EDA documentation update suggestion

Zabbix's official EDA integration docs describe the old approach (raw `ansible.eda.webhook` port listeners) but do not mention AAP 2.7 Event Streams. The Event Streams approach is significantly better (managed URLs through the AAP gateway with TLS and auth, no need for separate ports or users per rulebook). A documentation update suggestion to the Zabbix project would be valuable.

## 16. Level 2 experimental agent-authored automation

The README describes Level 2 as "experimental agent-authored automation (marked experimental)" but nothing defines what this means in practice -- how would Claude author a new playbook, how would it be reviewed, where would it be stored, how is it marked as experimental? This level is part of the architecture but completely undefined.

## 17. Apache / httpd remediation gap

Multiple demo runs discovered that httpd was also down on testserver1 (package removed alongside zabbix-agent2), but no AAP job template exists to remediate it. Claude correctly identified this and escalated. If the demo scenario includes Apache being broken, this is a known gap in remediation coverage that should be documented -- either as a deliberate "escalation to human" example or as a TODO to create the job template.

## 18. Playbook verification strategy

Sessions established three approaches for how Claude verifies a job template is the right one before launching it:

1. Review job events from past successful runs of the same template
2. Read playbook source files via linux-mcp on the AAP host
3. Git clone the repo locally to inspect source

This is operationally important (launching the wrong template could make things worse) and is not documented as part of the investigation methodology.

## 19. Operational improvements identified during demo runs

Incident reports from demo runs consistently recommended the same improvements that are not captured anywhere as known limitations or next steps:

- **Package-level monitoring in Zabbix**: detect package removal directly, not just service failure (faster detection, clearer root cause)
- **Grant mcp user `systemd-journal` group membership**: journal logs were inaccessible during investigations, forcing fallback to DNF logs
- **Audit monitoring templates against host roles**: Apache monitoring template was linked to testserver1 but httpd was never part of the intended role
- **Investigate recurring package removal pattern**: DNF logs showed repeated install/remove cycles over multiple days

## 20. Demo scope disclaimer in the repo

The repo has no explicit statement that this is a **functionality demo**, not a production reference architecture. No attempt is made to follow least-privilege, security hardening, or production-grade guidelines -- that is intentional and out of scope. This was clarified in project memory during this session but is not stated anywhere in the README or docs. Anyone cloning the repo should understand this upfront.
