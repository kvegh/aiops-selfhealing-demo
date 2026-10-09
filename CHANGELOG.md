# Changelog

Versions here track **what has been demonstrated and proven**, not an API
surface:

| Bump | Meaning |
|---|---|
| **Major** | A new demo scenario, complete and tested end to end |
| **Minor** | New functionality within the current scenario |
| **Patch** | Fixes to existing functionality |

History starts at `v1.0.0`. The pre-split history was moved to a private
archive during the repository split and is not part of this timeline.

## [Unreleased] — towards 2.0.0

The audience-facing button demo: the room causes the outage from their
phones and watches the platform put it back. Not yet end to end — the
nginx vhost, Zabbix web scenario, EDA rule, fault-injection and restore
templates, and the status page are still outstanding.

### Added

- `demo-web/index.html` — outer shell that polls `content.html` every 2s
  and renders either the site or a 404. Untouched by the fault, so every
  phone flips to the outage and back without a refresh.
- `demo-web/content.html` — the corporate page mockup, built to Red Hat
  brand standards (red-50 `#ee0000`, Red Hat Display/Text), with the
  **Secret Red Hat Button**. This is the file the fault moves aside, so the
  404 the audience sees is a real one.
- `demo-web/disabled.html` — inert placeholder served while the demo is
  switched off. No JavaScript, no external requests.
- `playbooks/demo_website.yml` — switches the site on and off around a
  demo session. Disabling swaps the page rather than deleting the site, so
  the URL keeps answering.

### Changed

- `playbooks/run_claude_analyse_fix.yml` — the user Claude Code runs as is
  now `claude_agent_user` from inventory instead of being hardcoded.
  **Breaking:** the job template fails its assert until that variable is
  supplied.
- `playbooks/deploy_zabbix_agent.yml` — dropped the `myvars` vault
  dependency in favour of asserting `zabbix_server` from inventory.
  Removes `playbooks/myvars.example`.
- Docs — remaining environment-specific identifiers replaced with
  placeholders (`AGENT_USER`, role names for hypervisor and TRA hosts).
- `demo-web/` — dropped the Google Fonts dependency for a system font
  stack. All three pages now make zero external requests, so they render
  identically on an audience phone with nothing but venue wifi.

## [1.0.0] — 2026-10-05

First proven version: Zabbix-agent self-healing (Level 1), demonstrated
working end to end.

A package is removed from the managed host, breaking monitoring. Zabbix
detects agent unavailability and fires an alert through the Event-Driven
Ansible media type to an EDA Event Stream. The rulebook matches and
launches an AAP job template, which invokes Claude Code CLI headless. The
agent investigates through Phases 1–4 (Zabbix MCP → linux-mcp → AAP MCP),
identifies the missing package, and launches the **Deploy Zabbix Agent**
template through AAP MCP. Zabbix confirms recovery.

Includes the build guide (docs 00–06), troubleshooting, the EDA rulebook,
and the agent guardrails.
