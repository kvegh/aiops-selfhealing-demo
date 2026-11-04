# Deploy the Linux and Zabbix MCP servers on the selected TRA

The two Job Templates use the existing AIOps Project and separate playbooks:

| Job Template | Playbook | Destination |
| --- | --- | --- |
| Deploy Linux MCP Server | `playbooks/deploy_linux_mcp.yml` | The matching new TRA |
| Deploy Zabbix MCP Server | `playbooks/deploy_zabbix_mcp.yml` | The matching new TRA |

Both preserve the working Podman containers and on-demand stdio transport.
They create no network listener, public port or persistent MCP service. The
existing guest account runs the containers and owns its client configuration.
Claude Code CLI installation, provider authentication and agent execution are
separate tasks; these jobs do not invoke a model or run the remediation agent.

## Select the existing instance and its verified guests

The imported TRA inventory entry receives `demo_mcp_deployment` from the source
inventory's selected AAP entry. It uses that entry's existing allocation,
`aiops_tra`, `aiops_testserver`, `aiops_zabbix` and offline artifact metadata.
All guests must belong to the same allocation and verified hypervisor. Their
public SSH keys and live machine identities are checked before changes.

Each MCP job uses exactly one existing native Machine credential: the base
guest login selected by `guest_machine_credential_name`. AAP connects directly
to TRA and the testserver on their existing guest bridge. There is no
hypervisor SSH hop and the base Machine credential receives no hypervisor key.
The existing runtime Vault credential is retained. Runtime secret delivery is
awaiting an owner decision; secret-dependent application jobs remain gated.
Do not substitute old production addresses, passwords or tokens.

## Prepare offline runtime artifacts

The new TRA needs Podman and its rootless runtime dependencies. Keep the
existing network isolation: download the signed RHEL RPM dependency closure
through the already prepared hypervisor, without installing staging tools or
packages there, and copy it through the approved management connection.
Inspect repository entitlement and existing download capability first.

Save the two already installed image artifacts, preserving their image IDs:

- `quay.io/redhat-services-prod/rhel-lightspeed-tenant/linux-mcp-server:latest`
- `localhost/zabbix-mcp-server:latest`

Stream archives to the hypervisor when the source VM lacks space. Stage them
and the RPMs under `/opt/aiops-mcp-artifacts/vNN` on the selected TRA after
checking its free space. No registry pull is needed. Never put archives, RPMs,
populated manifests or credentials in the public repository.

The reviewed manifest has `schema_version: 1`, the existing `counter`, image
entries containing `name`, `archive`, `image_id`, `sha256`, `bytes`, and RPM
entries containing `path`, `nevra`, `sha256`, `bytes`, `signature_verified`.
Archives are `linux-mcp.tar` and `zabbix-mcp.tar`; RPMs are under `rpms/` in
that same version's directory. Actual paths, hashes and metadata belong in
the selected instance's protected configuration/inventory handoff.

The jobs check manifest identity, paths, file sizes and SHA-256 values. They
verify RPM signatures against existing signing trust and install only local
RPMs with all repositories disabled. Existing subordinate user/group ID ranges
must support rootless Podman; no rootful fallback is used. Each image is loaded
into the existing user's image store and checked against the approved source
image ID. Client invocations use `--pull=never`.

## Linux MCP access

The Linux job generates a fresh instance client key on TRA. The private key
stays there in a private MCP SSH directory. Using the existing Machine login,
the job checks the new testserver's machine ID and installs only the public
half into its existing guest account without replacing management access.

The container's `testserver1` alias points only to that new address and uses its
fresh SSH public host keys. Host verification is enabled. The dedicated
directory is mounted read-only at `/var/lib/mcp/.ssh`, preserving the existing
container path without relabeling unrelated management SSH files. The existing
user-namespace mapping and writable log mount are retained.

The source image defaults to its fixed diagnostic toolset. Verification checks
that script-execution tools are absent, initializes stdio, calls
`get_system_information` for the alias and requires the expected new hostname.
No fault or write operation is used as a verification test.

## Zabbix MCP access

Zabbix must already be deployed and quarantined for this allocation. Its verified
artifact supplies the exact new private API address. The Zabbix MCP job requires
the explicitly selected target's `demo_zabbix_mcp_api_token`; it does not load
production `myvars` or reuse an ambient token. Supply that token only through
the protected runtime-input method after the owner selects it. Its saved
defaults are empty, so importing this job does not require a token or launch
the server. Inline Vault launch scalars and JSON Vault-marker mappings are
unsupported by Controller and are not used as a fallback.

The existing `/etc/zabbix-mcp/config.toml` shape is retained with mode `0600` and
the existing container SELinux label. It keeps stdio, the monitoring tool
categories, compact output and `read_only = true`. The source `verify_ssl`
setting is retained for the private HTTP endpoint; no public HTTPS certificate
check is disabled. The public Zabbix UI retains its independent trusted HTTPS
and Basic-auth protection, with no public API exception.

The job merges only the corresponding MCP entry into the existing user's
`~/claude-wd` project configuration. Existing client settings and other MCP
entries are preserved. Verification initializes the actual stdio command,
discovers tools and performs an authenticated read-only `host_get` count query.
The server's raw-data disclaimer remains enabled; verification interprets only
the returned count and never requests removal of that disclaimer.

## Verification and remaining application setup

Run the focused local checks using the existing toolchain:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/aiops-mcp-tests python3.12 -m unittest discover -s tests -p test_mcp_deployment.py -v
ansible-playbook --syntax-check -i localhost, playbooks/deploy_linux_mcp.yml playbooks/deploy_zabbix_mcp.yml
```

After each actual AAP run, inspect its terminal result and protocol verification.
Secret configuration and error logs stay protected; do not publish populated
configuration or raw error responses. Successful MCP deployment does not install
Claude Code, supply model-provider credentials, execute the agent or enable an
EDA activation. Those application stages require their own reviewed readiness.

## Native AAP MCP baseline

The platform's separate native MCP server remains private on its existing TLS
port `8448`, matching production. Public HTTPS `/mcp` is not routed to that
component and returns the same response as production. The owner has explicitly
excluded public MCP exposure. These TRA deployment jobs add no public MCP route,
listener or port and do not change the platform MCP service.
