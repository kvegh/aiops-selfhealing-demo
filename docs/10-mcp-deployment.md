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

The imported TRA inventory entry receives `demo_mcp_deployment` from the
encrypted private AIOps capture. Its `aiops_instances` map uses the selected
AAP inventory entry's existing `vm_resource.vm_name` key and owns the verified
`tra`, `testserver1`, `zabbix` and `mcp_artifacts` metadata. An inventory alias
rename leaves that physical/runtime key and the encrypted settings unchanged.
The selected AAP entry supplies its existing allocation and AAP identity.
All guests must belong to the same allocation and verified hypervisor. Their
public SSH keys and live machine identities are checked before changes.

Each MCP job uses exactly one existing native Machine credential: the base
guest login selected by `guest_machine_credential_name`. AAP connects directly
to TRA and the testserver on their existing guest bridge. There is no
hypervisor SSH hop and the base Machine credential receives no hypervisor key.
The existing runtime Vault credential decrypts the selected instance's
[whole-file runtime settings](11-protected-runtime-settings.md).
Do not substitute old production addresses, passwords or tokens.

## Prepare offline runtime artifacts

The new TRA needs Podman and its rootless runtime dependencies. Keep the
existing network isolation: download the signed RHEL RPM dependency closure
through the already prepared hypervisor, without installing staging tools or
packages there, and copy it through the approved management connection.
Inspect repository entitlement and existing download capability first.

Resolve the requested Podman, fuse-overlayfs and slirp4netns packages against
the selected guest's actual installed RPM database before recording the install
set. A download-only dependency list can omit conditional SELinux providers.
Stage those signed providers as needed, expose the verified local RPMs to a
read-only dependency solve with repositories disabled, and require a solution
without installed package removals. The manifest's `rpms` list contains that
minimal install set. This avoids forcing unrelated base-library upgrades just
because newer dependency files were downloaded. Keep signature verification,
SELinux policy and protected-package checks enabled throughout.

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
production `myvars` or reuse an ambient token. Put the reviewed token in that
instance's private runtime Vault and reapply its ciphertext through the existing
CaC import. The job decrypts only through the attached native Vault credential;
missing input fails before managed changes. Importing definitions launches no
server. Inline Vault launch scalars and JSON Vault-marker mappings are
unsupported by Controller and are not used as a fallback.

The existing `/etc/zabbix-mcp/config.toml` shape is retained with mode `0600` and
the existing container SELinux label. It keeps stdio, the monitoring tool
categories, compact output and `read_only = true`. The source `verify_ssl`
setting is retained for the private HTTP endpoint; no public HTTPS certificate
check is disabled. The public Zabbix UI retains its independent trusted HTTPS
and Basic-auth protection, with no public API exception.

The approved saved Zabbix MCP image runs as numeric UID/GID `999:999`. Its
rootless invocation maps the existing TRA user to those image IDs with
`--userns keep-id:uid=999,gid=999`, allowing that intended non-root process to
read its owner's `0600` configuration. The read-only mount, file permissions,
SELinux label and server read-only policy remain in place. Revalidate the
image user when deliberately replacing the pinned image artifact.

The native permission regression uses the exact saved image and unchanged
private configuration: its original default mapping fails the configuration
read; the explicit mapping must initialize stdio and complete an authenticated
read-only query. The normal Job Template retains that real query as its final
required verification.

The job merges only the corresponding MCP entry into the existing user's
`~/claude-wd` project configuration. Existing client settings and other MCP
entries are preserved. Verification initializes the actual stdio command,
discovers tools and performs an authenticated read-only `host_get` count query.
The server's raw-data disclaimer remains enabled; verification interprets only
the returned count and never requests removal of that disclaimer. After the
exact known disclaimer, its JSON-encoded count is decoded and must still be
numeric; errors, empty values and object/list responses fail verification.

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

Both normal MCP deployment jobs have now succeeded on the fresh TRA. Linux MCP
returned the matching new testserver's system identity; Zabbix MCP initialized
stdio, discovered its tools and completed an authenticated read-only host-count
query against the verified new clone. The private configuration and rootless
image identity are checked separately from the completed job status. Website
health and the full event/remediation loop are not established by these queries.

## Native AAP MCP baseline

The platform's separate native MCP server remains private on its existing TLS
port `8448`, matching production. Public HTTPS `/mcp` is not routed to that
component and returns the same response as production. The owner has explicitly
excluded public MCP exposure. These TRA deployment jobs add no public MCP route,
listener or port and do not change the platform MCP service.
