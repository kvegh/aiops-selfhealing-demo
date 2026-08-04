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

## CloudCLI access

CloudCLI is the browser-based interface to Claude Code. Three distinct failures
can occur — identify which one by what the browser shows.

### Symptom triage

| Browser shows | Meaning | First action |
|---|---|---|
| `502 Bad Gateway` | Backend down. nginx is up, cannot reach `cloudcli` on tra. | Check the service (below) |
| CloudCLI login screen | App token cleared. Not a fault. | Log in |
| "Offline — please check your connection" | Page loaded, WebSocket did not connect. Backend and nginx both served the shell. | **Capture the WS status code before touching anything** |

### The "Offline" case

This is the ambiguous one. The app rendered, so nginx and the backend are
both alive — the failure is in the live connection established afterward.

Before restarting anything, capture:

    F12 → Network → filter WS → reload → status code of the failed request

    101  handshake succeeded, look elsewhere
    401  auth — check htpasswd on the WS location
    200  nginx is stripping the upgrade headers
    502  backend died between shell load and socket open

And on tra:

    ss -tnp | grep :3001
    systemctl --machine=aaptra@.host --user status cloudcli
    journalctl --machine=aaptra@.host --user -u cloudcli -n 100 --no-pager

A restart usually clears it, but restarting first destroys the evidence.

### systemd linger (required)

**`cloudcli` runs as a systemd user service under `aaptra`.**
Without linger the user manager is torn down at logout, taking the service
with it — the service works while you are SSHed in and dies when you disconnect.

    sudo loginctl enable-linger aaptra
    loginctl show-user aaptra | grep -i linger    # expect Linger=yes

Enabling linger does not restart anything; it only prevents future teardown.

Verify unattended: log out completely, then from hactar:

    curl -sS -o /dev/null -w '%{http_code}\n' http://PUT_YOUR_IP_HERE:3001/

### Notes

**The service binds to `PUT_YOUR_IP_HERE:3001`, not localhost.**
`curl 127.0.0.1:3001` will refuse — expected, not a fault.

**Root cannot use `systemctl --user` against another user's manager.**
Use `--machine=aaptra@.host --user`.

**Settings → Agents → Claude may show "Disconnected" and "Failed to check authentication status" while the CLI works normally.**
Cosmetic; verify by sending a prompt.

**CloudCLI self-hosted is single-user.**
htpasswd identities are a door, not isolation — all sessions share one `~/.claude`,
one MCP config, one AAP token, one `--dangerously-skip-permissions` process family.

## Known upstream issues

**Zabbix EDA integration docs describe the old webhook approach.**
Zabbix's official documentation still references raw `ansible.eda.webhook` port listeners. It does not cover AAP 2.7 Event Streams, which provide gateway-managed URLs with TLS and authentication — no separate ports or users per rulebook needed. This demo uses Event Streams exclusively.
