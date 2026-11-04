# Deploy the versioned Zabbix monitoring VM

`playbooks/deploy_zabbix_demo.yml` is the **Deploy Zabbix Demo** Job Template.
It creates a monitoring VM from the already verified saved image on the selected
recovery hypervisor, configures that clone, and publishes its protected frontend.
The AIOps private CaC capture installs the template and its protected environment
selection. This application job is separate from importing AAP configuration.

The existing AAP reservation determines every name. For allocation 7:

| Resource | Name or path |
|---|---|
| AAP public hostname | `aap27.v07.example.invalid` |
| Demo website | `redhat.v07.example.invalid` |
| Zabbix public hostname | `zabbix.v07.example.invalid` |
| Monitoring libvirt domain | `zabbix-v07` |
| New monitoring disk | `/opt/vms/zabbix-v07.disk.qcow2` |
| nginx virtual host | `/etc/nginx/conf.d/demo-zabbix-v07.conf` |
| Dedicated nginx Basic-auth file | `/etc/nginx/demo-zabbix-v07.htpasswd` |
| Certificate lineage | `zabbix.v07.example.invalid` |

There is no independent counter or alternate public alias. The saved source
image is retained unchanged. Its active state is converted into a standalone
clone; historical internal image snapshots are not copied into the new disk.

## Launch inputs

Keep the template's saved hypervisor Machine credential and AIOps runtime Vault
credential. The encrypted CaC inventory derives `demo_zabbix_deployment` from the
selected AAP instance and its hypervisor. It includes the same allocation fields
as `demo_website_deployment`, plus:

- `source_image`: exact saved path and SHA-256 checksum;
- `vm_network`: the existing isolated libvirt network;
- `guest_user`: the new guest's explicit non-root management account;
- `guest_authorized_public_key`: the public counterpart of the attached Machine
  key, with its optional comment removed;
- `isolation_policy`: the complete current approved recovery policy, including
  any separately approved clients. The playbook validates it and never changes it.

The playbook declares these required structured inputs. The existing private
repository's [whole-file runtime Vault](11-protected-runtime-settings.md)
supplies them through saved ciphertext and the already attached Vault
credential; importing the CaC definitions launches no application:

| Variable | Content |
|---|---|
| `demo_zabbix_clone_api_token` | Existing write-capable token valid in this saved monitoring image; required explicitly. |
| `demo_zabbix_dns_api_token` | The existing DNS provider credential. |
| `demo_zabbix_basic_auth_file` | Reviewed htpasswd contents for the new public frontend. |
| `demo_zabbix_event_stream` | Mapping of `url`, `username`, `password` for the **new target AAP** Event Stream. |

The deployment playbook does not load the production runtime `myvars` file.
A missing clone credential fails; it cannot silently use the production token.
Native `include_vars` decrypts the whole-file ciphertext and validates its
selected instance before binding inputs. Controller does not support inline Vault launch scalars
or JSON Vault-marker mappings, and no custom decoder is added. Do not save
individual plaintext secrets in extra variables or defaults.
The Event Stream URL must use the selected `aap27.vNN` origin and an actual
external Event Stream UUID returned after AIOps CaC import. Credentials stay
out of event payloads, diagnostics, Git plaintext and returned artifacts.

`demo_zabbix_enable_delivery` is an explicit Boolean, default `false`. The
playbook creates the target-only problem/recovery action but leaves it disabled
until delivery is deliberately enabled. It never enables an AAP EDA activation,
sends a test outage, or arms the audience button. Prepare the healthy versioned
website before enabling monitoring delivery.

## Clone preparation and runtime access

The single target's SSH public keys, machine ID and current isolation policy are
checked before any clone write. Disk/name collisions are preserved for review.
Before its first boot, the new image receives a fresh machine identity and fresh
SSH host keys, DHCP configuration and the public management key. The monitoring
server and inherited monitoring agents are masked offline. The database and web
frontend can therefore start without running inherited polling or alert actions.
No packages or collections are installed by this playbook.

