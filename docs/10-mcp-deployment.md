# Deploy the Linux and Zabbix MCP servers on the selected TRA

The two Job Templates use the existing AIOps Project and separate playbooks:

| Job Template | Playbook | Destination |
| --- | --- | --- |
| Deploy Linux MCP Server | `playbooks/deploy_linux_mcp.yml` | The matching new TRA |
| Deploy Zabbix MCP Server | `playbooks/deploy_zabbix_mcp.yml` | The matching new TRA |

Both preserve the existing on-demand Podman/stdio transport.
They create no network listener, public port or persistent MCP service. The
existing guest account runs the containers and owns its client configuration.
The separate combined [Claude deployment job](14-claude-deployment.md) installs
the CLI, provisions approved Vertex authentication and imports these same plays.
The two standalone MCP jobs do not invoke a model or run the remediation agent.

## Select the existing instance and its verified guests

The imported TRA inventory entry receives `demo_mcp_deployment` from the
encrypted private AIOps capture. Its `aiops_instances` map uses the selected
AAP inventory entry's existing `vm_resource.vm_name` key and owns the verified
`tra`, `testserver1` and `zabbix` metadata. An inventory alias
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

## Target-side image builds

Before package installation, the existing MCP path prepares this selected TRA's
RHSM registration and enables only the required RHEL 9 BaseOS and AppStream
repositories. The selected namespace in the existing encrypted runtime Vault
must supply `demo_mcp_subscription` with `instance_name`, `organization`, a
nonempty `activation_keys` list and `repositories`. The latter contains exactly
the RHEL 9 x86-64 BaseOS/AppStream IDs as `{name: REPOSITORY_ID, state: enabled}`
mappings. Never put the organization or activation keys in inventory or plaintext
launch variables. The standalone Linux job now uses the same native runtime
loader as the other protected jobs.

The certified `redhat.rhel_system_roles` collection is pinned to `1.120.5`.
Its `rhc` role's complete entrypoint also manages Insights, and its packaged
modules explicitly prohibit direct use. This job therefore invokes only the
role's shipped `set_vars.yml` and `subscription-manager.yml` task entries.
These filenames are coupled to that exact collection version and must be
rechecked on an upgrade; they are not advertised as a separate public role API.
Registration uses `rhc_state: present`, preserving an existing valid identity;
the role enables the requested repositories with `purge: false`, preserving
unrelated repositories. Insights registration, existing Insights configuration,
remediation services and system release pins are untouched. TLS and RPM
signature checks remain enabled. Missing RHSM tooling/content entitlement stops
the job rather than forcing re-registration or transferring RPM bundles.

The selected TRA installs `podman`, `git`, `fuse-overlayfs` and `slirp4netns`
from its configured trusted RHEL repositories through normal Ansible package
management. Package signature checking stays enabled. Existing subordinate
user/group allocations must support rootless Podman. No RPM bundle, image
archive, hypervisor staging directory or hypervisor private key is needed.

Each public playbook fixes the upstream source, immutable revision and native
recipe used for its container:

| Server | Public source | Revision | Recipe |
| --- | --- | --- | --- |
| Linux MCP | `https://github.com/rhel-lightspeed/linux-mcp-server.git` | `1d15590f0ebad724e2e331ecd2bd9186f7eef478` | `Containerfile` |
| Zabbix MCP | `https://github.com/initMAX/zabbix-mcp-server.git` | `c3b93d5a1a4678d211d38a2a539a15241da65109` | `Dockerfile` |

The upstream recipes are reused unchanged from their pinned public checkouts.
The selected Linux recipe uses UBI 10; the Zabbix recipe uses its existing
Debian-based Python image. This does not change the separate Claude CLI image.
TRA needs network access to its trusted package repositories and the public
source/base-image/dependency endpoints used by these recipes. TLS verification
remains enabled. Four GiB free space is the initial build headroom check;
actual build disk and memory usage still need live verification.

Builds run as the existing runtime user, in a job-created temporary source
checkout beneath that user's home. Only the public checkout is the build
context. Tokens, SSH private keys, Vertex authentication and instance settings
stay outside it and are supplied later through the existing protected runtime
configuration. The temporary checkout is removed after success or failure.

