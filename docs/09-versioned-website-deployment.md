# Deploy the website beside a selected AAP instance

Use the existing **Enable Demo Website** Job Template after importing this
project's CaC into a freshly installed AAP. It runs the existing
`playbooks/demo_website.yml`; no additional dispatcher or application job is
needed. The configuration importer itself still launches no application.

## Identity and prerequisites

The AAP allocation determines both public names. For example, allocation 7
means `aap27.v07.example.invalid` and `redhat.v07.example.invalid`. Keep the
allocation's internal inventory key, such as `aap27-test-7`; do not allocate a
second number for the website. The source inventory entry needs
`aap_instance_number`, `ansible_fqdn` and `hypervisor_host`. The named hypervisor
also needs its own inventory entry containing `ansible_host`, `public_ipv4`,
`ansible_user`, `ansible_port`, `machine_id` and `host_keys`. The private CaC
capture derives the website's deployment dictionary from those selected entries.

The hypervisor must already have nginx, certbot, python3-certbot-nginx, git, an
approved ACME account, public HTTP/HTTPS reachability and the existing base
permissions for nginx proxying. The playbook checks package/account readiness;
it neither installs tools nor registers an account. Prepare the reviewed
`community.general` collection pin on the target PAH before synchronizing the
SCM Project. The existing supported execution image needs its DNS Python
dependency; use the base preparation process if missing.

The imported hypervisor Machine credential must contain the selected
hypervisor's authorized SSH key. Enable, Disable, Restore and Arm use the
existing runtime Vault credential. All website playbooks validate their target
and use strict host-key checking before remote actions; the live machine ID
must match the selected hypervisor. There is no installer-password discovery
or static production destination fallback.

## Protected post-import handoff

Using authenticated, certificate-verified HTTPS calls to the selected target:

1. Find the target's **Simulate Website Outage** Job Template by its exact name
   and project; require one matching result and `webhook_service: gitlab`.
2. Read that template's generated `webhook_key` through its webhook-key API.
   Preserve the key; this deployment does not rotate it.
3. Retain the following required input names for the existing **Enable Demo
   Website** template, stored in the selected instance's private runtime Vault:

| Variable | Value |
| --- | --- |
| `demo_website_fault_template_id` | The selected target's fault-template ID |
| `demo_website_webhook_key` | Its generated GitLab webhook key |
| `demo_website_dns_api_token` | The existing DNS provider authorization token |

Use the [whole-file runtime settings procedure](11-protected-runtime-settings.md)
to update the existing private repository and the existing Enable template's
saved ciphertext. Its already attached runtime Vault credential supplies native
decryption; no individual plaintext secret is entered at launch. Controller
rejects inline `!vault` launch values and does not decrypt JSON Vault-marker
mappings as ordinary variables; those approaches are not used. The CaC
definitions can be imported independently, with only saved ciphertext.
Missing application inputs stop the job before managed host, DNS or API writes.

Secret checks, DNS requests and nginx template writes keep protected logging
even at debug verbosity, and secret nginx configuration is root-readable only.
No custom decoder, credential type, store or unattended combined workflow is
implemented by these definitions. Do not print API responses or populated
configuration.

## What the job changes

The job refuses conflicting DNS A records and any AAAA record for the versioned
website. It creates only that exact A record when absent and waits for public
DNS to identify the selected hypervisor. Existing DNS records at another
address are not replaced. The matching AAP name must resolve to the same pinned
public IPv4 address without an alternate IPv6 route. It creates version-specific
content, nginx and delivery-cache paths without overwriting an unmanaged virtual host. The existing
target-side public content checkout is isolated under `/opt/demo-web-src-vNN`;
managed deployments require git to be preinstalled instead of installing it.

Certificate issuance uses the existing account and webroot challenges. Renewal
keeps the webroot method and validates/reloads nginx through a deploy hook.
The HTTPS site retains the arm-marker guard and nonce-based POST delivery
cache. Its only webhook destination is the matching public AAP FQDN, with TLS
verification and the system trust store enabled. A failed nginx/certificate
stage restores the previous version's virtual-host configuration; an already
created DNS record or certificate is retained for inspection and retry.

The existing lifecycle job deploys the page and verifies HTTP 200 over trusted
HTTPS using the real hostname and loopback routing. This exercises certificate
hostname validation without relying on a public-address hairpin. Separately
check trusted HTTPS from outside the hypervisor after the job finishes.

## Initial recovery state

The private capture explicitly sets these flags for the fresh target:

```yaml
demo_website_manage_infrastructure: true
demo_website_manage_monitoring: false
demo_website_manage_fail2ban: false
demo_website_arm_on_enable: false
```

The website serves healthy content, its button remains disarmed, production
Zabbix objects are not changed, and shared fail2ban configuration is untouched.
EDA activation definitions remain disabled. Do not press the panic endpoint or
run a fault/disable test during this initial deployment. Configure and verify
target-local monitoring and repair before deliberately enabling the complete
audience incident loop. Existing non-versioned production lifecycle behavior
retains its defaults.

## Verification

Run the allocation/DNS/nginx-template tests and the existing real-Ansible
hostname tests from the repository root:

```bash
python3.12 -m unittest discover -s tests -p test_versioned_website.py -v
ANSIBLE_LOCAL_TEMP=/tmp/aiops-hostname-local python3.12 -m unittest discover -s tests -p test_website_hostname.py -v
```

After the actual Enable job, inspect its terminal result, the exact DNS record,
trusted public HTTPS, nginx validation and the arm-marker's absence. Confirm
both EDA activation definitions remain disabled. A successful configuration
import or healthy website alone does not prove the monitoring/remediation loop.
