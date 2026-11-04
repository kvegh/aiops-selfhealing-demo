# Selected testserver monitoring

The normal **Deploy Zabbix Demo** playbook can enable monitoring for the selected
versioned testserver after **Deploy Zabbix Agent** succeeds. It uses the existing
Job Template and private CaC; there is no extra job, credential type or service.
Initial monitoring deployment keeps this opt-in off so an agent that has not
been installed cannot prevent creating the monitoring server it needs.

In the private CaC's existing selected-instance record, set
`testserver_monitoring_enabled: true` only after that instance's agent is ready.
The existing deployment template derives its saved
`demo_zabbix_enable_testserver_monitoring` boolean from that record, defaulting
to false for an instance without the setting. The selected AAP inventory entry's
existing `vm_resource.vm_name` chooses this private record, so changing its
inventory alias preserves the monitoring choice. Import the reviewed CaC into the
selected AAP and run its normal **Deploy Zabbix Demo** template again. Publishing
the repository alone does not change AAP or Zabbix.

## Identity and check selection

Before interrupting existing monitoring, deployment verifies the selected
testserver's actual domain UUID, disk, MAC, network and assigned DHCP address.
It queries that private address from the pinned monitoring VM: `agent.ping` must
return 1, the hostname must match the selected short name or FQDN, and the minimal
guest must have no Apache binary. A mismatch stops before the monitoring service
is stopped. A host requiring Apache monitoring needs a separately reviewed check
selection rather than silently applying this minimal-guest policy.

The inherited **Linux by Zabbix agent** and **ICMP Ping** templates provide the
appropriate checks. The copied **Apache by HTTP** items, triggers and discovery
rule remain linked but disabled on this host. Only host-level statuses change;
templates, records and historical samples are not cleared or deleted. Direct
and discovered check ownership must resolve to the reviewed templates; unknown
templates, unclassified checks and cross-host triggers stop configuration.
This uses the existing [Zabbix item status API](https://www.zabbix.com/documentation/7.4/en/manual/api/reference/item/update)
and preserves the inherited entities.

The monitoring host retains its existing ID and its versioned technical/display
name. Its interface and Apache address override stay bound to this deployment's
verified private guest, with no production address fallback. Normal reruns use
the same records and desired states, including the disabled Apache checks.

## Completion and event delivery

After starting monitoring, deployment reads back the check ownership and states,
then waits for fresh numeric history from this guest's agent ping, uptime and
ICMP ping. A copied historical success cannot satisfy this check. The existing
trusted-HTTPS frontend and selected website action checks still run; only the
exact website trigger may forward through its current target Event Stream.
Other copied hosts/actions and the general Claude rulebook remain disabled.

Collecting Linux metrics does not demonstrate AI remediation. The remaining
separate rehearsal would activate the reviewed agent rulebook and deliver a
controlled agent-down event, causing **Run Claude to analyse and fix** to call
the model provider. That model invocation and a new fault are not part of this
monitoring verification. The website outage/restore/rearm loop remains intact.

## Verified deployment state

The selected deployment passed its normal Zabbix template and an unchanged
normal repeat. Independent API/history readbacks confirmed fresh agent ping,
uptime and ICMP samples, retained host and original check identifiers, the
requested Linux/ICMP states and disabled Apache entities. Both runs left the
working website's exact forwarding action and target credentials intact; trusted
content and arm endpoints stayed healthy. The general Claude activation remained
disabled, and neither an inference nor a new fault was invoked. Exact instance,
job, revision and metric details are retained in the private verification Vault.
