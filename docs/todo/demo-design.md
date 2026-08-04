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
- **Stderr logging:** `2>~/claude-wd/logs/agent-$(date +%Y%m%d-%H%M%S).log`

## Demo trigger via AAP (no shell access needed)

Create an AAP workflow template that stages the demo incident end-to-end: node 1 removes zabbix-agent2 from the target host, node 2 deletes node 1's job record via the AAP API so the agent doesn't see AAP caused the outage. This lets SSPs run the demo entirely through the AAP UI without needing SSH access to the target host. The workflow template name should be innocuous (e.g. "Scheduled Maintenance") so Claude doesn't connect it to the incident if it appears in the job history.

## Shorten Zabbix reaction times for demos

The default `{$AGENT.TIMEOUT}` is 3 minutes. Override it at host level (host → Macros tab) if needed. Also verify the `agent.ping` item interval is short enough (default 1m is fine). Check that the trigger action has no "problem duration" condition adding extra delay. Document the recommended demo values in doc 00.

## ITSM integration

The architecture diagram shows ITSM (incident record and CMDB updates) as a target of the Trusted Execution Layer, but no ITSM system is wired up in the demo yet.

## CloudCLI lifecycle — replace linger with an AAP-started service

The original design ran CloudCLI with no linger: the systemd user service started at SSH login and died at last logout, so nothing listened on port 3001 between demos. That breaks for users who only ever reach the demo through a browser — they have no SSH session to keep the user manager alive — so linger was enabled to keep the service up.

Linger works, but it is a weaker posture: the UI is now continuously exposed rather than only during supervised demo windows, and CloudCLI access needs more protection than it currently has. Note in particular that the htpasswd perimeter does not cover `/api/` (see the split-auth table in doc 05) — it guards the page shell only, while the API is left to CloudCLI's own single-user login.

**Proposed direction:** start CloudCLI from an AAP job template instead of running it permanently. Users authenticate to AAP with their own accounts, which gives named authentication and an audit record of who started it and when, rather than one shared password. Scope this to a team with execute permission on exactly that one job template — not general AAP access, which would trade one exposure for a larger one.

**Implementation gotcha:** an AAP job that becomes `aaptra` cannot start a systemd *user* service. sudo creates a login shell, not a PAM/logind session, so `user@.service` is never triggered — the same gotcha already documented in doc 05 for EDA-driven headless runs. Two ways around it:

- **Convert `cloudcli` to a system unit with `User=aaptra`**, started by root with a plain `systemctl start cloudcli`. Preferred: it removes the `--machine=aaptra@.host` dance and the linger question entirely. The user-service design made sense when the lifecycle was tied to a human's SSH login; once it is tied to a job, a system unit is simpler.
- Keep the user unit and have the job toggle `loginctl enable-linger` / `disable-linger` around it.

**Auto-stop is required, not optional** — everyone will forget to stop it, and the setup drifts back to always-on within weeks. Keep `RuntimeMaxSec=10h` as a backstop and/or add a scheduled stop job with a shorter cap.

Open question: AAP would gate *starting* CloudCLI, not *using* it. Once running, it is still one htpasswd password and one CloudCLI login shared by everyone — named accountability at launch, anonymous at use.

## CloudCLI troubleshooting section — consistency pass

`docs/troubleshooting.md` gained a CloudCLI access section that does not yet match the rest of the docs. Outstanding items:

- **Linger contradiction.** The section calls linger "required"; doc 05 documents no-linger as a deliberate security posture. Both docs need to reflect whatever lifecycle is settled on above, with the trade-off stated rather than left implicit.
- **Linger does not override `RuntimeMaxSec=10h`.** The "verify unattended" `curl` can return 200 right after logout and fail the next morning for an unrelated reason. Worth a sentence.
- **"Disconnected" is not always cosmetic.** The section says it is, but doc 05 documents a real cause with the same symptom: a wrong `Environment=PATH=` means systemd cannot find the `claude` binary and CloudCLI reports it as an authentication failure. Add "if prompts genuinely fail, check PATH first".
- **Bare hostnames.** `hactar` and `tra` should be "hypervisor host" and "TRA VM", matching the placeholder convention in doc 05.
- **Indented code blocks** should be fenced with language tags, as everywhere else in the docs.
- **The WS status code list** could be a table, matching the triage table directly above it.
- **No links into doc 05** — cross-references to the architecture, the split-auth table for the `401` row, and the `HOST=` rationale for the bind note would save readers re-deriving what is already documented.
