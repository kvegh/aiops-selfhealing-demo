# 02 – Set up Claude agent

Claude Code CLI runs on the TRA VM as the AI agent. This section installs
the CLI, connects it to the MCP servers deployed in prior steps, and
configures headless execution for automated invocation by EDA.

> All commands run on the **TRA VM** unless noted otherwise.

## Environment

- TRA VM: RHEL 9, base installation (from [00-starting-setup](00-starting-setup.md))
- AAP MCP server deployed and reachable on port 8448 (from [01-aap-mcp](01-aap-mcp.md))
- Anthropic API key available

## 1. Install Claude Code CLI

Claude Code requires Node.js 18+.

```bash
dnf install -y nodejs
npm install -g @anthropic-ai/claude-code
```

Verify:

```bash
$ claude --version
```

## 2. Set up the agent project directory

Create a dedicated directory for the agent. Claude Code reads its
configuration (MCP connections, instructions, tool policy) from the
working directory it is launched in.

```bash
mkdir -p /opt/tra/agent
cd /opt/tra/agent
```

## 3. Authenticate

Set the Anthropic API key. For automated execution, persist it in the
service user's environment (shell profile, systemd unit, or a secrets
manager):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

## 4. Connect MCP servers

MCP connections are configured in `.mcp.json` at the root of the agent
project directory. This file is declarative — Claude Code reads it on
every invocation.

Create `/opt/tra/agent/.mcp.json`:

```json
{
  "mcpServers": {
    "aap": {
      "type": "http",
      "url": "https://AAP_SERVER:8448/mcp",
      "headers": {
        "Authorization": "Bearer AAP_API_TOKEN"
      }
    },
    "linux-mcp": {
      "type": "stdio",
      "command": "podman",
      "args": [
        "run", "--rm", "-i",
        "-v", "/opt/tra/keys/target-key:/key:ro",
        "ghcr.io/rhel-lightspeed/linux-mcp:latest",
        "--host", "TARGET_IP",
        "--user", "ansible",
        "--key", "/key"
      ]
    },
    "zabbix": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "zabbix-mcp-server"],
      "env": {
        "ZABBIX_URL": "https://ZABBIX_SERVER",
        "ZABBIX_API_TOKEN": "ZABBIX_TOKEN"
      }
    },
    "memory": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    }
  }
}
```

Replace the placeholder values (`AAP_SERVER`, `AAP_API_TOKEN`,
`TARGET_IP`, `ZABBIX_SERVER`, `ZABBIX_TOKEN`) with your environment.

> **Sensitive values in `.mcp.json`:** For a demo this is acceptable. In
> production, reference environment variables or a secrets manager instead
> of embedding tokens directly.

### Alternative: `claude mcp add`

Each server can also be added interactively. This stores the same
configuration but via the CLI:

```bash
claude mcp add --transport http \
  --header "Authorization: Bearer AAP_API_TOKEN" \
  aap https://AAP_SERVER:8448/mcp

claude mcp add memory -- npx -y @modelcontextprotocol/server-memory
```

### Verify MCP connectivity

```bash
claude mcp list
```

All four servers should appear. To test that each server responds:

```bash
claude -p "List available MCP tools" --output-format json
```

The output should include tools from all configured servers.

## 5. Create the agent instructions (CLAUDE.md)

Claude Code reads `CLAUDE.md` from the working directory on every
invocation. This file defines the agent's role, constraints, and operating
procedures.

Create `/opt/tra/agent/CLAUDE.md`:

