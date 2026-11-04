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

## Agent-remediation readiness

The general agent rule requires the matching agent-unavailable name and numeric
`event_value: 1`; missing fields, recovery and unrelated events cannot launch
its job. The maintained webhook uses `Number(parameters.event_value)`, so the
Zabbix macro strings `"1"` and `"0"` become numeric problem/recovery values.
The actual selected media script was read back and matched this implementation.
The separate website problem/restore and recovery/rearm rulebook is unchanged.

The condition uses the documented [Ansible Rulebook condition operators](https://docs.ansible.com/projects/rulebook/en/latest/conditions.html).
Run the focused payload/condition contract checks with existing Node.js and an
Ansible-equipped interpreter:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/aiops-agent-event-tests python3.12 -m unittest discover -s tests -p test_agent_event_guard.py -v
```

These checks execute the real webhook JavaScript, then evaluate the saved
condition with native Ansible. They do not start an EDA activation or invoke a
model, and do not replace a controlled end-to-end rehearsal.

Read-only inspection of the selected instance confirmed the existing **Run
Claude to analyse and fix** template selects only its `tra` inventory alias and
uses its existing Machine credential. That alias resolves to the verified TRA
and the account already owning its private MCP configuration. Both Linux and
Zabbix stdio servers initialized and listed the expected tools using only local
images, without a tool call. They create no public MCP listener.

The remaining concrete prerequisites on that TRA are Claude Code in the job
account's executable path, its own approved provider authentication, the reviewed
`CLAUDE.md` instructions in its workspace, and an authenticated private AAP MCP
client connection to the matching AAP. The existing Linux/Zabbix MCP deployment
does not install or supply these. The TRA still has neither a recovery release
nor an HTTPS exception, so model-provider connectivity also needs its own
reviewed policy decision. Do not copy source authentication or weaken recovery
isolation as a fallback. Provider authentication was inspected only for local
presence; no provider request or credential refresh was attempted.

After those prerequisites are deliberately configured and verified, review the
selected agent-event forwarding and activation, sync the published rulebook,
then authorize and run the controlled agent-down rehearsal. The proof must show
the agent calls the matching AAP's existing repair template and Zabbix receives
fresh recovery samples. No CLI installation, provider login, activation, model
invocation or new outage was performed during this readiness inspection.

## Verified deployment state

The selected deployment passed its normal Zabbix template and an unchanged
normal repeat. Independent API/history readbacks confirmed fresh agent ping,
uptime and ICMP samples, retained host and original check identifiers, the
requested Linux/ICMP states and disabled Apache entities. Both runs left the
working website's exact forwarding action and target credentials intact; trusted
content and arm endpoints stayed healthy. The general Claude activation remained
disabled, and neither an inference nor a new fault was invoked. Exact instance,
job, revision and metric details are retained in the private verification Vault.