The temporary public checkout receives only the SELinux type `container_file_t`
through native Ansible file attributes, recursively without following symlinks.
The confirmed target failure was an enforcing SELinux denial: `container_t`
could not execute the upstream RPM-install script still labeled `user_home_t`.
The script already had its upstream executable mode. Correcting only this
temporary build context preserves its owner/modes, home and storage labels,
SELinux enforcement and the unchanged upstream recipe. The build itself still
runs as the existing unprivileged user. Labeling must succeed before building;
no security-disable or privileged-container option is added.

If the container build fails, its standard output and standard error are saved
only as the runtime user's `build.log` in the server's private log directory:
`~/.local/share/linux-mcp-server/logs` or
`~/.local/share/zabbix-mcp-server/logs`. Directory mode is `0700` and file mode is
`0600`; the public job output retains protected logging. The job still fails,
and its temporary source checkout is still removed. Successful builds create
no diagnostic file; an earlier failure log may remain after a later success.
This preserves evidence for diagnosis and does not fix or conceal a failed build.

The image keeps its existing local name and records the pinned commit in the
standard OCI `org.opencontainers.image.revision` label. A repeat deployment
skips building when that label already matches. After a build, the job checks
it again. No custom build-state or ownership file is deployed. Client runs
retain `--pull=never` and the existing private stdio invocation.

The installed certified Podman role handles runtime configuration but exposes
no public image-build interface. The shared Ansible tasks therefore invoke
native `podman build` with an argument list; no shell wrapper or custom module
is introduced. Source checkout and package management use standard modules.
The existing source/guest filter remains for the selected-instance identity
checks; its obsolete offline-artifact validator is removed.

The per-instance private CaC no longer needs `mcp_artifacts` or an `artifacts`
manifest. Remove those obsolete runtime inputs when publishing the refreshed
settings, preserving the instance's guest, hypervisor and secret entries.
Registry images and a separate build host are deferred future work.

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

The existing Zabbix MCP invocation uses numeric UID/GID `999:999`. Its
rootless invocation maps the existing TRA user to those image IDs with
`--userns keep-id:uid=999,gid=999`, allowing that intended non-root process to
read its owner's `0600` configuration. The read-only mount, file permissions,
SELinux label and server read-only policy remain in place. The final authenticated stdio check must pass with the newly built image;
revalidate its image user if that existing mapping fails.

The earlier native permission regression used the saved image and unchanged
private configuration: its original default mapping fails the configuration
read; the explicit mapping initialized stdio and completed an authenticated
read-only query. The normal Job Template retains that real query as its final
required verification.

The job merges only the corresponding MCP entry into the existing user's
`~/claude-wd` project configuration, or the same `claude_agent_workdir` used by
the incident job. The override must remain beneath the verified user's home.
Existing path components are checked without following links before creation;
existing directory modes and user instruction files are preserved.
Existing client settings and other MCP
entries are preserved. Verification initializes the actual stdio command,
discovers tools and performs an authenticated read-only `host_get` count query.
The server's raw-data disclaimer remains enabled; verification interprets only
the returned count and never requests removal of that disclaimer. After the
exact known disclaimer, its JSON-encoded count is decoded and must still be
numeric; errors, empty values and object/list responses fail verification.

## Verification and remaining application setup

Run the focused local checks using the existing toolchain:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/aiops-mcp-tests python3.12 -m unittest discover -s tests -p 'test_mcp*.py' -v
ansible-playbook --syntax-check -i localhost, playbooks/deploy_linux_mcp.yml playbooks/deploy_zabbix_mcp.yml
```

After each actual AAP run, inspect its terminal result and protocol verification.
Secret configuration and error logs stay protected; do not publish populated
configuration or raw error responses. Successful MCP deployment does not install
Claude Code, supply model-provider credentials, execute the agent or enable an
EDA activation. Those application stages require their own reviewed readiness.

Earlier archive-based deployments passed their normal Linux and Zabbix MCP
jobs and read-only protocol checks. The new target-side build path has focused
local Ansible tests for building, repeat-run skipping, source-revision refusal
and cleanup after failure. Its actual package solve, container builds and final
MCP queries still need normal AAP verification on the selected TRA. Those live
results must be distinguished from the earlier archived-image acceptance.
Website health and the full event/remediation loop remain separate checks.

## Native AAP MCP baseline

The platform's separate native MCP server remains private on its existing TLS
port `8448`, matching production. Public HTTPS `/mcp` is not routed to that
component and returns the same response as production. The owner has explicitly
excluded public MCP exposure. These TRA deployment jobs add no public MCP route,
listener or port and do not change the platform MCP service.
