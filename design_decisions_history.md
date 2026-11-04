# Design decisions history

## Load per-instance application settings through native Vault — 2026-11-03

Implementation `ba099ef` implements the owner's approved whole-file settings
delivery in the existing private AIOps repository. The existing application
templates receive ordinary ciphertext strings. Native copy preserves that
ciphertext in a private execution-environment file; native `include_vars`
uses the already attached runtime Vault credential. A fixed schema checks
the selected instance and reviewed setting names before binding values, and
an `always` section removes the file after success or failure. Explicit
literal tags keep credential contents from becoming Jinja templates.

No custom decryption adapter, credential type, repository, service, dispatcher
or additional Job Template is introduced. A private maintenance command keeps
the existing CaC capture's opaque ciphertext equal to its encrypted runtime
file. Target-generated webhook and Event Stream settings still require the
initial CaC import; missing values stop dependent jobs before managed writes.
This replaces the earlier unsupported scalar-launch proposals documented above.

The private AIOps capture now owns selected guest and offline artifact data
instead of nested application settings on the AAP inventory host. Generic
source guest inventory ownership remains available for existing decommissioning.
The instance naming scheme is deliberately unchanged pending the user's
separate instruction to wait until the current import finishes.

Offline runtime preparation also imports only the reviewed, installed
release-owned vendor signing key after file hash and fingerprint checks. This
addresses an empty RPM key database in the upstream guest image while retaining
mandatory RPM signatures and package GPG checks; no external key is fetched.

Seven real-Ansible/schema runtime tests, two private maintenance checks and
eight MCP regressions pass. The actual private ciphertext loads in both Ansible
modes using ordinary JSON extra variables, with no secret output and cleanup
verified. Four application playbooks pass syntax; nineteen files pass scoped
production lint. Both-mode capture/dependency checks pass with all central
application fields removed from their fixture. No application, fault test or
activation is launched by this publication; a reference token remains only a
candidate until it authenticates on the verified new monitoring clone.

## Prepare target-local monitoring and the two requested MCP jobs — 2026-11-03

Implementation `fa73fef` adds the separately requested Zabbix deployment and
Linux/Zabbix MCP playbooks. All components reuse the selected AAP allocation;
verified guest artifacts and live machine identities prevent a production
destination fallback. Zabbix clones the saved image without altering it,
quarantines inherited integrations before starting monitoring, and retains
trusted public HTTPS with Basic authentication. Delivery is disabled by default.

Both MCP servers preserve their existing on-demand Podman/stdio transports on
the new TRA. They accept only verified local image archives and signed offline
runtime RPMs, use the existing guest account and direct guest-bridge SSH, and
perform read-only protocol checks. Linux MCP generates a private key on TRA
and installs only its public half on the new testserver. Zabbix MCP requires
the matching new private API and an explicit token. No public MCP listener,
Claude Code installation, model invocation or EDA activation is added. The
platform's separate private native MCP endpoint matches production; the owner
explicitly excluded public MCP exposure.

Website and frontend checks now respect the permitted DNS resolver and pinned
hypervisor route. Managed website monitoring requires explicit target-local
inputs instead of production defaults. Existing production lifecycle behavior
is preserved.

The runtime secret-input method remains an owner decision. Earlier proposed
inline Vault launch scalars were rejected by Controller, while JSON Vault
markers were accepted as ordinary dictionaries rather than decrypted values.
The documentation corrects that proposal. No replacement decoder, credential
type, store or input mechanism is implemented. Definitions can be imported
independently; missing required inputs stop secret-dependent jobs before
managed writes, and their saved defaults contain no secrets.

Twelve website tests, nine Zabbix tests and eight MCP tests pass. Six playbooks
pass syntax and twenty-one files pass production lint. The encrypted capture
renders against actual selected inventory data in both modes, and its ten
template references resolve against the new target's existing base credentials.
Publication launches no application, fault test or activation; actual runtime
proof remains open pending inputs and offline artifacts.

## Preserve the target-side content checkout across versioned deployment — 2026-11-03

