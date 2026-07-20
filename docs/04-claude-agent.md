# 04 – Set up Claude agent

Claude Code CLI runs on the TRA VM as the AI agent. This section installs
the CLI, connects it to the MCP servers deployed in prior steps, and
configures headless execution for automated invocation by EDA.

> All commands run on the **TRA VM** unless noted otherwise.

## Environment

- TRA VM: RHEL 9, base installation (from [00-starting-setup](00-starting-setup.md))
- AAP MCP server deployed and reachable on port 8448 (from [01-aap-mcp](01-aap-mcp.md))
- Anthropic API key available

## 1. Install Claude Code CLI

Claude Code requires Node.js 22+.

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

Replace `AAP_SERVER`, `YOUR_AAP_TOKEN`, `TARGET_IP`, and
`YOUR_ANSIBLE_USER` with your environment values.

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
cp AI_Instructions_Guardrails/CLAUDE.md /opt/tra/agent/CLAUDE.md
```

See [`AI_Instructions_Guardrails/CLAUDE.md`](../AI_Instructions_Guardrails/CLAUDE.md)
for the full content — it includes phase-disciplined investigation,
AAP-only remediation constraints, SSH alias rules, RHEL prerequisites,
and response format requirements.

## 7. Configure headless execution

Claude Code runs headlessly with `--print` (`-p`) mode: it reads a prompt
from the command line, executes the task, prints the result, and exits.
No interactive terminal required.

### Permission mode

In automated execution, there is no operator to approve tool calls.
Use `--dangerously-skip-permissions` to skip all permission prompts:

```bash
claude -p "diagnose the alert" --dangerously-skip-permissions
```

> **Security note:** This flag grants the agent unrestricted tool access.
> The architecture mitigates this: linux-mcp and Zabbix MCP are read-only
> by construction, and AAP enforces RBAC on every job launch. The blast
> radius is bounded by the MCP servers, not by the permission mode.

### Transcripts

Headless runs (`-p`) create JSONL transcript files under
`~/.claude/projects/.../` with a UUID filename. These transcripts are
the primary way to review what the agent did during an AAP-triggered
run. Headless sessions do **not** appear in `claude --resume` — this
is expected behavior, not a bug. However, you can extract the session
ID from the transcript filename and resume it explicitly with
`claude --resume SESSION_ID`.

## 8. Test the agent

Run a manual test from the agent directory:

```bash
cd /opt/tra/agent

claude -p "List the hosts monitored by Zabbix and check if the target server is reachable via linux-mcp. Report what you find." \
  --dangerously-skip-permissions \
  --max-turns 10
```

The agent should:
1. Query Zabbix MCP for monitored hosts
2. Run a connectivity check via linux-mcp
3. Return a summary of findings

## 9. Full invocation (EDA integration)

EDA launches the agent via an AAP job template that runs the playbook
[`playbooks/run_claude_analyse_fix.yml`](../playbooks/run_claude_analyse_fix.yml):

```yaml
---
- name: Run Claude to analyse and fix Zabbix alert
  hosts: all
  gather_facts: false

  tasks:
    - name: Run Claude Code CLI
      # shell, not command — command breaks on quoted arguments in the CLI invocation
      ansible.builtin.shell: >-
        claude -p
        "There is an alert on Zabbix, root cause analyse the alert and the state
        of the affected server, and fix it autonomously. Afterwards create an
        incident report and suggested further steps."
        --dangerously-skip-permissions
      args:
        # Claude Code needs a working directory with CLAUDE.md guardrails
        chdir: /home/aaptra/claude-wd
      # Controller connects as ansible user, but Claude must run as aaptra
      # (owns ~/.claude config, API keys, MCP wiring)
      become: true
      become_user: aaptra
      register: claude_output

    - name: Display incident report
      ansible.builtin.debug:
        var: claude_output.stdout_lines
```

The prompt does not inject the alert payload — the agent discovers the
active alert itself via Zabbix MCP. The `CLAUDE.md` guardrails
(phase discipline, AAP-only remediation) govern what happens next.

> **Optional tuning:** See [`docs/todo/demo-design.md`](todo/demo-design.md#playbook-invocation-tuning)
> for planned refinements (tool restrictions, turn limits, payload
> injection, structured output).

## Explicitly out of scope

- Deployment of individual MCP servers (linux-mcp container, Zabbix MCP)
  — covered in their own sections
- EDA rulebook configuration — covered in [06-eda-zabbix-integration](06-eda-zabbix-integration.md)
- Claude Code SDK (Python) as an alternative to CLI invocation
- Production hardening (rate limiting, cost controls, retry logic)
