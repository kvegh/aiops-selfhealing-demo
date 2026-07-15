# 03 – Linux MCP Server

The linux-mcp server gives Claude **read-only** diagnostic access to the
managed RHEL target host. It connects over SSH and exposes system
inspection tools (services, logs, processes, network, storage) via MCP
stdio transport.

The server runs as a container on the TRA VM — the same host where
Claude Code CLI runs — so the connection is a local stdio pipe, no
network listener required.

> **Note:** The MCP server for RHEL is Developer Preview software.
> It ships for RHEL 10 but works against RHEL 9 targets.
> Official documentation: [Using the MCP server for RHEL to enable AI assistants to run, discover, and troubleshoot complex issues](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/interacting_with_the_command-line_assistant/using-the-rhel-mcp-server-to-enable-ai-assistants-to-run-discover-and-troubleshoot-complex-issues)

## Environment

- TRA VM: RHEL 9, base installation (from [00-starting-setup](00-starting-setup.md))
- Target: `rhel-target` VM, RHEL 9, reachable from TRA over SSH (port 22)
- Container runtime: Podman (from `container-tools`)

## 1. Install container tools on the TRA VM

```bash
sudo dnf install -y container-tools
```

Verify:

```bash
podman --version
```

## 2. Prepare SSH key-based authentication

The containerized MCP server connects to the target host over SSH using
key-based authentication. You need an SSH keypair whose public key is
authorized on the target host.

> Creating the keypair itself is out of scope — use an existing key or
> generate one with `ssh-keygen`. What matters is that the private key
> is available on the TRA VM and the public key is in
> `~/.ssh/authorized_keys` on the target host.

### Store the private key

Place the private key in a dedicated location on the TRA VM:

```bash
mkdir -p /opt/tra/keys
cp ~/.ssh/id_ed25519_mcp /opt/tra/keys/target-key
chmod 600 /opt/tra/keys/target-key
```

The container runs as UID 1001. Set ownership accordingly:

```bash
chown 1001:0 /opt/tra/keys/target-key
```

### Create the SSH config

The MCP server uses `~/.ssh/config` inside the container to resolve host
aliases. Create a config file that maps your target host alias:

```
Host rhel-target
    HostName TARGET_IP
    User mcp
    Port 22
    IdentityFile /var/lib/mcp/.ssh/id_ed25519
    StrictHostKeyChecking no
```

Save this as `/opt/tra/keys/ssh-config` on the TRA VM. The
`IdentityFile` path is the container-internal mount point, not the host
path.

Set ownership to match the container user:

```bash
chown 1001:0 /opt/tra/keys/ssh-config
```

### Create the log directory

The MCP server writes logs to a directory that must exist before the
container starts:

```bash
mkdir -p ~/.local/share/linux-mcp-server/logs
```

## 3. Pull the container image

```bash
podman pull quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest
```

## 4. Test-run the container

Run the MCP server manually to verify the SSH connection works:

```bash
export LINUX_MCP_USER=mcp

podman run --rm --interactive \
    --userns keep-id:uid=1001,gid=0 \
    -e LINUX_MCP_USER \
    -v /opt/tra/keys/target-key:/var/lib/mcp/.ssh/id_ed25519:ro,Z \
    -v /opt/tra/keys/ssh-config:/var/lib/mcp/.ssh/config:ro,Z \
    -v $HOME/.local/share/linux-mcp-server/logs:/var/lib/mcp/.local/share/linux-mcp-server/logs:rw,Z \
    quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest
```

The server starts in stdio mode and prints initialization messages.
Press `Ctrl+C` then `Return` to stop it.

Key flags explained:

| Flag | Purpose |
|------|---------|
| `--rm` | Remove the container after exit |
| `--interactive` | Keep stdin open (required for stdio transport) |
| `--userns keep-id:uid=1001,gid=0` | Map the host user to UID 1001 inside the container (the MCP server's runtime user) |
| `-e LINUX_MCP_USER` | SSH username on the target host |
| `-v .../target-key:...id_ed25519:ro,Z` | Mount the SSH private key read-only |
| `-v .../ssh-config:...config:ro,Z` | Mount the SSH config read-only |
| `-v .../logs:...:rw,Z` | Mount the log directory read-write |

> **If the SSH key has a passphrase**, also pass
> `-e LINUX_MCP_KEY_PASSPHRASE=<passphrase>`. For this demo we assume
> an unencrypted key.

## 5. Configure Claude Code to use linux-mcp

The Claude Code agent (set up in [04-claude-agent](04-claude-agent.md))
connects to the containerized MCP server via stdio. The relevant entry
in `/opt/tra/agent/.mcp.json`:

```json
{
    "linux-mcp": {
        "type": "stdio",
        "command": "podman",
        "args": [
            "run", "--rm", "--interactive",
            "--userns", "keep-id:uid=1001,gid=0",
            "-e", "LINUX_MCP_USER",
            "-v", "/opt/tra/keys/target-key:/var/lib/mcp/.ssh/id_ed25519:ro,Z",
            "-v", "/opt/tra/keys/ssh-config:/var/lib/mcp/.ssh/config:ro,Z",
            "-v", "/home/USER/.local/share/linux-mcp-server/logs:/var/lib/mcp/.local/share/linux-mcp-server/logs:rw,Z",
            "quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest"
        ],
        "env": {
            "LINUX_MCP_USER": "mcp"
        }
    }
}
```

Replace `USER` with the actual username on the TRA VM and `mcp` with
the SSH user on the target if different.

## 6. Verify

From the agent directory, test that Claude Code can reach the target
host through linux-mcp:

```bash
cd /opt/tra/agent
claude -p "Use linux-mcp to check the OS version on the target host." \
    --permission-mode bypassPermissions \
    --max-turns 5
```

The agent should return the RHEL version of the target host.

## Explicitly out of scope

- SSH keypair generation
- Target host user creation and `authorized_keys` setup
- MCP server installation via pip (we use the container method)
- Read/write mode configuration (this demo uses read-only, the default)
- Claude Code CLI installation and full MCP wiring (covered in [04-claude-agent](04-claude-agent.md))