Implementation `cf111b2` integrates the existing upstream content-checkout
behavior preserved by merge `d13f3e2`. The staged checkout is isolated per
allocation alongside its content and nginx paths. Managed recovery deployments
require the existing git package rather than installing it; legacy lifecycle
behavior is retained. The matching public AAP name is also checked against the
selected hypervisor's public IPv4 before its webhook is configured. All twelve
website tests, the browser lifecycle test and nine-file production lint pass
after integration. No live application job is launched by publication.

## Deploy the versioned website on its selected hypervisor — 2026-11-03

Implementation `73d6b08` extends the existing Enable playbook rather than
introducing another dispatcher or Job Template. The selected AAP allocation
determines both AAP and website public names. Strict hypervisor SSH pins and
machine identity are checked before remote changes. Per-version nginx, content
and cache paths allow separate deployments without overwriting unrelated sites.
DNS changes refuse conflicting addresses or IPv6 routes. Certificates use an
existing approved account, webroot renewal and trusted HTTPS; the nginx webhook
proxy also verifies the matching public AAP certificate.

The owner approved an initial configuration/website scope with monitoring,
shared fail2ban changes and button arming disabled until target-local monitoring
and repair are ready. EDA activation definitions remain disabled. Existing
production lifecycle defaults are retained. DNS and generated target webhook
inputs use a protected post-import launch handoff with the existing runtime
Vault, rather than a new credential type or store. An unattended combined
workflow is not implemented or claimed.

Nine focused tests cover identity/allocation rejection, DNS conflicts, nginx
rendering and the actual Ansible target checks; the three existing real-Ansible
hostname tests and browser lifecycle test pass. Nine-file production lint and
syntax pass. The actual encrypted companion capture renders and validates for
three allocation widths in both templating modes. Live deployment to the new
selected instance remains a separate verification step.

Historical entries below are reconstructed from the available Git history.
Reasons are documented in the cited commit messages, unless explicitly marked
as inference. History before the repository split is unavailable here and has
not been reconstructed. No environment credentials or addresses are recorded.

| Commit | Change and reason |
|---|---|
| `36ec974` | Established the clean, split repository for the monitoring → EDA → agent → AAP demo. Earlier history was retained in a private archive; the reasons for individual earlier decisions are unknown here. |
| `ce4eced` | Moved environment-specific configuration into inventory and sanitized documentation, so reusable content no longer embeds deployment details. |
| `00efe2c` | Added an audience button and a shell that polls separate page content. Moving that content produces a real outage while every open browser can observe recovery. |
| `05e0a12` | Added the corporate mockup, placeholder, and shared enable/disable playbook. Disabling keeps the URL usable instead of making the site appear broken between demos. |
| `8a48d73` | Removed external webfonts to avoid venue-network stalls. Also added a DNS publication playbook with an allowlist. |
| `8c6121e`, `dddbe6f`, `705c818` | Refined the button label and heading size/wrapping so the presentation remains readable across laptop and phone widths. |
| `b5cba5b` | Aligned fault injection, restoration, and lifecycle automation with the actual nginx host. Restoration also redeploys missing content when an aside copy is unavailable, and verifies HTTP recovery. |
| `89b3b4d` | Removed the generic DNS publication playbook at the user's request; it had no deployed template. |
| `67558a0` | Documented the need to separate fault injection from the remediation catalog. Catalog separation was deferred so the live demo could retain an obvious audience-facing template name. |
| `a8d6155` | Stopped the demo-specific fail2ban jail while enabled and restored it on disable, avoiding a room-wide ban when participants share an address. |
| `e4f914e` | Fixed jail restoration to use reload, since stopping removes the jail. Moved jail management after content tasks so failures cannot block teardown. |
| `a59887a` | Enlarged outage messaging for projector readability and corrected the displayed server signature. |
| `ec943aa` | Introduced server-owned arming and a fresh nonce per arming. All clients become disarmed after a press, recovery does not re-arm automatically, and distinct arming bodies avoid AAP webhook deduplication. |

## Current implementation

