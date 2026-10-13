# Recreate the audience website demo

This guide records the implementation and findings from 2026-10-13. Actual
addresses, API tokens, webhook keys, and account details belong in encrypted
configuration or the platform's credential stores. Replace example domains,
paths, and IDs for your deployment.

## 1. What happens in one round

1. Enable deploys the shell and content, starts monitoring, and arms the button.
2. Every browser polls `/content.html` and `/armed` every two seconds.
3. `/armed` publishes a random nonce, shared by everyone in that round.
4. The browser POSTs `{"nonce":"<current-nonce>"}` to `/api/panic`.
5. nginx forwards one accepted delivery for that body to the fault template.
6. The fault job removes `.armed` and moves `content.html` aside. nginx really
   returns 404; already-open browsers display the failure automatically.
   The outage view says **OMG, PANIC, it is KAPUTT!!!** in large letters and
   keeps the **Outage detected at …** timestamp.
7. Zabbix samples the 404 and sends a problem event to the existing EDA stream.
8. EDA launches **Restore Website Content**, which restores and verifies HTTP 200.
9. Zabbix samples 200 and sends a recovery event to the same stream.
10. EDA launches **Arm Demo Button**, which verifies the content and publishes
    a fresh nonce. Open browsers enable their button again without refreshing.

Content recovery and rearming are distinct steps. Rearming immediately in the
repair job would allow a second press before Zabbix closed the first problem;
that second outage could then produce no new problem event. Waiting for the
Zabbix recovery event avoids this race.

## 2. Static nginx host setup

The demo is served directly by nginx on the hypervisor. Its dedicated vhost,
certificate, and AAP webhook secret remain host-owned configuration. The
lifecycle jobs manage content and a dedicated rate-limit include.

Use the [generic vhost example](../assets/nginx/demo-website-vhost.conf.example)
as a deployment reference. Substitute your values in protected host
configuration, provision the certificate and cache includes, and validate
before loading it. The example uses verified upstream TLS with a matching
controller hostname; the live cache change preserved the existing upstream
TLS settings. It is a reference, not a replacement for other host vhosts.

Configure a hostname-based HTTPS vhost with:

- the web root used by `demo_website_root`;
- a valid certificate for that hostname, using webroot renewal so renewal does
  not rewrite nginx configuration;
- `/armed` as an alias to `.armed`, with a `Cache-Control: no-store` response;
- an exact `/api/panic` location that accepts POST only, returns 423 when the
  arm marker is missing, and proxies the request body unchanged to the
  controller's GitLab webhook URL for **Simulate Website Outage**;
- the private GitLab webhook-token header injected by nginx, with the event
  header `X-Gitlab-Event: Push Hook` and JSON content type;
- the existing TLS and access settings for this deployment, preserved while
  changing the demo location.

Obtain the webhook URL and key from the fault template after enabling its
GitLab webhook. Keep the key on the host; it must never reach the browser or
appear in a plaintext repository export. Do not configure a constant
`proxy_set_body`: every round needs a distinct body.

### Rate-limit lifecycle

Keep the existing exemption map and `redhat_panic` zone definition in the
vhost. Replace the button's inline enforcement directives with:

```nginx
include /etc/nginx/demo-website-rate-limit.conf;
```

Create the include before the first lifecycle job. Disabled contents are:

```nginx
limit_req zone=redhat_panic burst=1 nodelay;
limit_req_status 429;
```

Enable empties enforcement for the entire demo site. Page loads and polling
already have no limits; other virtual hosts retain their existing limits.
Disable restores the original button limit. This matters when conference
participants share a single NAT address.

The jobs also stop the configured demo fail2ban jail while enabled and restore
it when disabled. Use `fail2ban-client reload` to restore a stopped jail:
`start <jail>` cannot recreate a jail removed by `stop`. Check the jail with
root privileges; a socket-permission error is not evidence that it is stopped.

### Concurrent presses: one upstream delivery

AAP's sequential webhook deduplication did not prevent simultaneous identical
requests from creating multiple jobs in the live ten-press test. The fault
playbook's idempotent move prevented some repeated damage, but queued duplicate
jobs could run after recovery. Deduplicate delivery at nginx as well.

Install the versioned snippets:

- [`demo-website-panic-cache-http.conf`](../assets/nginx/demo-website-panic-cache-http.conf)
  in the nginx `http` context, such as its `conf.d/` directory;
