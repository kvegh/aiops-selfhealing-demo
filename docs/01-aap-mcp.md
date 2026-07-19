# 01 – AAP MCP Server

The AAP MCP server is Claude's **sole write path** into the environment. It is
deployed by the AAP containerized installer itself, as an additional container
alongside the existing AAP growth-topology containers.

> **Note:** The Ansible MCP server is a Technology Preview feature in AAP 2.6/2.7.
> Official documentation: [Deploy Ansible MCP server on Ansible Automation Platform](https://docs.redhat.com/en/documentation/red_hat_ansible_automation_platform/2.7/extend-assembly_deploying_ansible_mcp_server)

## Environment

- Single-VM AAP 2.7 growth architecture, containerized, on RHEL
- Installer sources: `/opt/sources/ansible-automation-platform-containerized-setup-2.7-2`
- Installer runs as the AAP service user (here: `aap_service`)

## 1. Starting point

A stock inventory has no MCP configuration — only the commented-out section:

```
$ grep -i mcp inventory
# This section is for your Ansible MCP Server host(s)
# [ansiblemcp]
```

## 2. Configure the inventory

Two changes are required:

1. Uncomment the `[ansiblemcp]` group and add your AAP host to it:

```
[ansiblemcp]
YOUR_AAP_SERVER
```

2. Set the MCP variables (under `[all:vars]`):

```
mcp_allow_write_operations=true
mcp_extra_settings='[{"setting": "DEFAULT_PAGE_SIZE", "value": "25"}]'
```

- `mcp_allow_write_operations=true` — grants read-write access. This is what
  allows Claude to launch job templates. **This is the deliberate, single
  write path of the whole demo** — everything else (Linux MCP, Zabbix MCP)
  is read-only.
- `mcp_extra_settings` / `DEFAULT_PAGE_SIZE` — caps list-type API responses
  at 25 items, keeping tool responses small for the model context.

Resulting inventory state:

```
$ grep mcp inventory
[ansiblemcp]
mcp_allow_write_operations=true
mcp_extra_settings='[{"setting": "DEFAULT_PAGE_SIZE", "value": "25"}]'
```

## 3. Re-run the installer

```
$ ansible-playbook -i inventory ansible.containerized_installer.install
```


## 4. Verify

```
aap_service@aap-remote /opt/sources/ansible-automation-platform-containerized-setup-2.7-2
❯ podman ps | grep -i mcp 
242bc0f298c0  registry.redhat.io/ansible-automation-platform-27/mcp-server-rhel9:latest         /entrypoint.sh        About a minute ago  Up About a minute  8080/tcp, 8086/tcp  ansiblemcp
aap_service@aap-remote /opt/sources/ansible-automation-platform-containerized-setup-2.7-2
❯ 
```

You should see an `ansiblemcp` container running. The MCP server listens on
**port 8448** (HTTPS): `https://YOUR_AAP_SERVER:8448`

## 5. Trust the AAP CA on the client VM

The installer generates a self-signed CA for AAP. The MCP endpoint on port 8448
uses a certificate signed by it, so the VM running Claude Code must trust that CA.

Copy the CA certificate created by AAP at install time (`~/aap/tls/ca.crt`) from the AAP host to the TRA VM:

```
# On the AAP host, the CA lives at:
~/aap/tls/ca.crt        # home of the AAP service user

# On the client VM (RHEL):
$ sudo cp ca.crt /etc/pki/ca-trust/source/anchors/aap-ca.crt
$ sudo update-ca-trust extract
```

Verify:

```
$ curl -s -o /dev/null -w '%{http_code}\n' https://YOUR_AAP_SERVER:8448/mcp
```

Any HTTP status without a TLS error means the chain validates.

## 6. Create an API token

*TBD — token creation for the MCP server, RBAC inheritance notes.*

## 7. Connect Claude Code CLI

*TBD — `claude mcp add` with bearer token, session verification.*
