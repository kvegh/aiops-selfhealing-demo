# Starting setup

Baseline environment — all of this is a **prerequisite**. The build guide starts from this state.

## Environment overview

Four virtual machines. VM sizing is out of scope; use vendor minimums or better.

| VM | Role | Software state | Credentials available |
|----|------|---------------|----------------------|
| `aap` | Automation platform | AAP (latest, 2.7 as of writing), containerized installation on RHEL, default configuration | AAP admin |
| `zabbix` | Monitoring | Zabbix appliance, default configuration | Zabbix admin |
| `rhel-target` | Managed target | RHEL, base installation | SSH user with sudo (Ansible-ready) |
| `tra` | Trusted Remediation Agent | RHEL, base installation; runs Claude Code CLI and the MCP layer | root/sudo on the VM itself |

## Baseline definitions

### AAP VM
- AAP installed via the containerized installer on RHEL, driven by the standard installer inventory file (`inventory` ini format).
- All AAP components on this single VM (Controller, EDA, gateway).
- Default post-install state: admin login works on the web UI, no projects, job templates, or inventories created yet.

### Zabbix VM
- Zabbix deployed as the [official appliance image](https://www.zabbix.com/download).
- Default post-install state: admin login works on the web UI, no custom hosts, triggers, or media types configured yet.

### RHEL target VM
- Minimal/base RHEL installation.
- A user account with SSH key access and passwordless sudo exists (standard Ansible managed-node prerequisites).
- No agents or additional packages installed yet.

### TRA VM
- Base RHEL installation with sudo access.
- Nothing demo-specific installed yet. Claude Code CLI, Podman containers (linux-mcp, MCP filtering proxy), and all MCP client configuration are set up by this guide.

## Zabbix host setup for the target VM

Add the target VM as a monitored host in Zabbix:

1. Navigate to **Data collection → Hosts → Create host**
2. Set hostname, add to a host group, configure the Zabbix agent interface (IP/DNS, port 10050)
3. Link the following templates:
   - **Linux by Zabbix agent** — OS-level metrics and the agent availability trigger (`Zabbix agent is not available`) that drives the demo scenario
   - **ICMP Ping** — network reachability check
   - **Apache by HTTP** — HTTP service monitoring
4. Save and confirm the agent status turns green (ZBX icon)

> The demo scenario relies on the `Zabbix agent is not available` trigger
> from the Linux by Zabbix agent template. This trigger fires after the
> `{$AGENT.TIMEOUT}` macro expires (default 3 minutes).

## Network requirements

All connectivity is within one lab network. Required reachability:

| From | To | Port / protocol | Purpose |
|------|----|-----------------|---------|
| `tra` | `aap` | 443 (HTTPS), 8448 (HTTP/SSE) | AAP API, AAP MCP server |
| `tra` | `zabbix` | 443/80 (HTTPS/HTTP) | Zabbix API |
| `tra` | `rhel-target` | 22 (SSH) | Read-only diagnostics via linux-mcp |
| `aap` | `rhel-target` | 22 (SSH) | Remediation job execution |
| `rhel-target` | `zabbix` | 10051 (Zabbix trapper) | Agent → server reporting |
| `zabbix` | `aap` | 443 (HTTPS) | Alert forwarding to EDA via Event Streams |
| `tra` | Anthropic API (internet) | 443 | Claude Code CLI inference |

## Credentials checklist

Present before starting the build guide:

- [ ] AAP admin username + password
- [ ] Zabbix admin username + password
- [ ] SSH private key + username for `rhel-target` (sudo-capable)
- [ ] Anthropic account/API access for Claude Code CLI

Everything else (API tokens, service accounts, AAP credentials objects) is **created during the build guide** from these admin credentials.

## Explicitly out of scope

- VM provisioning, sizing, and OS installation
- AAP, Zabbix, and RHEL installation procedures (vendor documentation applies)
- Production hardening (TLS certificates, LDAP/SSO, network segmentation)
- ITSM system installation (an existing instance, e.g. ServiceNow developer instance, is assumed if the ITSM integration stage is used)