- [`demo-website-panic-cache-location.conf`](../assets/nginx/demo-website-panic-cache-location.conf)
  at `/etc/nginx/demo-website-panic-cache-location.conf`.

Create `/var/cache/nginx/demo-website-panic`, owned by the nginx worker account,
with mode 0750 and the appropriate SELinux cache context. Add this inside the
existing exact panic location:

```nginx
include /etc/nginx/demo-website-panic-cache-location.conf;
```

Preserve the arm-marker guard and private forwarding headers. The cache key
includes the POST body, and the cache lock shares a successful HTTP 202 response
across identical simultaneous presses. Only accepted responses are cached.
The next arm nonce makes a different key, so the next round reaches AAP.
This is independent of client IP and request-rate enforcement. Upstream
timeouts are shorter than the cache lock timeout to avoid normal requests
escaping the lock before the first delivery completes.

See the official [nginx proxy-cache reference](https://nginx.org/en/docs/http/ngx_http_proxy_module.html#proxy_cache_lock)
for lock and POST caching behavior. Back up private configuration with protected
permissions, run `nginx -t`, reload, and verify new workers actually appear.
The live installation used a root-only backup and rollback on validation or
reload failure.

## 3. Allow monitoring through the hypervisor's VM-facing firewall zone

The monitoring VM reaches the public hostname through the VM bridge, so its
traffic is evaluated by the hypervisor's VM-facing zone rather than its public
zone. Public HTTPS access alone is insufficient.

Add a static rich rule restricted to the monitoring VM's source address and
TCP 443, in both runtime and permanent configuration. For example, after
replacing placeholders:

```bash
firewall-cmd --zone=<vm-facing-zone> --add-rich-rule='rule family="ipv4" source address="<monitoring-ip>/32" port port="443" protocol="tcp" accept'
firewall-cmd --permanent --zone=<vm-facing-zone> --add-rich-rule='rule family="ipv4" source address="<monitoring-ip>/32" port port="443" protocol="tcp" accept'
```

Query both copies of the rule, then test HTTPS from the monitoring VM. Use the
real hostname for TLS SNI; an IP URL with only a Host header can fail before
nginx processes HTTP. A temporary firewall job template was removed: this is
static host setup, not a step in the demo lifecycle.

On the Rocky Linux monitoring appliance, `host`, `firewall-cmd`, and `nft` were
unavailable. Existing `iptables -S OUTPUT` and `ip route get <destination-ip>`
showed permitted outbound traffic and the route through the hypervisor. The
connection refusal was traced to the hypervisor zone, not fixed by installing
diagnostic packages on the appliance.

## 4. Create the dedicated Zabbix HTTP agent item and trigger

Create a dedicated website host in a demo group, without an agent interface.
Set its visible name to the website hostname, for example `demo.example.com`.
The existing live host initially appeared as **Demo Website** and was renamed
to its website hostname for easier discovery; its technical name and monitoring
identity were retained. There was no duplicate host or additional agent.
Add this item:

| Setting | Value |
| --- | --- |
| Name | `Demo website content HTTP status` |
| Type | HTTP agent (`19` in the API) |
| Key | `demo.website.http_status` |
| URL | `https://demo.example.com/content.html` |
| Method | GET |
| Information type | Numeric unsigned (`3`) |
| Update interval | `4s` |
| Timeout | `10s` |
| Retrieve mode | Headers (`1`) |
| Output format | Raw (`0`) |
| Required status codes | **Empty** |
| Follow redirects | Enabled |
| Verify peer and host | Enabled |
| History / trends | `31d` / `365d` |

Add regular-expression preprocessing to extract the status code:

```text
Pattern: ^HTTP/\S+[ \t]+([0-9]{3})
Output:  \1
```

Leaving required status codes at the default `200` makes a 404 sample
unsupported instead of recording 404, so the intended trigger cannot fire.
The initial rehearsal used 20 seconds at the user's request. The user later
requested four seconds for faster detection and recovery confirmation; the
live item and this recreation setting now use `4s`.

Create a single-problem trigger named **Demo website content unavailable**,
severity High, with normal expression-based recovery:

```text
last(/<website-host>/demo.website.http_status)<>200
```

Record the generated item and trigger IDs in encrypted `myvars`. Confirm a
healthy sample is 200 before enabling the trigger.

In the UI, edit the check under **Data collection → Hosts → Items**. It is an
HTTP agent item, not a web scenario. View samples under **Monitoring → Latest
data** and the alert under **Monitoring → Problems**. Disabled items can retain
their last stored value; inspect their enabled/disabled status too.

### Show the live green → red → green cycle

For the host row, use **Monitoring → Hosts**, clear stale name/group filters,
and find the website's visible hostname. The HTTP check contributes to its
**Problems** column. Agent availability badges such as ZBX describe agent
interfaces; this HTTP-only host has no agent interface.

The trigger configuration list shows a snapshot. In **Monitoring → Problems**,
select **Show: Recent problems** to retain green recovery records. A short
outage can be repaired between slow frontend refreshes: observed follow-up
problems lasted twelve seconds, while the presenter's refresh was thirty
seconds. A red state can therefore be missed even though Zabbix detected it.
For example, the EDA activation log explicitly recorded launching repair job
1717, and that job succeeded; monitoring samples and events confirmed the
404 → problem → 200 → recovery sequence.

Use the native **Monitoring → Maps → Big Bad Button - Live Website** view for
a persistent status indicator. The live setup is private to the presenter:

1. Upload the three PNGs from [`assets/zabbix/`](../assets/zabbix/) in
   **Administration → General → Images**, as icons named **BBB Website
   Healthy**, **BBB Website Problem**, and **BBB Website Disabled**.
2. Create a 900 × 480 map named **Big Bad Button - Live Website**. Make the
   presenter its owner and keep it private.
3. Add one **Trigger** element linked to **Demo website content unavailable**.
   Use the green icon for the default/OK state, red for the problem state, and
   grey for the disabled state. Disable automatic icon mapping, highlighting,
   and recent-change blinking; keep the current color continuously visible.
4. Place the element at x=322, y=100. Add the **WEBSITE HEALTH** title and the
   green/red/grey legend. The portable
   [`map.create` request template](../assets/zabbix/website-status-map.json.j2)
   records the exact element and shape configuration. Substitute the generated
   icon IDs and the dedicated trigger ID; keep authentication separate.
5. Under **User settings → Profile**, set **Refresh** to `4s` and update. This
   is a frontend setting, separate from the item's sampling interval. The live
   change affected the presenter account's display refresh, not permissions.
6. Open the map as a standalone view, press the audience button, and observe
   green → red → green. Disable monitoring produces the grey state.

The map and icon bindings, private ownership, and four-second profile refresh
were read back and verified through the API. Its native screen renderer uses
the profile refresh interval. Standard dashboard widgets offer a ten-second
minimum refresh, so embedding the map in a dashboard widget can again miss a
short outage. Use the standalone map for the conference presentation.
See [map element icons](https://www.zabbix.com/documentation/7.4/en/manual/api/reference/map/object#map-element),
[profile refresh](https://www.zabbix.com/documentation/7.4/en/manual/web_interface/user_profile),
and [dashboard widget refresh choices](https://www.zabbix.com/documentation/7.4/en/manual/api/reference/dashboard/widget_fields/item_value).

Bundled SVGs are the native geometric sources; the PNGs are used by Zabbix.
To recreate them without installing dependencies:

```bash
python3 src/generate_status_icons.py
```

## 5. Preserve and extend the Zabbix media integration

Use the existing **Event-Driven Ansible** media type and the existing AAP Event
Stream. The complete modifications are in
[integration guide section 7](06-eda-zabbix-integration.md#update-media-type-parameters-for-event-streams):

1. Set `endpoint` to the gateway Event Stream path; user media **Send to** holds
   only the base URL.
2. Retain the added `eda_username` and `eda_password` parameters and Basic Auth
   header in `sendMessage`.
3. Extend the stock event-value guard to accept both problem `1` and recovery
   `0`, retaining the trigger-source restriction and existing payload handling.

The stock problem-only guard initially rejected recovery with “Only
trigger-based events of problem are supported.” Changing only that validation
preserved the previous Event Stream patch. Verify delivery using Zabbix alert
status: sent with no error, rather than merely finding the alert record.
Alerts that exhausted their retries before the change require a fresh cycle
for validation. Reimporting a stock media type can overwrite these changes.

Keep the existing problem action. Add a separate action filtered by the
website's trigger ID with a recovery operation sending a message to the same
Zabbix user through this media type. A recovery-only action was verified to
deliver successfully; it needs no extra duplicate problem operation.

Zabbix MCP access in this deployment is read-only. Setup writes use the
authenticated Zabbix JSON-RPC API. The appliance reported version 7.4.12.
The API token worked; a UI filter initially hid it from the user. No token was
rotated during this work. The API and the user confirmed three active tokens
after removing the UI filter.

## 6. Vault and AAP controller setup

Create `myvars` in this repository's root as a fully Ansible Vault-encrypted
file containing:

```yaml
demo_zabbix_api_url: "http://monitoring.example.com/api_jsonrpc.php"
demo_zabbix_api_token: "<api-token>"
demo_zabbix_item_id: "<created-item-id>"
demo_zabbix_trigger_id: "<created-trigger-id>"
```

Use the existing Vault password convention and attach the existing Vault
credential to the two lifecycle templates. This repo's standalone AAP checkout
cannot load the shared `myvars` from its parent repository. The project-specific
file contains only monitoring settings, not a copy of every shared secret.
Do not commit a decrypted file. A custom credential type was considered, then
replaced with this Vault approach at the user's request; none was created.

The local Vault password file was verified against the shared Vault and used
to encrypt the project file without printing either secret. A local Ansible
temporary-directory error occurred before decryption; using a private writable
temporary directory resolved it. Use the installed RPM Ansible binaries.

Create or reuse these normal job templates in the same organization:

| Template | Playbook | Fixed variables / credentials |
| --- | --- | --- |
| Enable Demo Website | `playbooks/demo_website.yml` | `demo_website_state: enabled`; machine and Vault credentials |
| Disable Demo Website | `playbooks/demo_website.yml` | `demo_website_state: disabled`; machine and Vault credentials |
| Simulate Website Outage | `playbooks/inject_website_fault.yml` | Description: `Inject Website Fault`; machine credential; GitLab webhook enabled |
| Restore Website Content | `playbooks/restore_website_content.yml` | Machine credential |
| Arm Demo Button | `playbooks/arm_demo_button.yml` | Machine credential |

The outage template was renamed from **Inject Website Fault** to **Simulate
Website Outage**, with **Inject Website Fault** as its description. Its existing
ID, webhook settings, and playbook path were retained. The nginx webhook URL
targets the template by ID; the EDA rulebook references only the repair and
arm template names. Neither needs an update for this rename.

Use the inventory host serving nginx, with the same explicit host limit and
machine credential on all five templates. Supply deployment-specific site
settings through inventory or encrypted configuration. The supplied content
checks use the deployed demo's hostname; adapt their `curl --resolve` hostname
and URL together for another deployment. Loopback resolution avoids relying
on NAT hairpin access from the web server itself.

Sync the project before assigning a newly added playbook to a template:
controller validates against its last synced file list. Verify sync completion
and revision. Agent-side Git operations use SSH; AAP's SCM URL remains HTTPS.
Existing credential attachment and project sync used controller REST where the
MCP lacked the required operation; job launches and results used AAP MCP.

Disable disarms first, disables the trigger and item, then puts the page away
and restores rate limiting and fail2ban. Enable disarms during transition,
pauses the trigger, deploys and verifies content, resumes the item, waits for
a **fresh** 200 sample, enables the trigger, and finally arms. API calls run
inside the execution environment with `no_log: true`. Both paths were tested
through AAP, confirming the execution environment can reach the API and
decrypt the Vault file.

## 7. Import and activate the website rulebook

Commit and push [`demo-website-restore.yml`](../extensions/eda/rulebooks/demo-website-restore.yml),
sync the EDA project, and verify the imported rulebook contains both rules.
Create its activation using the existing decision environment, controller
credential, organization, and Event Stream. Map the single source to the same
stream already used by Zabbix. The webhook source declaration is a placeholder
replaced by AAP's Event Stream mapping at runtime.

The two rules match the fixed website trigger name and numeric event values:

- `1`: **Restore Website Content**;
- `0`: **Arm Demo Button**.

Quoted values (`"1"` and `"0"`) caused live EDA errors comparing `int` with
`str`; changing to numeric comparisons fixed them. Activation summary counters
were insufficient to diagnose this failure: the event had arrived, and the
activation-instance logs contained the actual evaluation error. After changing
a rulebook, sync its project and restart its activation, then check the new
instance is running and has the current rules. Inspect launch logs and actual
controller job outcomes.

## 8. Validation and observed results

Local checks use existing binaries and no installed dependencies:

```bash
ansible-playbook --syntax-check --vault-password-file /path/to/vault-password -i localhost, playbooks/demo_website.yml
node tests/browser_polling.test.js
git diff --check
```

The Node harness runs the actual page script with simulated DOM and HTTP
responses. It verifies two-second polling, failure and recovery transitions,
waiting for server rearming, fresh nonces across rounds, and a benign message
for HTTP 423. It checks behavior, not browser rendering. The user also observed
the live page switching to failure without refreshing.

Stress requests used SSH and loopback hostname resolution on the web server;
the Zabbix check used the actual monitoring VM's HTTPS route. This verifies
webhook concurrency and the monitoring chain rather than Wi-Fi throughput.

| Live rehearsal | Result |
| --- | --- |
| nginx body forwarding, jobs 1486 / 1488 | Distinct JSON bodies returned 202 and both fault jobs completed |
| Rate-limit lifecycle, jobs 1494 / 1496 / 1498 | Disable → Enable → Disable passed; initial malformed include was rolled back and corrected |
| Initial Zabbix → EDA repair, jobs 1504 / 1506 | Actual 200 → 404 → 200 and successful repair |
| Automatic rounds 1537 / 1539 / 1541 and 1543 / 1545 / 1547 | Fault → repair → recovery-driven rearm passed twice |
| Monitoring lifecycle, jobs 1550 / 1552 | Disabled item/trigger and restored healthy enabled state verified |
| First simultaneous ten-press test | Nine fault jobs were created; three completed and six queued duplicates were cancelled; repair/rearm completed |
| nginx cache-lock rounds 1568 / 1570 / 1572 and 1574 / 1576 / 1578 | Ten HTTP 202 responses per round; exactly one fault, one repair, and one rearm job per round |
| Final Disable 1581 → Enable 1583 | Both succeeded with the deployed browser update and Vault-backed monitoring lifecycle |
| Final rounds 1585 / 1587 / 1589 and 1591 / 1593 / 1595 | Ten concurrent 202 responses in each round; one fault, repair, and automatic rearm per round; fresh nonce in the second round; late presses returned 423 |
| Final Disable 1597 | Successful; placeholder 200, content/arm 404, panic 423, marker absent, item/trigger disabled, rate limit restored, jail running |
| Later panic-message update, Enable 1616 | Successfully deployed the larger OMG message and retained the timestamp; no repeat rehearsal, as requested |

The complete final sequence passed and the demo was left disabled as requested.
Zabbix alerts 77–80 were sent with no errors for the two final problem/recovery
pairs. Activation-instance logs confirmed EDA launched jobs 1587, 1589, 1593,
and 1595; all completed successfully. Final monitoring status was disabled and
the trigger was healthy. The last stored 200 remains visible while the item
is disabled; it does not mean the intentionally removed content is being
sampled.

To rehearse again, run **Enable Demo Website** and wait for success, then open
the demo URL. Refresh a previously loaded disabled placeholder once. Keep the
enabled tab open for subsequent rounds: press, observe failure, wait for repair
and the button to rearm, and press again. The two-second browser polls show
state changes automatically; the four-second Zabbix sampling interval and
controller job queue add their own delay. End with **Disable Demo Website**
and verify it succeeds. Manual monitoring switches or a separate manual arm
job are no longer required during normal rounds.

## 9. Operational lessons and deferred work

- `nginx -t` and a successful reload command do not prove the running master
  accepted a change. A live zone-key change was rejected by the master while
  the reload command succeeded; a restart was required. Prefer a new zone name
  for changed keys, and inspect worker replacement and the error log.
- The missing panic file-test guard was restored. A disarmed endpoint returned
  423. A late concurrent press now gets a benign browser message rather than
  an injection-failed message.
- The panic endpoint expects JSON containing the nonce. A test posting only
  the raw nonce returned 400; the correct browser-format JSON returned 202.
- Repair verifies content and can redeploy it when the aside copy is missing.
  Fault injection removes the marker before moving content; repeated moves
  safely do nothing when content is already absent.
- The disabled placeholder is intentionally inert. After Enable, refresh a
  previously loaded placeholder once. Keep the enabled tab open for repeated
  automatic failure/recovery rounds.
- Raw-content CDN caching can delay visible Git changes; verify AAP's synced
  commit rather than assuming an unpinned raw URL is current.
- Rotate integration tokens later; review and label the job-template catalog
  later; clean up the shared/project-specific Vault structure later.
- A diagnostic configuration dump exposed the private webhook header in tool
  output earlier in the session. Its value is omitted from this guide; rotate
  it together with its nginx setting during the planned token maintenance.
- Status UI enhancements, full nginx configuration management, and the parent
  repo's stale submodule pointer remain deferred after the conference.

These follow-ups are tracked in [the design backlog](todo/demo-design.md).
