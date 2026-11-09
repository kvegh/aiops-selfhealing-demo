# Protected runtime settings in the existing private AIOps repository

The private companion owns both the desired AIOps guest configuration and the
runtime settings. The AutoDeploy configuration retains AAP's own allocation,
VM, FQDN and API token. No new repository, credential type, service or job is
required for application settings.

## Files and credential

`vaults/runtime/aiops-selfhealing-demo-runtime-vault.yml` is a whole-file Ansible
Vault document encrypted with the existing **AIOps Playbook Vault** credential.
It uses this structure, shown only with placeholders:

```yaml
schema_version: 1
instances:
  aap27-test-7:
    demo_website_dns_api_token: !unsafe REPLACE_WITH_DNS_AUTHORIZATION
    demo_website_fault_template_id: 123
    demo_website_webhook_key: !unsafe REPLACE_WITH_TARGET_WEBHOOK_KEY
```

The `instances` key uses the VM name recorded in the selected AAP inventory
entry's `vm_resource.vm_name`. The launch input `aap_instance_key` selects that
inventory entry. Renaming the inventory alias leaves the created VM name and
runtime namespaces unchanged; missing VM metadata stops configuration rather
than guessing another namespace.

Keep credential text explicitly `!unsafe` so it remains literal data after
decryption. Actual instance names, host facts and settings are encrypted. The
fixed allowed variable names are listed in `playbooks/filter_plugins/demo_runtime.py`;
the application procedures describe their required values. Unknown names,
unexpected document fields and missing selected-instance namespaces are rejected.

The existing encrypted CaC capture contains an unchanged copy of this file's
ciphertext in `aiops_runtime_settings_vault`. The existing Enable, Zabbix Demo,
Linux/Zabbix MCP and combined Claude templates receive it as the ordinary string variable
`demo_runtime_settings_vault`. The saved value is ciphertext; individual
plaintext tokens, passwords and keys are not stored in template extra variables.

## Update and deploy the settings

1. Edit the private runtime file with `ansible-vault edit`, using its existing
   runtime Vault key. Add only the selected instance's reviewed values.
2. From the private repository, refresh its encrypted capture using its separate
   existing CaC Vault key:

   ```bash
   python3.12 scripts/embed_runtime_settings.py --cac-vault-password-file /secure/path/cac-vault-password
   ```

   This maintenance command copies opaque ciphertext, preserves explicit literal
   tags, validates the native YAML/encryption roundtrip and prints no secrets.
3. Review, commit and push both encrypted files together. Run the existing AIOps
   CaC importer for the selected AAP instance. This updates saved ciphertext on
   the existing application templates and launches no application itself.
4. Launch the required existing application template with its saved Machine and
   runtime Vault credentials. There is no need to enter individual secrets at
   launch or create an additional dispatcher job.

The target-generated website fault-template ID/webhook key and Event Stream
URL/Basic credentials must be read from that selected AAP after the initial CaC
import. Update the private runtime file and reapply the same CaC when those
values become available. Missing values stop the dependent application before
managed writes. Never substitute a production URL or an unverified token.

## Native runtime handling

The shared task writes only the opaque whole-file ciphertext to a temporary file
in the execution environment, mode `0600`, with native copy decryption disabled.
Native `include_vars` then decrypts it using the attached existing Vault
credential. The task checks the selected allocation namespace and fixed allowed
names, binds only those settings, and always deletes the temporary file,
including on decryption or validation failure. Secret tasks retain `no_log` and
secret file writes suppress diffs.

This uses an ordinary JSON-compatible ciphertext string. It does not depend on
Controller accepting `!vault` launch tags or decrypting JSON Vault-marker
dictionaries; those earlier scalar transport proposals were unsupported.

## Metadata ownership and runtime proof

`aiops_instances[hostvars[aap_instance_key].vm_resource.vm_name]` in the encrypted private CaC owns the
verified testserver, TRA and Zabbix metadata, plus the existing
base guest Machine credential reference. Application inventory derives from
that private data, without requiring nested AIOps fields on the AAP host.
Generic source-inventory guest rows retain their `vm_resource` ownership facts
for existing decommissioning; no additional cleanup job or lookup store exists.

MCP runtime setup reads `demo_mcp_subscription` only from the selected encrypted
runtime namespace. It uses the pinned certified RHEL registration role's
subscription task entries to prepare the required repositories without forcing
registration or managing Insights. Normal RHEL package signature verification
and trusted HTTPS remain enabled; no offline RPM/image bundles are transferred.
See the [MCP prerequisites](10-mcp-deployment.md#target-side-image-builds).

An approved reference Zabbix token is an initial clone-authentication candidate,
not proof that it exists in the saved appliance. Authentication must succeed on
the verified new clone while inherited monitoring/delivery remains stopped.
Failed authentication leaves that server stopped for diagnosis. Read-only
checks, healthy HTTPS and a successful CaC import do not prove the complete
monitoring/remediation loop. EDA activation, delivery release and deliberate
outage tests require their existing reviewed readiness steps.