The lifecycle now disables site rate limiting during an enabled audience
session and restores the previous button limit on disable. Conference users
share a public IP, so per-IP throttling would otherwise reject legitimate
presses. Page loads and polling were already unrestricted. A dedicated
credential-free nginx include confines the change to this site's button
location; other virtual hosts retain their limits. Reload verification checks
new workers because this session found that nginx can reject a configuration
while the reload command still reports success.

Implementation commit: `798dc3d916c411bec405892cc2baa9c953454d26`.

## Rate-limit rendering correction

The first live Disable test rejected the generated nginx include because
escaped newline strings did not become directive separators in the controller
execution environment. The rollback restored the prior include. Literal YAML
newlines now separate directives, avoiding reliance on escape interpretation.

Fix commit: `be885755105dab94e9f4a4153f77ba1abfe6323a`.

The corrected live Disable → Enable → Disable sequence passed. nginx accepted
the include changes, the expected HTTP and arm-state checks passed, and the
demo-specific fail2ban jail was restored at the end. The site was left disabled.

## Monitored website repair routing

The website monitor needs to reach HTTPS on the web host from an internal VM.
The host's VM-facing firewall zone rejects that incoming connection even
though internet-facing HTTPS and outbound VM web access work. A source-restricted
TCP 443 rule admits only the monitoring VM. The user clarified that this is
static host networking setup, so the initial one-time AAP playbook and template
were removed; the address remains outside this repository. A separate EDA
rulebook routes the dedicated website-content problem event to the existing
deterministic restoration template.

Implementation commit: `1ead8a2`.

Static-firewall correction commit: `f0d3176`.

## Deferred token maintenance

The user asked to track rotation of all demo integration tokens for later
maintenance, without changing credentials during the current repair-flow
setup. This is recorded in the design backlog.

Backlog commit: `427a9a5`.

## Deferred job template catalog review

The user requested a later review of which templates the different demos
still need and consistent labels for easier browsing. No deployed template
was changed during the current repair-flow setup.

Backlog commit: `aab1238`.

## Rearm after monitoring confirms recovery

The audience should be able to repeat the fault-and-repair cycle without a
presenter running Enable between presses. Rearming immediately when the repair
job finishes could let a second press happen before Zabbix closes the first
problem, so that press would create no new problem event. The website rulebook
now distinguishes problem and recovery event values: the former restores
content, while the latter launches the existing arm playbook through a job
template. A separate action scoped to the website trigger sends recovery
events to the same Event Stream. The arm playbook checks the content endpoint
before issuing a fresh nonce.

Implementation commit: `044bd41`.

## Compare numeric Zabbix event values

Live EDA logs showed that comparing a numeric event value with a quoted string
prevented both website rules from firing. Numeric comparisons restored problem
handling. Recovery delivery also required extending the existing Zabbix media
script's problem-only guard to accept recovery, while preserving the established
Event Stream destination, authentication header, and payload handling.

Rulebook fix commit: `fc075c7`.

## Tie monitoring to the website lifecycle

Disable now pauses the dedicated trigger and item before removing content.
Enable waits for a fresh healthy sample before enabling the trigger and arming
the audience button. This prevents intentional shutdown from starting a repair
and prevents audience presses before monitoring is ready. Live lifecycle jobs
1550 and 1552 verified the execution environment's API access and Vault setup.

At the user's request, encrypted project-root `myvars` supplies the monitoring
settings using the existing Vault credential. A standalone project checkout
cannot read the parent repository's shared Vault. The project file contains
only its monitoring settings. Vault-structure cleanup, token rotation, and
template catalog review are deferred until after the conference.

Implementation and integration-documentation commit: `b20aaa9`.

## Share concurrent audience deliveries at nginx

Ten simultaneous requests with the same arming nonce created nine fault jobs
despite AAP's sequential deduplication. Queued duplicates could outlive the
outage and inject another fault after recovery, so six queued test jobs were
cancelled. A dedicated nginx POST cache and cache lock now share one accepted
upstream delivery for each request body. Each automatic rearm produces a new
nonce and cache key. Two subsequent ten-request rounds each created exactly
one successful fault job, repair job, and rearm job.

