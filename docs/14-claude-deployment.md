# Deploy Claude and private MCP integrations

**Deploy Claude and MCP Servers** runs `playbooks/deploy_claude.yml` on the
selected TRA. It installs only Claude Code, provisions the explicitly approved
Vertex authentication, and imports the existing Linux and Zabbix MCP deployment
playbooks. It does not install the full Assistant Team environment.

The saved template uses the existing guest Machine credential, AIOps Playbook
Vault, TRA inventory limit and opaque runtime ciphertext. Arbitrary launch
variables are disabled. Reapply AIOps CaC to install its definition; configuration
import alone runs no installation or model request.

## Program and target verification

The exact native Linux x64 release URL, version, SHA-256 and size live in
`aiops_claude_release` in the existing private CaC. The selected TRA receives
that value as `demo_claude_release`. The reviewed pin was checked against the
official signed release manifest and Anthropic's published signing fingerprint.
See [native binary verification](https://code.claude.com/docs/en/setup#binary-integrity-and-code-signing).

The job verifies the same guest ownership, machine ID, runtime account and
pinned SSH keys used by the MCP jobs. It downloads the binary inside the AAP
execution environment using certificate-verified HTTPS, then checks its exact
size and SHA-256 before a managed write. TRA needs no additional download
exception. The temporary download and job-local SSH trust are removed after
success or failure.

The root-owned command is `/usr/local/bin/claude`. A different existing command,
symlink or ownership is preserved for explicit review; the job does not silently
replace another installation or upgrade a different pinned version. It verifies
that the actual agent user's noninteractive shell resolves that command and
that `claude --version` matches the approved release. No inference is involved.

## Workspace and private MCP configuration

The workspace defaults to the existing account's `claude-wd` directory.
`claude_agent_workdir` selects another normalized directory beneath that
account's actual home. The installer, both MCP client entries and protocol
verifiers use that same location. Each existing path component must be a real
directory owned by the runtime user; links, files and unrelated ownership stop
the job before directory creation. Existing directory permissions are preserved.

The existing `AI_Instructions_Guardrails/CLAUDE.md` seeds only a missing workspace
instruction file. It updates only the known unchanged previously managed copy; user edits or unrelated ownership stop for review. The Linux and Zabbix
deployment playbooks keep their current private Podman/stdio transports, pinned
images, instance-local targets and read-only checks. No public MCP listener is
created. Their containers are built on the selected TRA from pinned public
source recipes, using normal trusted RHEL packages and separate protected
runtime settings; see [MCP deployment](10-mcp-deployment.md).

## Approved Vertex authentication

The selected instance's existing runtime Vault contains `demo_claude_vertex_auth`
with `project_id`, `region` and the explicitly approved Google authorized-user
`adc` mapping. The existing opaque ciphertext transport decrypts it only in the
job, keeping its strings literal. No credential value belongs in inventory,
plaintext extra variables, logs or the public repository.

The job provisions only that ADC as a private user-owned file and merges the
selected Vertex environment into the user's Claude settings. It preserves
unrelated settings. A different existing ADC, other provider selection or
conflicting Vertex values stop provisioning for review. The files are rechecked
immediately before writing so concurrent account/configuration changes are not
overwritten. Existing authentication directories are not chmodded or replaced.

`claude auth status --json` must recognize the approved Vertex method. That is
configuration readiness, not proof that a model request succeeds. The installer
does not log in, invoke a model, enable an EDA activation or simulate a fault.
The short approved read-only model/MCP test and full agent repair are separate
coordinated functional checks.

## Selected private AAP MCP and bounded repair

After compatible readers are published, run the existing AutoDeploy base
configuration for the selected instance to publish its verified public CA and
private MCP endpoint alongside its unchanged API/MCP token. Refresh AutoDeploy
CaC on the receiving AAP, then AIOps CaC. Existing AIOps preparation copies only
that selected connection into the existing whole-file runtime Vault; it never
uses SSH or copies another instance's token. The normal combined installer
merges its private HTTP client entry and verifies native read access. It adds no
public MCP route, global trust, credential type or secret store.

The CA file stays in the validated application workspace.
`NODE_EXTRA_CA_CERTS` adds it only to the agent process; system trust and other
Claude settings stay unchanged. Native child-job modules use `SSL_CERT_FILE`
only in their process for the same verified CA. The native client bearer remains in private
files, never the model prompt or command arguments. Provider authentication
requires its own explicit per-instance approval and is not automatically copied
into later namespaces.

**Run Claude to analyse and fix** supports the selected agent-unavailable demo.
It verifies the existing same-project repair template, saved inventory/limit and
selected guest identity before invoking Claude. Native permissions remain on;
no general command/edit tools or permission bypass are enabled. A tiny
invocation-only [PreToolUse check](https://code.claude.com/docs/en/hooks)
denies another repair ID, launch overrides or remote Linux host. Its successful
return grants no permissions and preserves other native denials/hooks. The
existing administrator/write token remains broader than one template; this is
a controlled functionality demo, not per-template RBAC.

One run is limited to 48 turns and 600 seconds. The existing saved Job Template
has an outer timeout; private invocation files are removed on success/failure.
Ordered phase messages and the final report are displayed after completion;
live UI streaming is not required for this functional test. Completion also
requires successful native repair children, an active selected agent service,
a new successful monitoring sample and recovery of the original trigger.
A successful model narrative cannot satisfy these checks. Unsupported incidents
fail clearly rather than expanding into other repairs.

The isolated service-outage rehearsal passed with one real monitoring event,
one EDA-launched agent invocation and one successful saved repair. The native
service and fresh original-trigger recovery checks also passed. Package removal
and migration of the pinned production runner were outside that rehearsal.

The existing agent playbook imports the official repository signing key using
its full verified fingerprint and leaves RPM signature verification enabled.
General agent forwarding/activation and a controlled fault remain separate
explicit launch steps; publishing these changes starts none of them.

HTTP MCP checks use native `uri`/assert tasks; child monitoring uses the
certified `ansible.controller.job_wait` and `job_list` modules. The existing
stdio MCP verifier, selected-data/stream filters and invocation hook remain
custom code for their protocol/tool-request boundaries. Consolidating such code into suitable standard content is tracked
separately; this change introduces no service or orchestration framework.

The collection requirement pins certified `ansible.controller` to the version
already declared in the existing AIOps PAH prerequisites; normal project sync
uses that content and retains the existing community collection dependency.

## Preserve the existing production runner during migration

The existing production SCM Project intentionally stays pinned to its tested
commit `b32ceb675d2699205400daee327f9b89ddb5f10a`. Its older runner lacks the
encrypted runtime input and associated Vault credential required by this version.
The owner approved this production-only exception before publication. The
Controller's automatic update after saving the pin succeeded at that revision;
no production runner or guest configuration was changed.

Shared desired CaC remains on `main` for test and future instances. Remove the
production pin only after deliberately supplying and verifying its selected
runtime, Vault credential, private MCP connection and maintained instructions.
Do not remove it merely because the newer test deployment has passed.

## Local validation

Use the existing toolchain; install no dependencies automatically:

```bash
ANSIBLE_LOCAL_TEMP=/tmp/aiops-claude-tests python3.12 -m unittest discover -s tests -p test_claude_deployment.py -v
ANSIBLE_LOCAL_TEMP=/tmp/aiops-claude-runtime python3.12 -m unittest discover -s tests -p test_runtime_settings.py -v
ansible-playbook --syntax-check -i localhost, playbooks/deploy_claude.yml
```

Before a live launch, coordinate shared TRA work and take a fresh AAP object
baseline. Inspect the actual terminal job result and its CLI/MCP checks. Imported
definitions or passing local fixtures do not establish a successful deployment.
