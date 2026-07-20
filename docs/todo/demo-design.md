# Demo Design — TODO

## Level 0 → Level 1 escalation scenario

Add a demo scenario where a known-issue fix (Level 0) fails, causing automatic escalation to Level 1 (AI agent). To keep the demo snappy, shorten Zabbix check intervals on the relevant items to 10-30 seconds — EDA reacts near-instantly once the event re-fires.

## Level 2 — job template factory

A meta job template that creates other job templates: accepts playbook name, inventory, credentials as extra vars, uses `ansible.controller.job_template` to create the JT. The agent can launch this through MCP like any other template — keeps Level 2 entirely within the Trusted Execution Layer.

Open questions: where does the agent-authored playbook get stored (dedicated repo, branch, directory)? How is it marked as experimental / agent-generated so it's distinguishable from human-authored content?

## Level 2 — approval gate for agent-authored content

Open question: how do we decide whether agent-created content (playbook + job template) is safe to execute? The second reviewer agent checks for sanity and policy compliance, but what are the actual criteria? What constitutes a pass vs. a fail? This needs to be untangled before Level 2 is demonstrable.

## Incident memory MCP

Add `@modelcontextprotocol/server-memory` (or similar) so the agent can record what it learns across incidents — root causes, resolution steps, patterns. This would build a persistent knowledge base the agent can consult during future investigations. Currently not wired up; needs design decisions on storage location, retention, and whether the agent should read past incidents to inform current diagnosis.

## Apache remediation scenario

httpd was found broken on the target host during demo runs (package removed alongside zabbix-agent2). No AAP job template exists to remediate it — Claude correctly identified the issue and escalated. Decide: is this a deliberate Level 3 "escalation to human" example, or should a remediation job template be created to make it a Level 1 self-healing scenario?

## Package-level monitoring in Zabbix

Detect package removal directly rather than waiting for service failure. Faster detection, clearer root cause — the agent currently has to deduce that a missing package is the cause rather than seeing it as the alert.

## Grant mcp user systemd-journal group membership

Journal logs were inaccessible during agent investigations, forcing fallback to DNF logs. Adding the mcp user to the `systemd-journal` group would give the agent direct access to journal output via linux-mcp.

## Audit monitoring templates against host roles

The Apache by HTTP template was linked to testserver1 but httpd was never part of the intended host role. Monitoring templates should match the actual service inventory of each host to avoid false alerts and wasted investigation time.

## AAP as fallback information gatherer

Where no MCP interface exists for a system, the automation platform could be triggered to gather the information instead. Extends the agent's diagnostic reach without adding new direct interfaces.

## Playbook invocation tuning

The current playbook uses a generic prompt and minimal flags. Future refinements:

- **Alert payload injection:** pass `{{ extra_vars }}` into the prompt so the agent gets alert details directly instead of discovering them via Zabbix MCP
- **`--allowedTools "aap,linux-mcp,zabbix,Read"`:** restrict the agent to MCP tools only, preventing use of Bash/Edit/Write
- **`--max-turns 25`:** cap agent loops to prevent runaway execution
- **`--output-format json`:** machine-readable output for downstream parsing
- **Stderr logging:** `2>/opt/tra/logs/agent-$(date +%Y%m%d-%H%M%S).log`

## ITSM integration

The architecture diagram shows ITSM (incident record and CMDB updates) as a target of the Trusted Execution Layer, but no ITSM system is wired up in the demo yet.
