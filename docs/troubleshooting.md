# Troubleshooting

Hard-won gotchas encountered while building and running the demo.

## EDA / Rulebooks

**Rulebook path must be `extensions/eda/rulebooks/`.**
Not `eda/` or any other layout. The AAP project scanner only finds rulebooks in this specific path.

**Single-quote condition strings that contain colon-space.**
YAML interprets `colon-space` as a key-value separator. Rulebook conditions like `event.payload.name: something` will cause parse errors unless the entire string is single-quoted.

**Use `is search()`, not `==`, for Zabbix trigger names.**
Zabbix appends a dynamic suffix like `(for 3m)` to trigger names. Exact match will never fire; `is search()` matches the stable prefix.

**The Zabbix payload field is `event_name`, not `alert_name`.**
The EDA event payload from the Zabbix media type uses `event_name`. Using the wrong field name silently matches nothing.

**"Forward events" toggle must be enabled on the Event Stream.**
Without this, the Event Stream appears grayed out in the source mapping UI and receives no events.

**Changing a rulebook requires deleting and recreating the activation.**
Activation source mappings are hash-based. Editing the rulebook file does not update a running activation — you must delete it and create a new one.

## AAP

**AAP 2.7 API path is `/api/controller/v2/`, not `/api/v2/`.**
The old path returns 404 on AAP 2.7. This affects manual API calls and any tooling that hardcodes the path.

**AAP MCP has no EDA-specific endpoints.**
No `projects_create`, no `inventories_create`, no Event Stream or Rulebook Activation management. Many setup steps require the AAP UI and cannot be done autonomously through MCP.

## Zabbix media type

**Send-to field is hostname only; the path goes in the endpoint parameter.**
The media type JavaScript concatenates them. Putting the full URL in Send-to results in a malformed request.

## Host investigation

**Systemd unit files persist after `dnf remove`.**
A service can show as `loaded` in systemd even after its package has been removed (if `daemon-reload` was not run). Always verify the binary exists before concluding a service is installed.

## Known upstream issues

**Zabbix EDA integration docs describe the old webhook approach.**
Zabbix's official documentation still references raw `ansible.eda.webhook` port listeners. It does not cover AAP 2.7 Event Streams, which provide gateway-managed URLs with TLS and authentication — no separate ports or users per rulebook needed. This demo uses Event Streams exclusively.
