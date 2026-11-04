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

- Versioned website infrastructure in the existing Enable job: reuse the
  selected AAP allocation for DNS, existing-account certificates and a dedicated
  nginx virtual host, with pinned hypervisor SSH/machine identity and verified
  HTTPS forwarding to that AAP. Initial recovery deployments keep monitoring,
  shared fail2ban changes and audience button arming disabled until their own
  monitoring/repair integration is ready. DNS authorization and the target's
  generated webhook information have no saved secret defaults; their protected
  runtime settings use the existing private whole-file Vault and runtime
  credential, with native loading and unconditional temporary-file cleanup.
- Separate versioned Zabbix deployment: immutable saved-image cloning,
  quarantine before monitoring starts, target-local website monitoring and a
  trusted HTTPS frontend retaining Basic authentication. Event delivery stays
  disabled until explicitly released.
- Two requested MCP deployment playbooks retain the existing on-demand
  Podman/stdio servers on the matching new TRA. They verify signed offline
  runtime artifacts and image identities, pin fresh guest SSH keys and perform
  read-only protocol checks. Linux MCP generates its private key only on TRA;
  Zabbix MCP requires the new target's explicit API token. Neither opens a
  public MCP port or installs or launches the agent.
- Exact reviewed `community.general` collection pin for the public DNS checks.

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

- Fresh-target inventory data comes from the AIOps private capture's selected
  allocation and verified guest artifacts. Guest jobs reuse the target's existing base Machine
  credential; hypervisor jobs retain their separate Machine credential.
- Website and monitoring checks use the permitted configured DNS resolver and
  pinned hypervisor route. Managed website monitoring requires explicit new
  target inputs instead of using production monitoring defaults.
- CaC import and application execution are documented separately. The ten
  template definitions can be imported independently of application execution;
  missing settings stop dependent jobs before managed writes. Unsupported inline
  Vault launch scalars and JSON Vault-marker mappings are not advertised as a
  Controller transport.
- Offline MCP runtime preparation imports only the reviewed existing
  release-owned Red Hat signing key after checksum/fingerprint checks, before
  mandatory RPM signature verification. Package GPG checks remain enabled.

- `playbooks/demo_website.yml` — Enable removes rate limiting for the whole
  audience site; Disable restores its previous button limit through a
  dedicated nginx include. Reloads verify actual worker replacement.

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

## [1.1.0] — 2026-11-04

### Added

- A static interactive visualization of the existing missing-Zabbix-agent
  recovery scenario, with 17 presenter-paced stops, a persistent SVG architecture,
  all three MCP investigations, distinct reasoning and catalog discovery,
  AAP-only remediation execution, and subsequent monitoring confirmation.
- Keyboard and direct-step navigation, motion controls, reduced-motion support,
  responsive architecture scrolling, and source-linked technical detail.
- Built-in Node model checks and an allowlisted GitHub Pages workflow that
  validates pull requests and prepares publication from `main`.
- Presenter/publication documentation with explicit simulated-evidence and
  functionality-demo limitations. No live infrastructure configuration changes.

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
