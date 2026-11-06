# 04 – Set up Claude agent

Claude Code CLI runs on the TRA VM as the AI agent. This section installs
the CLI, connects it to the MCP servers deployed in prior steps, and
configures headless execution for automated invocation by EDA.

> All commands run on the **TRA VM** unless noted otherwise.

## Environment

- TRA VM: RHEL 9, base installation (from [00-starting-setup](00-starting-setup.md))
- AAP MCP server deployed and reachable on port 8448 (from [01-aap-mcp](01-aap-mcp.md))
- Anthropic API key or Google Vertex AI project credentials available

## 1. Install Claude Code CLI

Claude Code requires Node.js 22+.

```bash
dnf module install -y nodejs:22/common
npm install -g @anthropic-ai/claude-code
```

Verify:

```bash
$ claude --version
```

## 2. Set up the agent **W**orking **D**irectory

Create a dedicated directory for the agent. Claude Code reads its
configuration (MCP connections, instructions, tool policy) from the
working directory it is launched in. We use `~/claude-wd`:

```bash
mkdir -p ~/claude-wd
cd ~/claude-wd
```

## 3. Authenticate

Set the Anthropic API key. For automated execution, persist it in the
service user's environment (shell profile, systemd unit, or a secrets
manager):

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

> **Claude via Google Vertex AI** requires different configuration
> (environment variables instead of an API key). See the
> [Claude Code documentation](https://docs.anthropic.com/en/docs/claude-code/bedrock-vertex)
> for Vertex-specific setup.

## 4. Create an AAP API token

Claude authenticates to the AAP MCP server with a Personal Access Token
(PAT). Creating one requires an OAuth2 application first.

### Create an OAuth2 application

In the AAP Controller UI:

1. Navigate to **Access Management → OAuth Applications → Create OAuth application**.
2. Set the fields:
   - **Name:** `mcp-client` (or any descriptive name)
   - **Grant type:** Resource owner password-based
   - **Client type:** Confidential
   - **Redirect URIs:** leave blank
3. Save. Note the **Client ID** — you won't need the secret for PAT
   auth, but keep it on record.

### Create a Personal Access Token

1. Navigate to **Access Management → Users → your user → API Tokens → Create API Token**.
2. Select the OAuth2 application you just created (`mcp-client`).
3. Set **Scope** to **Write** (covers both read and write operations —
   required because the MCP server launches job templates).
4. Save. **Copy the token value immediately** — it will not be shown
   again.

The token inherits the creating user's RBAC permissions — ensure that
user can launch the relevant job templates.

Store the token securely. You will reference it in the Claude Code
configuration on the TRA VM in the next step.

## 5. Connect MCP servers

Claude Code reads MCP configuration from `~/.claude.json`. The AAP MCP
server uses Streamable HTTP transport with Bearer token authentication.
Add the AAP MCP entry under `mcpServers` (if the file doesn't exist,
`claude mcp add` creates it):

```json
"mcpServers": {
    "aap-mcp": {
        "type": "http",
        "url": "https://AAP_SERVER:8448/mcp",
        "headers": {
            "Authorization": "Bearer YOUR_AAP_TOKEN"
        }
    }
}
```

Replace `AAP_SERVER` with the AAP hostname or IP, and `YOUR_AAP_TOKEN`
with the PAT created in step 4.

> **HTTPS is required.** The MCP server on port 8448 uses TLS with the
> AAP CA certificate. The TRA VM must trust that CA (see
> [01-aap-mcp](01-aap-mcp.md), section 5). Using `http://` will fail
> silently or return 401.

Add the remaining MCP servers to the same `mcpServers` block:

```json
"mcpServers": {
    "aap-mcp": {
        "type": "http",
        "url": "https://AAP_SERVER:8448/mcp",
        "headers": {
            "Authorization": "Bearer YOUR_AAP_TOKEN"
        }
    },
    "linux-mcp": {
        "type": "stdio",
        "command": "podman",
        "args": [
            "run", "--rm", "--interactive",
            "--userns", "keep-id:uid=1001,gid=0",
            "-e", "LINUX_MCP_USER=mcp",
            "-e", "LINUX_MCP_ALLOWED_LOG_PATHS=/var/log/messages,/var/log/secure",
            "-v", "/home/USER/.ssh:/var/lib/mcp/.ssh:ro,Z",
            "-v", "/home/USER/.local/share/linux-mcp-server/logs:/var/lib/mcp/.local/share/linux-mcp-server/logs:rw,Z",
            "quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest"
        ]
    },
    "zabbix": {
        "command": "podman",
        "args": [
            "run", "--rm", "-i",
            "-v", "/etc/zabbix-mcp/config.toml:/etc/zabbix-mcp/config.toml:ro",
            "zabbix-mcp-server",
            "--config", "/etc/zabbix-mcp/config.toml"
        ]
    }
}
```

Replace `AAP_SERVER`, `YOUR_AAP_TOKEN`, and `USER` with your
environment values.

> **Sensitive values in `~/.claude.json`:** For a demo this is acceptable.
> In production, reference environment variables or a secrets manager
> instead of embedding tokens directly.

### Alternative: `claude mcp add`

Each server can also be added interactively:

```bash
claude mcp add --transport http \
  --header "Authorization: Bearer YOUR_AAP_TOKEN" \
  aap-mcp https://AAP_SERVER:8448/mcp

```

### Verify MCP connectivity

```bash
claude mcp list
```

All servers should appear. To test that each server responds:

```bash
claude -p "List available MCP tools" --output-format json
```

The output should include tools from all configured servers.

## 6. Create the agent instructions (CLAUDE.md)

Claude Code reads `CLAUDE.md` from the working directory on every
invocation. This file defines the agent's role, constraints, and operating
procedures.

Copy the production-tested version from the repo:

```bash
cp AI_Instructions_Guardrails/CLAUDE.md ~/claude-wd/CLAUDE.md
```

See [`AI_Instructions_Guardrails/CLAUDE.md`](../AI_Instructions_Guardrails/CLAUDE.md)
for the full content — it includes phase-disciplined investigation,
AAP-only remediation constraints, SSH alias rules, RHEL prerequisites,
and response format requirements.

## 7. Use the bounded AAP runner

Run **Run Claude to analyse and fix** through AAP after completing
[Deploy Claude and MCP Servers](14-claude-deployment.md). The maintained
[runner playbook](../playbooks/run_claude_analyse_fix.yml) is the executable
procedure; do not copy an older shell invocation into another template.

The runner uses native `dontAsk` permissions, an explicit read-only diagnostic
tool list, and a temporary deny-only hook. Built-in shell tools are disabled.
Only the checked **Deploy Zabbix Agent** template can make changes, using its
saved selected-host limit and no launch overrides. Existing permission checks
and hooks remain effective.

One invocation is limited to 600 seconds and 24 turns. It may launch at most
two instances of that repair. There is no configured monetary spending cap.
The private AAP MCP connection must use its selected trusted certificate; the
runner does not weaken TLS or expose a public MCP endpoint.

## 8. Verify the selected alert-to-repair demo

Prepare the selected testserver with its Zabbix agent installed and healthy.
The target-local agent action must forward only that host's agent-availability
trigger through the current Event Stream. Enable the matching agent rulebook
activation only for the agreed demo test; the website has a separate rulebook.

For one controlled test, an operator stops only the selected guest's
`zabbix-agent2` service. Zabbix must report the problem and EDA must launch the
saved runner. The agent cannot inject the fault itself.

A successful result requires at least one actual saved repair job, matching
project, inventory and host limit, followed by an active agent service, a fresh
`agent.ping=1` sample and recovery of the original trigger. Model prose alone is
not proof. On failure, stop further agent invocations and use the existing repair
template to restore the selected service before repeating the test.

## 9. Read the findings

The runner captures ordered streaming assistant findings and the final incident
report in the protected AAP job, then performs independent native recovery
checks. It uses no persistent CLI session. Review the AAP runner and child-job
results; do not rely on a manually resumed CLI transcript as acceptance evidence.
Temporary invocation settings, the tool-request hook and temporary SSH trust
are removed when the job finishes or fails. Provider authentication and existing
workspace settings are preserved.

## Explicitly out of scope

- Deployment of individual MCP servers (linux-mcp container, Zabbix MCP)
  — covered in their own sections
- EDA rulebook and Zabbix integration — covered in [06-eda-zabbix-integration](06-eda-zabbix-integration.md)
- Claude Code SDK (Python) as an alternative to CLI invocation
- Production hardening (rate limiting, cost controls, retry logic)
