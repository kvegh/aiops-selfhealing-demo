# 03 – Zabbix MCP Server

The Zabbix MCP server gives Claude **read-only** access to the
monitoring layer — hosts, problems, triggers, history, and events. It
uses the [initMAX/zabbix-mcp-server](https://github.com/initMAX/zabbix-mcp-server),
which exposes the complete Zabbix API (237 tools) over HTTP transport.

The server runs on the TRA VM as a systemd service, listening on
`127.0.0.1:8080`. Claude Code connects to it over HTTP — no internet
exposure required.

## Environment

- TRA VM: RHEL 9, base installation (from [00-starting-setup](00-starting-setup.md))
- Zabbix appliance VM: reachable from TRA over HTTPS/HTTP
  (from [00-starting-setup](00-starting-setup.md))
- Zabbix admin credentials available
- Python 3.10+ on the TRA VM

## 1. Create a Zabbix API token

In the Zabbix web UI:

1. Navigate to **Users → API tokens → Create API token**.
2. Select the admin user (the token inherits the user's permissions).
3. Optionally set an expiration date.
4. Click **Add**. Copy the token — it is shown only once.

> For this demo the admin user is sufficient. In production, create a
> dedicated read-only user and associate the token with that user.

## 2. Install the Zabbix MCP server on the TRA VM

```bash
git clone https://github.com/initMAX/zabbix-mcp-server.git /opt/zabbix-mcp-server
cd /opt/zabbix-mcp-server
sudo ./deploy/install.sh
```

The installer:
- Creates system user `zabbix-mcp` (no login shell)
- Creates a Python virtualenv at `/opt/zabbix-mcp/venv`
- Installs the server and dependencies
- Places the config at `/etc/zabbix-mcp/config.toml`
- Installs a systemd service `zabbix-mcp-server`
- Sets up logrotate

## 3. Configure

Edit `/etc/zabbix-mcp/config.toml`:

```toml
[server]
transport = "http"
host = "127.0.0.1"
port = 8080
log_level = "info"
log_file = "/var/log/zabbix-mcp/server.log"
tools = ["host", "hostgroup", "problem", "trigger", "event", "item", "history"]
compact_output = true

[zabbix.production]
url = "https://ZABBIX_SERVER"
api_token = "YOUR_ZABBIX_API_TOKEN"
read_only = true
verify_ssl = false
```

Replace `ZABBIX_SERVER` and `YOUR_ZABBIX_API_TOKEN` with your
environment values.

Key settings explained:

| Setting | Purpose |
|---------|---------|
| `host = "127.0.0.1"` | Listen on localhost only — no network exposure |
| `read_only = true` | Block all write operations at the MCP layer |
| `verify_ssl = false` | Accept the appliance's self-signed certificate |
| `tools = [...]` | Limit exposed tools to monitoring-relevant ones, reducing the MCP tool catalog token overhead for the model |
| `compact_output = true` | Return key fields only, keeping responses concise |

> **SSL note:** If you have the Zabbix CA certificate, add it to the
> TRA's trust store and set `verify_ssl = true` instead.

> **Tool filtering:** The full server exposes 237 tools (~100k tokens
> of catalog overhead). The `tools` list above limits this to the
> categories needed for incident diagnosis. Add more prefixes as needed
> (e.g. `"template"`, `"maintenance"`).

## 4. Start the service

```bash
sudo systemctl start zabbix-mcp-server
sudo systemctl enable zabbix-mcp-server
```

## 5. Verify

Check the service is running:

```bash
sudo systemctl status zabbix-mcp-server
```

Check the health endpoint:

```bash
curl http://localhost:8080/health
```

Expected response: `{"status":"ok"}`

Check the application log for Zabbix connectivity:

```bash
sudo tail -20 /var/log/zabbix-mcp/server.log
```

## 6. Connect Claude Code

Claude Code connects to the Zabbix MCP server over HTTP transport. The
relevant entry in `/opt/tra/agent/.mcp.json` (full file in
[04-claude-agent](04-claude-agent.md)):

```json
{
    "zabbix": {
        "type": "http",
        "url": "http://127.0.0.1:8080/mcp"
    }
}
```

Since the server listens on localhost with no authentication configured,
no headers are needed. If you add MCP authentication (see below), add
the bearer token header.

### Optional: MCP authentication

To add a bearer token for the Claude Code → Zabbix MCP connection:

```bash
cd /opt/zabbix-mcp-server
sudo ./deploy/install.sh generate-token claude
```

Add the generated hash to `/etc/zabbix-mcp/config.toml`:

```toml
[tokens.claude]
name = "Claude Code"
token_hash = "sha256:<paste-hash>"
scopes = ["*"]
read_only = true
```

Restart the service and update `.mcp.json`:

```json
{
    "zabbix": {
        "type": "http",
        "url": "http://127.0.0.1:8080/mcp",
        "headers": {
            "Authorization": "Bearer zmcp_<your-token>"
        }
    }
}
```

## 7. Test from Claude Code

```bash
cd /opt/tra/agent
claude -p "Use Zabbix to list all monitored hosts and their current problems." \
    --permission-mode bypassPermissions \
    --max-turns 5
```

The agent should return the list of hosts from Zabbix and any active
problems.

## Updating

```bash
cd /opt/zabbix-mcp-server
git pull
sudo ./deploy/install.sh update
```

The update preserves `config.toml` and restarts the service.

## Explicitly out of scope

- Zabbix appliance installation and configuration
- Zabbix host/trigger/template setup for the target VM
- MCP authentication hardening (TLS, IP allowlists, OAuth 2.1)
- Admin portal configuration (port 9090)
- PDF report generation
- Claude Code CLI installation and full MCP wiring (covered in [04-claude-agent](04-claude-agent.md))
