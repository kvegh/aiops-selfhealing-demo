# Mandatory Operating Rules

These rules OVERRIDE all default behavior. Follow them exactly, without exception.

---

## 1. Incident Investigation — Phase Discipline

Every alert investigation must follow these phases in order. No exceptions.

**Before entering any phase:** explicitly announce `Entering Phase N — [phase name].`
**After completing any phase:** explicitly state all findings (what was checked, what was found) before proceeding.
**Never proceed to Phase N+1** without having stated Phase N findings out loud.

**Phase findings display rule (mandatory, every phase including Phase 4):**
At runtime — live, immediately when a phase's last check returns, as its own output message, BEFORE the next phase announcement or any further tool call — display a findings-and-conclusions block:

```
**Phase N findings — [phase name]:**
- <item checked>: <result>
- ...

**Phase N conclusion:** <what this phase established and what it means for the next phase>
```

- Both parts are mandatory every time: findings (what was checked, what was found) AND conclusion.
- Retroactive summaries at the end of the run do NOT satisfy this rule. The block must appear in the live output between phases.
- Sequence is always: `Entering Phase N` → checks → Phase N findings + conclusion → `Entering Phase N+1`.

- Phase 4 is no exception: after remediation verification, display the Phase 4 block (job ID/result, host state, Zabbix state, recovery timestamp, ticket action) *before* writing the report.
- The final incident report MUST include a "Phase summaries" section repeating every phase block, in addition to root cause, evidence, remediation and next steps.
- If a phase is repeated in cycle 2, label blocks `Phase N findings (cycle 2)`.

**Phase block length (mandatory):**
- Findings: max 8 bullets, one line each (~120 chars), format `<check>: <result>`.
  Results only — no raw output, epochs, IDs or file listings unless needed for correlation.
- Suspicions are wanted: one line each, prefixed `Suspicion:`.
- Conclusion: max 2 sentences — what is established, what it means for the next phase.
- Don't cite which rule a check satisfies ("per §3") — just give the result.
- Phase 4 block follows the same limits; full detail belongs in the final report only.

### Phase 1 — Monitoring checks (Zabbix MCP)
1. Note the alert onset time from Zabbix — this is the reference timestamp for all correlations.
2. Read the host's agent availability and interfaces with `host_get` and `extra_params: {"selectInterfaces": "extend"}`. Unknown active-check availability alone does not prove a passive agent is dead; check the interface and fresh item evidence.
3. Check network/ICMP reachability in Zabbix.
4. Check TCP service port status.
5. Check application-level functionality per the monitoring template.
6. Correlate all other active problems on this host and related hosts.

### Phase 2 — Host checks (linux-mcp)
1. Verify host reachability via linux-mcp.
2. Check service status (`get_service_status`, `list_services`).
3. Check port listening (`get_listening_ports`).
4. Verify software is installed — always do this when a service is dead. Do NOT trust systemd's `loaded` state; unit files persist after package removal if `daemon-reload` was not run.
5. Read service logs (`get_service_logs`, `get_journal_logs`). Cross-reference timestamps against the Zabbix alert onset time.
6. Check dependencies, disk, memory, permissions, SELinux if logs point there.

### Phase 3 — AAP context check (AAP MCP)
1. Check recent AAP job runs — did any job execute close to the alert onset time?
2. Correlate job completion timestamps against the Zabbix alert onset time.

### Phase 4 — Remediation (AAP only)
1. Identify whether an existing AAP job template can fix the root cause.
2. If yes: launch via AAP. Wait for completion.
3. Wait up to 80 seconds for Zabbix to reflect the state change.
4. If monitoring confirms recovery: close the ticket. Done.
5. If problem persists: restart from Phase 1 with new information.

### Loop limit
Maximum 2 complete cycles. If the problem persists after 2 cycles: generate a full report and escalate. Do not attempt further autonomous fixes.

---

## 2. Remediation Constraint — AAP Only

**All changes MUST be made through AAP job templates. No exceptions.**

- No direct host modifications (no SSH commands to the user, no manual service restarts).
- No direct Zabbix API changes as a fix (Zabbix MCP is for investigation only).
- Investigation tools: Zabbix MCP, linux-mcp, AAP MCP — all read-only for diagnosis.

---

## 3. linux-mcp — SSH Alias Rule

Before calling any linux-mcp tool with a remote `host` parameter:
1. Use the selected SSH alias supplied by the launcher after it verifies the installed MCP SSH configuration. If no verified alias was supplied, inspect the applicable SSH configuration before proceeding.
2. Match the alias to the selected target host; do not guess another host.
3. Pass the alias as `host`, not the raw IP.

**Why:** linux-mcp uses `~/.ssh/config` for connection resolution. A raw IP bypasses the config, causing authentication failures.

---

## 4. linux-mcp — RHEL Prerequisites

When using linux-mcp on RHEL hosts:
- `~/.ssh/crt` must exist on the MCP host (can be empty).
- `LINUX_MCP_ALLOWED_LOG_PATHS` controls which log files `read_log_file` can access.
- The `mcp` user must be in the `systemd-journal` group for `get_journal_logs` to work.
- RHEL log files are `root:root 600` — `adm` group membership does NOT grant read access. Use `read_file` on world-readable logs or set an explicit ACL (`setfacl -m u:mcp:r /var/log/messages`).

---

## 5. Memory Hygiene

Do not save memories that reference specific hostnames, IP addresses, software package names, service names, or past incidents.

**Rule:** Before saving any memory, ask: does this rule apply only because of a specific host, software, or past event? If yes, generalize it or do not save it.

**Why:** Memories must remain universally applicable. Specifics belong in the incident record.

---

## 6. Alerts Are Symptoms

Treat Zabbix alert names as symptoms, not root causes. Always investigate host agent availability and interface status before concluding on root cause. Never act on the alert name alone.

---

## 7. Headless Runs — Phase Output Must Be Visible

When Claude CLI runs non-interactively (`claude -p`, e.g. launched by EDA/AAP), the default `--output-format text` prints ONLY the final message. Phase findings/conclusion blocks emitted between phases are lost, which violates Section 1.

**Rule:** Any automation that launches Claude CLI for incident investigation MUST:
1. Use `claude -p --output-format stream-json --verbose` so intermediate phase announcements, findings and conclusions are retained in their original order.
2. Render the assistant messages and final report into readable AAP job output. The bounded functionality demo may display that ordered evidence when the job completes; live UI streaming is a separate feature.

When creating, reviewing or modifying such a launcher (playbook, job template, EDA rulebook, wrapper script), verify these flags are present. If they are missing, flag it and fix it via the source repo / AAP — never silently accept final-only output.

---

## 8. Response Format

Report your findings and actions concisely. Include:
- What triggered the investigation
- What you found (root cause)
- What you did (AAP job template launched, parameters)
- Whether the fix was verified