```markdown
# AIOps Trusted Remediation Agent

You are an infrastructure remediation agent. You diagnose incidents on
managed servers and resolve them — exclusively through Ansible Automation
Platform.

## Architecture constraints

- You MUST NOT change systems directly. Every remediation action goes
  through AAP by launching a job template via the AAP MCP server.
- linux-mcp and Zabbix MCP are read-only. Use them for diagnosis only.
- If no suitable AAP job template exists for the required fix, escalate
  to a human operator. Do not attempt workarounds.

## Diagnostic procedure

1. Read the alert details from the triggering event (passed as input).
2. Use Zabbix MCP to retrieve alert context, trigger history, and metrics.
3. Use linux-mcp to inspect the affected system (logs, service status,
   packages, configuration).
4. Determine the root cause.

## Remediation procedure

1. Identify the appropriate AAP job template for the fix.
2. Launch the job template via AAP MCP with the correct parameters.
3. Wait for the job to complete.
4. Verify the fix by re-checking the system state via linux-mcp.
5. Verify the alert clears via Zabbix MCP.

## Incident memory

Use the memory MCP to record what you learn:
- What the incident was, what caused it, how it was resolved.
- This builds a knowledge base for future incidents.

## Response format

Report your findings and actions concisely. Include:
- What triggered the investigation
- What you found (root cause)
- What you did (AAP job template launched, parameters)
- Whether the fix was verified
```

> **Tuning:** This is a starting point. Refine the instructions based on
> observed agent behavior during testing.

## 6. Configure headless execution

Claude Code runs headlessly with `--print` (`-p`) mode: it reads a prompt
from the command line, executes the task, prints the result, and exits.
No interactive terminal required.

### Permission mode

In automated execution, there is no operator to approve tool calls.
Use `--permission-mode bypassPermissions` to skip all permission prompts:

```bash
claude -p "diagnose the alert" --permission-mode bypassPermissions
```

> **Security note:** This flag grants the agent unrestricted tool access.
> The architecture mitigates this: linux-mcp and Zabbix MCP are read-only
> by construction, and AAP enforces RBAC on every job launch. The blast
> radius is bounded by the MCP servers, not by the permission mode.

### Restrict available tools (optional)

To further limit what the agent can do, use `--allowedTools` to enumerate
the permitted tools explicitly:

```bash
claude -p "diagnose the alert" \
  --permission-mode bypassPermissions \
  --allowedTools "aap,linux-mcp,zabbix,memory,Read"
```

This prevents the agent from using its built-in Bash, Edit, or Write
tools — restricting it to MCP interactions and reading files.

### Output format

For machine-readable output (useful when EDA parses the result):

```bash
claude -p "diagnose the alert" \
  --permission-mode bypassPermissions \
  --output-format json
```

The JSON output includes the response text, session ID, token usage, and
cost.

### Limit agent turns

To prevent runaway loops, cap the number of agentic turns:

```bash
claude -p "diagnose the alert" \
  --permission-mode bypassPermissions \
  --max-turns 20
```

## 7. Test the agent

Run a manual test from the agent directory:

```bash
cd /opt/tra/agent

claude -p "List the hosts monitored by Zabbix and check if the target server is reachable via linux-mcp. Report what you find." \
  --permission-mode bypassPermissions \
  --max-turns 10
```

The agent should:
1. Query Zabbix MCP for monitored hosts
2. Run a connectivity check via linux-mcp
3. Return a summary of findings

## 8. Full invocation (EDA integration)

When EDA triggers the agent, it calls Claude Code with the alert payload
as the prompt. The complete invocation:

```bash
claude -p "An alert has fired. Details: ${ALERT_PAYLOAD}. Diagnose the issue and remediate it through AAP." \
  --permission-mode bypassPermissions \
  --allowedTools "aap,linux-mcp,zabbix,memory,Read" \
  --max-turns 25 \
  --output-format json \
  2>/opt/tra/logs/agent-$(date +%Y%m%d-%H%M%S).log
```

> **Note:** The exact EDA-to-agent integration (rulebook, webhook handler,
> alert payload format) is covered in a later section.

## Explicitly out of scope

- Deployment of individual MCP servers (linux-mcp container, Zabbix MCP)
  — covered in their own sections
- EDA rulebook configuration — covered in a later section
- Claude Code SDK (Python) as an alternative to CLI invocation
- Production hardening (rate limiting, cost controls, retry logic)
