# 02 – Linux MCP Server

The linux-mcp server gives Claude **read-only** diagnostic access to the
managed RHEL target host. It connects over SSH and exposes system
inspection tools (services, logs, processes, network, storage).

The server runs as a container on the TRA VM — the same host where
Claude Code CLI runs — so the connection is a local stdio pipe, no
network listener required.

> **Note:** The MCP server for RHEL is Developer Preview software.
> It ships for RHEL 10 but works against RHEL 9 targets.
> Official documentation: [Using the MCP server for RHEL to enable AI assistants to run, discover, and troubleshoot complex issues](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/interacting_with_the_command-line_assistant/using-the-rhel-mcp-server-to-enable-ai-assistants-to-run-discover-and-troubleshoot-complex-issues)

## Environment

- TRA VM: RHEL 9, base installation (from [00-starting-setup](00-starting-setup.md))
- Target: `testserver1`, RHEL 9, reachable from TRA by hostname over SSH (port 22)
- Container runtime: Podman (from `container-tools`)
- SSH user on target: `mcp` (SSH key authentication, no sudo — read-only diagnostics only)
- The TRA user's default SSH key (`~/.ssh/id_ed25519`) is already
  authorized on the target host for the `mcp` user

### Target host preparation

The `mcp` user on the target host does **not** need sudo. The linux-mcp
server's diagnostic tools (`systemctl status`, `ss`, `journalctl`,
`ps`, etc.) run without elevated privileges.

For full diagnostic access, the `mcp` user needs:

- Membership in the `systemd-journal` group (for `journalctl` access):

  ```bash
  sudo usermod -aG systemd-journal mcp
  ```

- ACLs on log files that are `root:root 600` on RHEL:

  ```bash
  sudo setfacl -m u:mcp:r /var/log/messages
  sudo setfacl -m u:mcp:r /var/log/secure
  ```

## 1. Create the SSH config

The linux-mcp server runs inside a container and cannot resolve
hostnames or execute commands on the host directly — all inspection
happens over SSH to the target. The container needs an SSH config
to map hostnames to connection parameters.

Create `~/.ssh/config` on the TRA VM:

```
Host testserver1
    HostName TARGET_IP
    User mcp
    IdentityFile /var/lib/mcp/.ssh/id_ed25519
    StrictHostKeyChecking no
```

Replace `TARGET_IP` with the IP address of the target host.

The `IdentityFile` path is the **container-internal** mount point, not
the host path — the SSH config is read inside the container where the
key is mounted at `/var/lib/mcp/.ssh/id_ed25519`.

## 2. Install container tools on the TRA VM

```bash
sudo dnf install -y container-tools
```

## 3. Pull the container image

```bash
podman pull quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest
```

## 4. Create the log directory

```bash
mkdir -p ~/.local/share/linux-mcp-server/logs
```

## 5. Add linux-mcp to the Claude Code configuration

Add the `linux-mcp` entry to the `mcpServers` block in `~/.claude.json`,
next to the AAP MCP server configured in [01-aap-mcp](01-aap-mcp.md):

```json
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
}
```

Replace `USER` with the local username on the TRA VM (the user that
runs Claude Code).

Mounting the entire `~/.ssh` directory gives the container access to
the private key, SSH config, and `known_hosts` in a single mount.

Key flags explained:

| Flag | Purpose |
|------|---------|
| `--rm` | Remove the container after exit |
| `--interactive` | Keep stdin open (required for stdio transport) |
| `--userns keep-id:uid=1001,gid=0` | Map the host user to UID 1001 inside the container (the MCP server's runtime user) |
| `-e LINUX_MCP_USER=mcp` | SSH username on the target host |
| `-v .../.ssh:...:ro,Z` | Mount the entire SSH directory read-only (key, config, known_hosts) |
| `-v .../logs:...:rw,Z` | Mount the log directory read-write |

Claude Code launches the container automatically at startup via the
stdio transport — no manual `podman run` needed.

> **Note:** The first connection attempt may time out while podman sets
> up the user namespace. Reconnecting from the MCP status screen
> resolves this.

## 6. Verify

Start Claude Code from the agent directory and test:

```bash
cd /opt/tra/agent
claude -p "Use linux-mcp to check the OS version on testserver1." \
    --permission-mode bypassPermissions \
    --max-turns 5
```

The agent should return the RHEL version of the target host.

## Why an SSH config is needed

The linux-mcp server runs inside a container. It cannot execute commands
on the host directly — all system inspection happens over SSH to the
target. The container detects that it is containerized and refuses local
execution, requiring a `host` parameter on every tool call.

The SSH config mounted into the container maps human-readable hostnames
to connection parameters (IP, user, key path) so that tool calls can
reference a short hostname (e.g. `testserver1`) instead of raw IPs.

## Explicitly out of scope

- SSH keypair generation
- Target host user creation and `authorized_keys` setup
- MCP server installation via pip (we use the container method)
- Read/write mode configuration (this demo uses read-only, the default)
- Sudo for the remote `mcp` user (not needed for read-only diagnostics)
- Claude Code CLI installation and full MCP wiring (covered in [04-claude-agent](04-claude-agent.md))