Native libvirt domain description metadata retains the allocation, source hash,
hypervisor identity and generated guest public keys. A rerun validates the actual
domain UUID, disk and network and reuses those keys. Management always traverses
the pinned hypervisor with both SSH host-key checks enabled. DHCP must identify
the actual selected domain MAC; another lease cannot select another guest.

While the cloned server is stopped, API configuration disables inherited hosts,
actions, media types, discovery and web scenarios, and neutralizes copied scripts.
Only the selected version's website host, HTTP-status item and trigger are then
configured. The check uses the versioned website HTTPS name, verifies its chain
and hostname, and refuses redirects. The selected service names resolve inside
the guest to the verified hypervisor bridge, avoiding a NAT hairpin or firewall
exception. Public DNS continues to point to that hypervisor's public IPv4.
The guest's own versioned name is first in its managed proxy-address aliases,
so `hostname --fqdn` retains the guest identity when multiple service names share
one bridge address. A retry repairs only the exact older alias line before
checking that hostname; unrelated hosts-file entries are preserved.

A dedicated target-only native Zabbix webhook media and action deliver problem
and recovery events to the selected AAP Event Stream, using its Basic credentials.
The copied appliance administrator remains the recipient; no new user, role or
credential type is introduced. Existing copied outbound integrations remain
quarantined. Only after all configuration succeeds is the monitoring server
unmasked and started. Failed authentication or quarantine leaves it stopped.

## DNS, HTTPS and the additional nginx authentication gate

The frontend uses exact-name DNS queries and refuses conflicting A or AAAA
records. It reuses the separately approved certificate account and existing base
packages. Its managed nginx file supports the ACME webroot challenge, trusted
public HTTPS and the source deployment's additional Basic-auth gate. nginx uses
`auth_basic_user_file`; Apache `.htaccess` files are not interpreted by nginx.
The new hash file and certificate are specific to this deployment version.
nginx is validated before reload, and its previous managed vhost is restored on
a failed publication. No production virtual host is edited.

Basic authentication covers the **entire public Zabbix frontend**, including
its public API path. No public API exception is added. Configuration API calls
use the guest loopback HTTP endpoint over its verified SSH connection. Existing
website jobs running on the pinned hypervisor may use that new guest's private
HTTP API with the explicit clone bearer. This internal transport is distinct
from the public, certificate-verified HTTPS frontend.

## Results and validation

The protected `demo_zabbix_instance` job artifact first retains ownership before
startup, then the DHCP route before API configuration. Later failures therefore
preserve useful cleanup evidence. After success it returns the actual guest UUID,
disk, MAC, IP/address, network, bridge, machine ID, public SSH keys, source hash
and owned nginx/TLS paths, plus the
verified private API URL and new website item/trigger IDs. It never returns the
API token. Early ownership is marked unverified until the fresh guest machine
identity has been authenticated through its pinned SSH key. The deployment
coordinator persists verified provenance in the existing source inventory's
`vm_resource` and the owning use case's encrypted configuration, so decommissioning
can prove ownership. AutoDeploy allocation retains only primary AAP ownership. Website
monitoring requires the target-local URL/token/IDs as `demo_website_zabbix`
in the same instance's private runtime settings.

Offline checks exercise exact naming and ownership, refusal of foreign disks or
networks, target-only Event Stream selection and credential-free webhook payloads.
A real local Ansible/API fixture proves that failed quarantine does not start the
server and that a successful run disables inherited integrations before starting
only target monitoring. Reruns preserve the created object identities. Both HTTP
challenge and HTTPS/Basic-auth templates also pass the target hypervisor's actual
nginx syntax check using temporary fixture files, without a reload.

Run the focused local tests with existing dependencies:

```sh
python3.12 -m unittest discover -s tests -p test_versioned_zabbix.py -v
ansible-playbook --syntax-check -i localhost, playbooks/deploy_zabbix_demo.yml
```

These checks establish implementation behavior. Actual VM boot, clone API access,
DNS propagation, certificate issuance and public authentication require a
separately observed successful deployment job; offline tests do not establish them.