The nginx snippets are versioned without private vhost headers. Live deployment
preserved existing access restrictions and forwarding, used a private backup,
validated nginx, and verified worker replacement. The browser now treats a 423
race as another participant pressing first and displays an automatic-recovery
message. A test of the actual page script verifies repeated transitions and
nonce changes without a page refresh. The recreation guide records today's
setup, troubleshooting, and validation, with environment-specific values kept
in encrypted configuration.

Implementation commit: `b49a988`.

## Final conference reliability rehearsal

The deployed lifecycle and concurrency fixes passed Disable 1581, Enable 1583,
two ten-request automatic rounds (1585/1587/1589 and 1591/1593/1595), and final
Disable 1597. Each round created one fault, repair, and recovery-driven rearm
job. Twenty simultaneous-round requests returned 202; late presses returned
the expected 423. Zabbix sent both event types without error and EDA logs
confirmed the repair and arm launches. The final placeholder, disarmed panic
endpoint, disabled monitoring, restored limit, and restored jail were verified.

The recreation guide includes the integration patches, protected Vault setup,
source-controlled cache snippets, a generic vhost example, operational lessons,
and test evidence. Optional improvements remain deferred after the conference.
Validated implementation commits: `fc075c7`, `b20aaa9`, and `b49a988`.

## Make the outage message visible to the audience

At the user's request, the technical missing-file sentence was replaced with
"OMG, PANIC, it is KAPUTT!!!" in larger bold letters. The detection timestamp
is retained, and reduced vertical padding leaves room for the larger message.
This is a presentation change; the user explicitly requested no repeated
end-to-end rehearsal. Deployment uses the existing Enable template.

Enable job 1616 deployed the change successfully from revision `ce0b102`.

Implementation commit: `1e7bcfd`.

## Shorten website monitoring to four seconds

The user requested faster website checks after the twenty-second rehearsal.
The dedicated HTTP agent item's interval was changed through the Zabbix API to
`4s`, retaining its enabled status. Readback confirmed the setting, and five
recent HTTP 200 samples were recorded four seconds apart. The recreation guide
and README now specify the new interval; earlier rehearsal results remain
historical evidence of the twenty-second configuration.

Configuration documentation commit: `4b447fd`.

## Make website health visible throughout the demo

The user needed a persistent green → red → green indicator. Short outages
were detected and repaired in twelve seconds, while a thirty-second frontend
refresh could miss the problem and show only the recovered record. A private
native Zabbix map now links one trigger element to green healthy, red problem,
and grey disabled icons. The presenter's profile refresh was changed to four
seconds. Standard dashboard widgets have a ten-second minimum refresh, so
the standalone map is the presentation view.

The existing website host's visible name was changed to its website hostname
for easier discovery under Monitoring → Hosts. Its technical identity and
HTTP check were retained. Map bindings, ownership, and profile refresh were
verified through API readback. The user confirmed the live-map icons looked
good. The repository includes the PNGs, matching SVGs, a standard-library
generator, and a generic map-create template with recreation instructions.
The generator and JSON template validation completed successfully.

Configuration documentation and asset commit: `964f666`.

## Rename the audience outage job template

At the user's request, the fault template is now named Simulate Website
Outage, with Inject Website Fault as its exact description. Only its name
and description were changed through the controller API. Readback confirmed
the rename and retained template ID, playbook path, webhook service, and
execution settings. The button's webhook references the ID, and the EDA
rulebook names only the repair and arm templates, so no nginx or rulebook
change was required. Current documentation and backlog references use the
new name; the original playbook filename is retained.

Configuration documentation commit: `964f666`.

## Refresh the EDA delivery display automatically

The user confirmed that filtering Reports → Action log made new deliveries
easier to identify, but that the report did not refresh automatically. A
private presenter dashboard now uses a native Action log widget with a
supported ten-second refresh, five newest-first entries, and a rolling
five-minute window. Its filters follow the existing problem and recovery
actions and Event-Driven Ansible media type. This retains pending and failed
notifications as well as successful deliveries. The problem action remains
shared, so other demo incidents can also appear in this view.

