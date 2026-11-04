# Deploy Claude and both private MCP integrations

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
instruction file. Existing user edits remain intact. The Linux and Zabbix
deployment playbooks keep their current private Podman/stdio transports, pinned
images, instance-local targets and read-only checks. No public MCP listener is
created. Their existing offline image/RPM manifests must already be prepared;
see [MCP deployment](10-mcp-deployment.md).

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
coordinated functional checks. Private AAP MCP also remains a separate prerequisite
for the guardrails' AAP investigation and remediation phases.

The current incident launcher still needs the streaming phase-output correction
required by the maintained guardrails before complete remediation acceptance.
This installation change does not silently redesign that launcher.

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
