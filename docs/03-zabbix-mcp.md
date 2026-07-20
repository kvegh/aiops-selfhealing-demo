# 03 – Zabbix MCP Server

The Zabbix MCP server gives Claude **read-only** access to the
monitoring layer — hosts, problems, triggers, history, and events. It
uses the [initMAX/zabbix-mcp-server](https://github.com/initMAX/zabbix-mcp-server),
built and open-sourced by [initMAX](https://www.initmax.com/) — a Zabbix
Premium Partner with deep Zabbix expertise. Their work on this MCP
server is what makes the monitoring side of this AIOps demo possible.
Thank you, initMAX.

The server runs as a container, launched by Claude Code on demand via
stdio transport — no persistent service, port mapping, or network
exposure required.

## Environment

- TRA VM: RHEL 9, base installation (from [00-starting-setup](00-starting-setup.md))
- Zabbix appliance VM: reachable from TRA over HTTP/HTTPS
  (from [00-starting-setup](00-starting-setup.md))
- Zabbix admin credentials available
- Podman installed on the TRA VM

## 1. Create a Zabbix API token

In the Zabbix web UI:

1. Navigate to **Users → API tokens → Create API token**.
2. Select the admin user (the token inherits the user's permissions).
3. Click **Add**. Copy the token — it is shown only once.

> For this demo the admin user is sufficient. In production, create a
> dedicated read-only user and associate the token with that user.

## 2. Build the container image

initMAX does not publish a prebuilt registry image. Clone the repo and
build locally:

```bash
git clone https://github.com/initMAX/zabbix-mcp-server.git /opt/zabbix-mcp-server
cd /opt/zabbix-mcp-server
podman build -t zabbix-mcp-server .
```

The HEALTHCHECK warning (`HEALTHCHECK is not supported for OCI image
format`) is harmless — the container runs fine.

## 3. Configure

Create the config directory and file:

```bash
sudo mkdir -p /etc/zabbix-mcp
```

Create `/etc/zabbix-mcp/config.toml`:

```toml
[server]
transport = "stdio"
log_level = "info"
tools = ["host", "hostgroup", "problem", "trigger", "event", "item", "history"]
compact_output = true

[zabbix.lab]
url = "http://ZABBIX_SERVER"
api_token = "YOUR_ZABBIX_API_TOKEN"
read_only = true
```

Replace `ZABBIX_SERVER` and `YOUR_ZABBIX_API_TOKEN` with your
environment values.

Key settings explained:

| Setting | Purpose |
|---------|---------|
| `transport = "stdio"` | Claude Code launches the container and communicates via stdin/stdout — no network listener |
| `read_only = true` | Block all write operations at the MCP layer |
| `tools = [...]` | Limit exposed tools to monitoring-relevant categories, reducing token overhead (the full server exposes ~220+ tools) |
| `compact_output = true` | Return key fields only, keeping responses concise |

> **SSL note:** If your Zabbix instance uses HTTPS with a self-signed
> certificate, add `verify_ssl = false` under the `[zabbix.lab]` section.

> **Tool filtering:** Add more prefixes as needed (e.g. `"template"`, `"maintenance"`).

## 4. Set SELinux context

The container needs to read the config file. Set the SELinux label so
Podman can mount it without the `:Z` flag (which requires root
privileges on `/etc/` paths):

```bash
sudo chcon -t container_file_t /etc/zabbix-mcp/config.toml
```

> **Why not `:Z`?** The `:Z` volume flag relabels the file with
> per-container MCS categories. Non-root users cannot relabel files
> under `/etc/`. Setting the label once with `chcon` avoids this.

## 5. Verify manually

Test that the server starts and connects to Zabbix:

```bash
podman run --rm -i \
  -v /etc/zabbix-mcp/config.toml:/etc/zabbix-mcp/config.toml:ro \
  zabbix-mcp-server \
  --config /etc/zabbix-mcp/config.toml
```

The process should start and wait for stdio input (no errors). Press
`Ctrl+C` to stop.

## 6. Connect Claude Code

The Zabbix MCP entry uses the same pattern as linux-mcp — Claude Code
launches the container as a subprocess and communicates over stdio.

Add to `~/.claude.json` under `mcpServers`:

```json
"zabbix": {
    "command": "podman",
    "args": [
        "run", "--rm", "-i",
        "-v", "/etc/zabbix-mcp/config.toml:/etc/zabbix-mcp/config.toml:ro",
        "zabbix-mcp-server",
        "--config", "/etc/zabbix-mcp/config.toml"
    ]
}
```

> **No `:Z` flag** — the SELinux label was set in step 4.

## 7. Test from Claude Code

```bash
cd /opt/tra/agent
claude -p "Use Zabbix to list all monitored hosts." \
    --dangerously-skip-permissions \
    --max-turns 5
```

The agent should return the list of hosts from Zabbix.

## Updating

```bash
cd /opt/zabbix-mcp-server
git pull
podman build -t zabbix-mcp-server .
```

The config file is not affected. The next Claude Code invocation will
use the new image.

## Explicitly out of scope

- Zabbix appliance installation and configuration
- Zabbix host/trigger/template setup for the target VM
- Claude Code CLI installation and full MCP wiring (covered in [04-claude-agent](04-claude-agent.md))
