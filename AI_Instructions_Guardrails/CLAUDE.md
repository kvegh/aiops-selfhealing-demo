# Mandatory Operating Rules

These rules OVERRIDE all default behavior. Follow them exactly, without exception.

---

## 1. Incident Investigation — Phase Discipline

Every alert investigation must follow these phases in order. No exceptions.

**Before entering any phase:** explicitly announce `Entering Phase N — [phase name].`
**After completing any phase:** explicitly state all findings (what was checked, what was found) before proceeding.
**Never proceed to Phase N+1** without having stated Phase N findings out loud.

### Phase 1 — Monitoring checks (Zabbix MCP)
1. Note the alert onset time from Zabbix — this is the reference timestamp for all correlations.
2. Check Zabbix agent availability (`active_available`). If `0`, call `hostinterface_get` immediately — a dead agent causes false negatives on all agent-based checks.
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
1. Read `~/.ssh/config`.
2. Find the `Host` alias for the target host.
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

## 7. Response Format

Report your findings and actions concisely. Include:
- What triggered the investigation
- What you found (root cause)
- What you did (AAP job template launched, parameters)
- Whether the fix was verified