The standalone health map keeps its four-second profile refresh. The delivery
widget has its own refresh setting, and recent notification records remain
visible after the website has recovered. API readback verified private
ownership, no sharing entries, and every saved widget field. Browser refresh
behavior was not independently observed during creation. A portable request
template and the README/recreation guide record how to rebuild the dashboard.

Configuration documentation and dashboard-template commit: `8179c7a`.

## Combine website health and event deliveries

The user requested the existing green/red health indicator on the custom
delivery dashboard. A native Map widget now shows the existing live website
map on the left, with the Action log on the right. It reuses the map, trigger,
and icons. The existing log widget, its filters, and the dashboard's private
ownership and sharing were retained.

Both widgets use the supported ten-second dashboard refresh. The standalone
map remains available with four-second profile refresh for faster health
updates. API readback verified both map and log bindings, the side-by-side
geometry, widget refresh settings, and preserved access settings. The portable
dashboard template and recreation instructions now include both widgets.

Configuration documentation and dashboard-template commit: `e00f8a0`.

## Preserve the unfinished AAP dashboard extension for another session

The user requested the selected EDA Event Stream's received count and recent
and currently running Big Bad Button jobs on the existing Zabbix dashboard.
The job queries are restricted to the demo templates. A gateway read-scope
token supplies API access; environment values remain in the project Vault,
the Zabbix token macro is secret, and preprocessing retains only the fields
needed for the display. Existing service health and notification widgets are
retained in the expanded six-widget layout.

The configuration was created and read back during the earlier session, but
metric collection failed because the Zabbix poller could not validate the AAP
certificate issuer. The issuing CA needs to be checked and trusted on the
poller; TLS verification remains enabled. This is an unfinished checkpoint,
not a claim that the new dashboard works end to end. Local preprocessing,
syntax, template/layout, documentation-link and Vault checks passed.

The user cancelled the extra ten-second repair pause after confirming that
the existing job works well live. The uncommitted pause was removed before
deployment; the repair playbook is unchanged. On 2026-10-17 the user requested
a committed handoff so another chat can resume from Git and the existing
Vault password file. The README, recreation guide, backlog and dated handoff
record the scope, blocker, external access prerequisites and remaining checks.
Generated Python bytecode is excluded from version control.

Checkpoint implementation and handoff commit: `f03a18f`.

## Select the website hostname per environment

The hypervisor rebuild needs production and test copies to run separately.
The enable/disable, content-restore and button-rearm checks now use an
environment hostname instead of a literal production name. The existing
production value is preserved in the encrypted project Vault; inventory or
job extra variables can override it. HTTPS verification, loopback resolution,
expected status codes and all other lifecycle tasks are retained.

Restore and rearm now load the same Vault file as enable/disable. Their
existing machine-only templates must receive the existing project Vault
credential before this revision is synced into a deployed controller. This
requirement is recorded in the README and recreation guide. No controller
settings, project syncs or live website changes were made for this change.

Three local Ansible tests use synthetic encrypted settings and a curl recorder
to cover the production default, an inventory-selected test hostname and a
job override. They exercise argument rendering without contacting services.
Syntax and lint pass. Comparison with the preceding revision confirms the
other tasks and existing Vault settings are unchanged; a live lifecycle
rehearsal remains part of replacement-host validation.

Implementation and documentation commit: `89e113f`.

## Prepare the hostname revision for main — 2026-10-30

The user prefers working on main and explicitly approved attaching the
existing project Vault credential to the restore and rearm templates before
merging the hostname change. Both associations were applied through the
controller API and verified by readback, preserving their machine credentials.
The MCP credential-association tool's request schema could not express an
existing credential association, so the normal authenticated API was used
with TLS verification. No credential was created and no lifecycle job was launched.

The generic recreation instructions continue to require Vault on all four
lifecycle templates. The current deployment's association is complete;
cloned-controller setup and a live recovery rehearsal remain separate work.
The source implementation remains `89e113f`, with its production hostname
default encrypted and inventory/job overrides covered by three local tests.
