# Design decisions history

## Bound monitoring DNS readiness through the observed negative cache — 2026-11-08

Implementation `93a30e36554c7e640ef2f711d00b6e1fc5d36d40` changes only the existing monitoring frontend's DNS
retry count from 30 to 65, retaining its ten-second retry delay and immediate
success when the original assertions pass. The controlled zone's SOA permits
600 seconds of negative caching; its provider and an independent public resolver
already returned the correct address while the hypervisor lookup still failed.
The previous 300-second window expired after the guest had been authenticated.

The selected IPv4, absent-IPv6, TLS, ownership and rollback checks remain
unchanged. No resolver fallback, fixed sleep, DNS record change, listener,
credential transfer or helper was added. The same deployment template reuses
its authenticated owned clone; VM ownership can be retained separately without
claiming its frontend is ready. All 14 existing versioned-Zabbix regressions,
strict production lint of the changed task file, YAML parsing and whitespace
checks passed. A normal AAP retry remains the live acceptance step; publication
alone does not prove the complete demo. The changelog identifies deployment
correction 1.1.7 and retains the unfinished 2.0 roadmap.


## Deploy Claude with the existing private MCP integrations — 2026-11-04

Implementation `80b7dff` adds one application playbook and its reviewed native
Claude release/ownership checks. The execution environment downloads the pinned
official binary with trusted HTTPS and validates its SHA-256 and size before
copying it to the verified TRA. The pin was checked against Anthropic's signed
manifest and published signing fingerprint. The actual incident-job account must
resolve the installed command and report the selected version. A different
existing command is preserved for review; no full Assistant Team installation
or new service, credential type or secret store is introduced.

The same job reuses the existing Linux and Zabbix MCP playbooks and their private
stdio/read-only verification. Their selected workspace now follows the incident
job's override consistently. Every existing directory component is checked
without following links before creation, existing directory modes are retained,
and the existing guardrails seed only a missing instruction file. User edits and
other MCP project entries remain intact.

The owner explicitly approved reusing the current Vertex authentication. Only
the selected project/region and approved authorized-user ADC are persisted in
the existing private runtime Vault and provisioned to that runtime account.
Conflicting provider/account configuration, unrelated paths and concurrent
authentication changes stop provisioning. Secret values remain literal and
protected. Provider recognition is checked without inference; private AAP MCP,
phase-output correction and functional agent remediation remain separate work.

Fourteen focused Claude/workspace/Vertex tests, ten MCP tests, seven native
runtime-loader tests and two private ciphertext-maintenance tests passed.
Native fixtures cover both modes, integrity failure cleanup, path/link refusal,
existing settings preservation, account conflicts, concurrent changes,
idempotence and literal secret canaries. Three playbook syntax checks and strict
production lint across ten files passed. Actual encrypted CaC renders eleven
templates in both modes with the existing credentials and opaque runtime input.
These results establish code/configuration readiness, not a live installation
or model test. The parent coordinates the shared target's normal deployment.

Integration `501821c` preserves the independently published visualization-link
documentation commits `c13573a` and `3eee49f` through a normal merge. Their source
and documentation remain intact.

## Require problem events before launching the agent — 2026-11-04

Implementation `ba7785d` requires the agent-unavailable name and problem value
before launching the existing remediation template. The selected live media
script was read back: it converts Zabbix macro strings to numeric event values.
Four focused tests execute the maintained JavaScript and evaluate the saved
condition with native Ansible. Problem values match; recovery, missing/unknown
values and unrelated event names do not. Offline production lint passed.
The website's separate problem/recovery rulebook remains unchanged.

Read-only inspection confirmed the existing template selects the verified TRA
and MCP account. Its private Linux and Zabbix stdio servers initialized and
listed tools without tool calls or image pulls. Concrete remaining prerequisites
are the Claude executable, target-owned provider authentication, reviewed
workspace instructions, private target AAP MCP configuration and a reviewed
provider-egress policy. No application job, activation, model invocation,
provider login or new fault was performed. Exact instance and inspection
metadata is retained in the private evidence Vault; the full agent-remediation
rehearsal remains unproved.

## Verify the published monitoring playbook through its normal job — 2026-11-04

Implementation `1172d8a`, published in revision `9b83204`, has now completed the
normal monitoring deployment using the matching private inputs from `f44193a`.
This verifies the repeatable playbook after the initial in-place API repair.
Independent readbacks found no remaining reconciliation changes, exactly the
selected forwarding action enabled, the website activation still running and
healthy content and arm endpoints over trusted HTTPS. Copied unrelated hosts
and actions remain disabled.

The public source, private capture and corresponding hypervisor policy changes
have been published and their remote heads independently checked. Exact job and
resource evidence remains encrypted in the private companion repository.
At that checkpoint, a separate AutoDeploy repeat-import failure was still under
investigation; it did not stop the working website activation. AutoDeploy
implementation `8c0af1c` subsequently preserved the original activation variable
text, and its normal import passed on version 0.34.3 while preserving activation
state, the Event Stream and existing template identities.

## Verify the existing agent job on its intended guest — 2026-11-04

The existing agent playbook completed a normal job after private capture
implementation `f44193a` selected this repository and host implementation
`223606d` recorded the approved HTTPS bootstrap allowance. Its fixed one-host
limit and guest machine identity were verified. Installation, selected server
configuration and enabled service passed, followed by a successful passive
agent ping from the matching monitoring VM.

The owner's real website button/webhook test also produced successful automatic
restore and rearm jobs. Exact environment/job details remain in the private
evidence Vault. Copied testserver monitoring and remaining guest recovery
restrictions are still separate unfinished work. These checks make no further
source-code or credential changes; Git publication remains pending.

## Reconcile copied monitoring before enabling delivery — 2026-11-04

Implementation `1172d8a` follows the owner's requirement to replace copied
production endpoints with the selected deployment's settings before enabling
event forwarding. It updates known host identities, item labels, trigger labels,
interfaces and URL macros in place, preserving record IDs and history. The
canonical website check stays distinct from the disabled imported duplicate.
Copied dashboard credentials are cleared, and stale administrator EDA media
associations are removed while unrelated media remain disabled.

The selected website action stays disabled through frontend and exact delivery
readbacks. The existing delivery flag enables only that action as the last
configuration write. Other inherited hosts and actions remain disabled. This
retains the approved quarantine and existing Basic Event Stream authentication.

Nineteen focused tests, including real Ansible execution of final enable and
failure-before-frontend paths, passed. Syntax, twelve-file production lint and
whitespace checks passed. The selected live clone's reconciliation readback is
idempotent, trusted frontend checks passed, and an unmatched diagnostic event
reached its own Event Stream over trusted HTTPS. A subsequent normal fault job
produced problem and recovery events; EDA automatically ran the existing restore
and rearm templates successfully. Final trusted HTTP checks confirmed healthy
content and an armed button, with the monitoring trigger recovered. Protected
evidence is retained in the private companion repository.

Publication remains pending under the active local-only Git rule. These live
settings were reconciled through the existing authenticated API using the
reviewed helper. The normal monitoring deployment job has not yet executed this
new, unpublished playbook revision.

## Verify the versioned website after base tooling — 2026-11-04

The normal website deployment from implementations `73d6b08` and `cf111b2`
has now succeeded after the owner-approved Git prerequisite installation.
Independent checks cover public trusted HTTPS, healthy content, valid nginx,
the selected new AAP webhook and enabled upstream certificate verification.
The matching monitoring item reports HTTP 200 and no problem trigger. The
button and event delivery remain disabled; no outage or agent execution was run.

The first certificate request saw cached NXDOMAIN after DNS creation. The
existing rollback preserved nginx; a normal rerun succeeded after independent
public A/AAAA convergence checks. This is an operational result, with no new
playbook, workflow, authentication mechanism or certificate-account registration.

## Verify both MCP jobs on the new TRA — 2026-11-03

The normal Zabbix MCP job and an independent stdio/read-only query now pass on
the fixes in `ef45ec7`, deployed at `15bf30e`. The exact approved image, private
API endpoint, 0600 configuration, read-only policy and existing Linux/client
settings were checked. Linux MCP was already independently verified on the
delegated-connection fix in `06f64ba`. Both actual deployment tasks are complete.
Website deployment and event/remediation readiness remain separate; no public
MCP listener or agent execution is introduced.

## Match the monitoring container user and native count response — 2026-11-03

Implementation `ef45ec7` fixes two observed failures in the real Zabbix MCP
deployment. The approved image runs as non-root UID/GID 999:999; its invocation
now maps the existing TRA user to those image IDs, preserving the owner's 0600
configuration and read-only mount. The server's unchanged safety disclaimer is
followed by a JSON string count, so the verifier decodes that exact payload
before requiring a numeric count. Authentication errors and malformed, empty,
object or list results still fail.

A native before/after test using the exact saved image reproduces the original
permission error and then completes stdio discovery and an authenticated
read-only query with unchanged private configuration. Ten MCP checks, syntax
and scoped production lint pass. Normal Job Template retry remains a separate
deployment verification. The website still requires its base tooling, and no
event delivery, outage, model invocation or public MCP endpoint is enabled.

The same publication documents independently verified Linux MCP and Zabbix
deployment results. The monitoring clone's identity and object IDs match its
private capture and source inventory; trusted public and guest-to-own-host HTTPS,
quarantine and the proxy backend pass. Website health and the full remediation
loop remain separate work.

## Wait for the protected monitoring frontend — 2026-11-03

Implementation `ef7af00` gives the final frontend probe a bounded retry window
after nginx publication. The expected result remains trusted HTTPS with HTTP
401 and a Basic authentication challenge, with redirects refused. Independent
checks passed after an actual deployment's final probe failed, so this change
handles temporary readiness failures without relaxing authentication or trust.

Native Ansible tests verify temporary failure followed by readiness, permanent
failure, and rejection of a missing Basic challenge. Scoped production lint
and the existing quarantine checks pass. Actual deployment retry is tracked
separately from this publication.

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


## Validate the offline runtime install set on the selected guest

The existing runtime installer from f8ccebe keeps signature and repository
restrictions. Private configuration implementation 04267b8 corrects its RPM
input after DNF rejected an overbroad dependency request before installation.
The revised procedure resolves the runtime against the selected guest package
database, includes conditional SELinux providers, and records only the proven
install set. The real read-only solve required no installed package removals.
This documentation does not claim the later installation or MCP smoke test.


## Preserve original SSH context and complete cloned guest identity

Implementation 06f64ba fixes delegated testserver connection options by reading
the original TRA facts explicitly. The actual MCP installation reached the
identity check after installing the verified runtime and image, then Ansible
failed to resolve the delegated variables before SSH. A native SSH recorder
reproduces the original error and verifies the corrected pinned connection.

The Zabbix deployment also emits complete verified machine, SSH and network
ownership once guest identity has been checked, supporting later MCP setup and
cleanup. Its exact-disk guard accepts the positive numeric index produced by
libvirt while rejecting foreign source attributes and different files. Nine MCP
cases and nine Zabbix cases, syntax checks and scoped production lint passed.
These fixes do not claim the subsequent live deployment has completed.


## Keep the cloned Zabbix hostname canonical

Implementation eac43d7 places the clone hostname first in the one owned hosts
entry for versioned proxy URLs and idempotently repairs that same entry on an
existing clone. The actual guest had the correct static hostname and verified
machine identity, but its fully qualified hostname resolved to the first website
alias sharing that address. The existing identity check now retains its purpose
without replacing unrelated hosts entries or recreating the VM.

Nine focused cases, native old-entry repair and unrelated-localhost preservation
checks, syntax and scoped production lint passed. The server remained masked
during diagnosis; no source monitoring service or credential was changed.

## Visualize missing-agent recovery through the existing AAP catalog

The user requested one continuous missing-`zabbix-agent2` recovery story with
**AAP as the Trusted Execution Layer**, using the Windows + AAP visualization
as the presentation reference. Release 1.1.0 adds a buildless static frontend
in `demo/` with an explicit SVG platform containing EDA, separate MCP interfaces,
and 17 presenter-paced stops. AI investigation, evidence correlation, catalog
discovery, job requests, AAP execution, and monitoring confirmation remain
distinct. A successful remediation job leaves monitoring unresolved until a
subsequent check confirms recovery. The functionality-demo wording separates
platform capabilities from configured controls and agent instructions.

The repository had no configured Pages site or workflow when inspected. The
new workflow follows the reference's GitHub Actions approach and stages only
an explicit frontend allowlist. This avoids uploading automation or protected
configuration alongside the walkthrough and needs no frontend build dependency.
This work changes no live AAP, monitoring, managed-host, or agent configuration.

Validation: both runtime scripts passed syntax checks; 14 built-in Node tests
passed for story ordering, MCP routes, AAP-originated execution, monitoring
verification, and actual application handlers in a minimal DOM harness. HTML
references, relative links, workflow structure, local assets, and sensitive
patterns were checked. The user declined Chromium installation; no browser was
installed and rendered desktop/mobile inspection was not performed. The DOM
harness does not attest to browser layout.

Implementation commit: `19da250`.

Publication outcome: the user explicitly requested pushing the visualization
and its GitHub Pages link. Both implementation and decision commits were pushed
to `main` over SSH. The first workflow run failed at Configure GitHub Pages
because Pages was not enabled. After inspecting that exact error, Pages was
enabled with the workflow build source and only the failed deployment was
rerun. GitHub Actions run `41824037505`, attempt 2, succeeded at source
`777ec46`; both validation and publication succeeded. The public HTML returned
HTTP 200 and matched the committed frontend byte for byte. No Chromium was
installed, no browser-based layout review was claimed, and no managed
infrastructure was contacted. Implementation remains `19da250`.

## Separate AAP brand color from incident status

The user requested a more professional, fresh technical palette, proposed
Red Hat red for AAP, and approved the resulting color set. Release 1.1.1 uses
the official `#ee0000` as a fixed AAP header and headline accent above a dark
navy platform. This preserves clear Red Hat identity while keeping brand
color independent of incident state. White surfaces, blue interactions and
MCP reads, and teal AI/execution accents replace the softer mixed palette.
Dark crimson Problem statuses and green Recovered statuses retain the agreed
monitoring story. Labels, line widths, and dash patterns continue to carry
meaning alongside color. This is a demo palette, not a claim of full Red Hat
product-interface compliance. The brand reference is
https://www.redhat.com/en/about/brand/standards/color.

SVG marker colors match their paths and legend. Muted text is darker for
readability, and twelve representative text/background combinations meet
4.5:1 contrast or better; the white AAP heading on brand red measures 4.53:1.
All 14 existing story and application-handler checks passed, both runtime
scripts passed syntax checks, and a structure comparison confirmed the CSS
changes affect color rather than layout or behavior. No new tests were
added for this visual correction. No browser was installed or run, in line
with the user's server constraint; rendered review remains unverified.

Implementation commit: `fdd676f`.

## Reduce the visual dominance of the AAP brand accent

After seeing release 1.1.1 live, the user found the solid Red Hat red header
visually harsh. Release 1.1.2 restores the deep navy AAP header and dark
headline, retaining only a thin red brand line and small brand details.
The blue MCP paths, teal AI and execution accents, and labeled crimson/green
incident states remain. This makes the large architectural form calm and
stable while keeping a small brand reference.

Both runtime syntax checks and all 14 existing story/application-handler tests
passed. This correction changes color emphasis only and adds no browser or
new dependency. Rendered browser inspection remains unverified under the
user's no-Chromium constraint.

Implementation commit: `06a06b9`.

## Show an interchangeable AI agent role in the walkthrough

The user requested replacing the displayed Claude Code CLI label with
**Codex/Claude/Copilot etc**. Release 1.1.3 shows that exact text on two lines
inside the existing agent node and uses generic runtime wording in the
walkthrough. The surrounding architecture, MCP paths and AAP execution
relationship are retained. Technical detail explicitly states that the current
repository launcher invokes Claude Code CLI and preserves its real source
excerpt and job-template names; this presentation change does not implement
additional runtime integrations or alter automation configuration.

Validation: both runtime scripts passed syntax checks, all 14 existing model
and application-handler tests passed, the SVG label's combined text matched
the request exactly, and diff checks passed. Automation, agent instructions,
and rulebooks were verified unchanged. No dependency or browser was installed
or run; rendered layout review remains unverified.

Implementation commit: `26223e3`.

## Make functionality more prominent than product names

The user clarified that functionality should be the primary visual message.
Release 1.1.4 makes PROD SERVER, MONITORING, and AGENTIC AI the large headings,
with smaller captions reading Red Hat Enterprise Linux, Zabbix in this case,
and Claude in this case. Role headings use 22 px SVG type and product captions
11 px. The AAP platform follows the same hierarchy: TRUSTED EXECUTION LAYER
is the 25 px heading and Ansible Automation Platform is the 12 px product
caption. Existing palette, shapes, connection routes, step controls and
monitoring-verification behavior remain. Other agent runtimes are still
mentioned as examples in technical documentation; no runtime configuration
was changed.

Validation: both runtime syntax checks, all 14 existing story/application
checks, exact heading/product-caption verification, and diff checks passed.
Automation, rulebooks, and agent instructions were verified unchanged. No
new tests were added for this presentation adjustment. No browser or dependency
was installed or run; rendered browser review remains unverified.

Implementation commit: `b7c1409`.

## Introduce the incident with a general error heading

The user requested replacing One package disappears with An error suddenly
arises. Release 1.1.5 updates the failure-step heading and initial Next-button
label, reusing the existing arrow. The underlying missing-agent-package
scenario, explanation, technical detail, and state transitions remain.
Both runtime syntax checks, all 14 existing tests, and diff checks passed.
No browser, dependency, or runtime configuration changes were needed.

Implementation commit: `39c4e60`.

## Give Ansible Automation Platform the leading product identity

The user explicitly requested a much larger, bold Ansible Automation Platform
name because AAP is the central character. Release 1.1.6 gives the full product
name 32 px SVG type at weight 750, alongside a 20 px Trusted Execution Layer
label. The product title is bounded to 430 SVG units to preserve clearance
for the existing job-dispatch and MCP paths. Other components retain their
large function headings and small product captions. Palette and workflow
behavior remain unchanged.

Both runtime syntax checks, all 14 existing tests and diff checks passed.
Automation, rulebooks and agent instructions were verified unchanged. No new
tests were added for this presentation change; no browser or dependency was
installed or run. Rendered browser review remains unverified.

Implementation commit: `bf52f59`.


## Enable verified Linux monitoring through the existing deployment

The copied monitoring image carried Apache checks that do not apply to the
minimal versioned testserver. Agent installation alone also left that host
disabled. The existing Zabbix deployment now accepts an explicit per-instance
monitoring opt-in after agent readiness. It verifies the actual domain/lease and
passive agent identity, enables reviewed Linux/ICMP checks, disables only the
retained Apache entities and requires fresh numeric samples. Unknown template
ownership fails before status changes. Existing records/history, website
forwarding and the disabled general Claude activation are preserved; no model
invocation or new job/service/credential is introduced.

Implementation: `a2ccdd9`. Integration `e688f67` preserves the independently
published interactive walkthrough. Native fixture execution covers normal
deployment and repeat configuration; identity, ownership and stale-sample
regressions, syntax and scoped production lint passed. Both the normal monitoring deployment and an unchanged normal repeat passed
actual fresh-sample and independent configuration readbacks. Original check IDs,
website readiness and the disabled general Claude activation were preserved;
exact runtime evidence remains in the private companion Vault.


## Keep application identity stable when the AAP inventory name changes

The launch input selects the current AAP inventory entry. Private AIOps guest
and runtime records use that entry's existing `vm_resource.vm_name`, retaining
the created VM name independently of its inventory alias. Placement and FQDN
lookups continue to use the selected entry. This permits inventory naming
cleanup without renaming VMs, tokens, registry records or runtime Vault keys,
and requires no new mapping or store. Missing VM metadata stops rendering.

Companion implementation: `a9ed0be`. Full resource rendering is identical for
the original selection and renamed alias in both native Ansible modes, including
runtime ciphertext, guest identities and monitoring opt-in. Current monitoring
and activation readbacks remain healthy; no application job was launched.

## Make the published visualization easy to find in the documentation

The user requested adding the visualization link to the AIOps demo repository's
documentation. The link already appeared in the walkthrough section; this
change adds a prominent link directly beneath the title of the repository
README, starting-setup guide, and presenter guide. Readers can open the static
recovery story before following the implementation documentation. Existing
concurrent documentation and automation updates were preserved by first
fast-forwarding the clean checkout to current main over SSH.

Validation checked the exact destination at all three entry points and clean
diffs. This is documentation only: frontend version 1.1.6 and all runtime,
workflow, configuration and dependency files are unchanged.

Implementation commit: `c13573a`.

## Bound the existing agent repair and trust only the selected private AAP

Implementation `8422662` carries the selected private AAP MCP connection through
the existing encrypted runtime and installer. Application-scoped verified CA
trust leaves system trust unchanged, preserves unrelated Claude settings, and
does not publish an MCP endpoint. The existing runner keeps native permission
checks and uses a small deny-only invocation hook for the verified repair
template and Linux host. It reports success only after actual repair children,
the selected agent service and fresh monitoring recovery pass independent checks.
The existing agent installer now verifies packages using the fingerprint-pinned
official signing key.

Native HTTP and certified Controller modules cover network probes and child-job
verification. Remaining protocol/selected-data filters and the invocation hook
have explicit boundaries; broader standard-content cleanup is separate work.
Twenty focused tests, syntax checks and compilation passed, including failed
child, stale monitoring, wrong CA, target/override refusal and preservation of
edited instructions. Optional lint was not verified. These checks do not claim
a completed live remediation rehearsal.

Before publication, the owner approved pinning only the original production
SCM Project to tested commit `b32ceb675d2699205400daee327f9b89ddb5f10a` because
its legacy runner lacks the new encrypted runtime inputs. API readback and the
automatic SCM update confirmed that pin; production execution was unchanged.
Shared desired CaC remains on `main` for test and future instances. Removing
the production exception requires an explicit runtime migration. No new
credential type, store, repository, Job Template, public listener or service was
introduced, and no model call, fault or activation was started by publication.

## Forward only selected agent incidents and require a real repair — 2026-11-06

Implementation `c618d1f` adds one allocation-local Zabbix action for the verified
testserver's existing agent-availability trigger. It reuses the current Event
Stream media and recipient, and resolves the trigger only after copied monitoring
has been reconciled. Both selected actions remain disabled until final delivery
validation; the existing delivery setting can then enable them. Imported
unfiltered actions and media remain disabled, and no EDA activation is enabled.

The bounded runner now requires at least one native repair child before accepting
recovery. Existing target checks, child success, service and fresh monitoring
proof remain in place. The manual guide now describes the maintained native
permissions and bounded job rather than duplicating an obsolete bypass command.
Active MCP, EDA and walkthrough guides link to that procedure as well; archived
historical notes retain their original context.
The runner's non-idempotent invocation is reported as changed, and its long
expressions were wrapped for the existing production lint profile.

Focused native checks reject an absent or failed repair, stale monitoring and
untrusted TLS; selected-action checks preserve imported restrictions. Both
playbooks passed syntax and thirteen files passed offline production lint.
Code readiness is separate from normal monitoring setup and the controlled
alert-to-repair test, which remain pending at this publication checkpoint.

## Read project identity from the actual Controller job — 2026-11-06

Implementation `269a2e7` fixes the first live event-driven runner attempt, which
stopped before model invocation because Controller does not inject a project-ID
variable. The runner now uses the existing certified Controller job-list module
to read its native job ID through selected trusted HTTPS. It verifies the
injected inventory and exact saved limit, then uses that native project ID for
repair selection and child verification. No target restriction was removed.

The real monitoring event reached the Event Stream, the intended EDA rule and
the saved runner. After the pre-model failure, the agent activation was stopped
and the existing repair restored the service; fresh monitoring confirmed recovery
of the original problem. The model repair remains unverified and needs a new
controlled test. The existing native fixture now covers a Controller context
without a synthetic project variable and rejects a mismatched current-job
inventory. Syntax checks and focused offline production lint passed.

## Match the installer's default workspace — 2026-11-06

Implementation `d81e7e6` fixes the next live attempt. The event reached the saved
runner and passed its initial context
check, but stopped before model invocation because an absent workspace override
was supplied as null. The existing workspace filter expects an empty string to
select the installer's account-local default. The correction uses that same
default without changing installed files or allowing a different destination.

The existing native argument fixture now evaluates the actual default-workspace
expression under both supported Jinja modes. Read-only checks against the selected
installed user, instructions, application CA and private MCP definitions passed.
The activation was stopped and the normal repair succeeded after the failed
attempt. No model inference ran; full automatic remediation remains unproved.

Implementation `54304f1` extends only the existing monitoring postcheck from
ninety seconds to three minutes. The controlled cleanup exposed a real
107-second delay between a successful repair and original-trigger recovery,
followed by a fresh agent item sample. This accommodates the existing passive
availability/item polling without weakening service, child-job, target or TLS
checks. The model's 600-second hard timeout and maximum repair count are unchanged.

## Keep useful failure metadata without exposing model output — 2026-11-06

The first real bounded model invocation launched the correct existing repair,
which succeeded. Independent checks confirmed the selected service and fresh
monitoring recovered. The parent runner nevertheless exited unsuccessfully
inside its CLI command before its acceptance checks. Protected command output
was censored and no persistent session/debug log was available, so the exact CLI
cause remains unknown; successful remediation acceptance is not claimed.

Implementation `671b4a8` adds only numeric CLI exit code and an explicit whitelist
of known completion markers to the existing failure message. Raw model/tool
output and stderr remain protected. This does not recover discarded output from
the prior attempt or change its model budget, permissions or cleanup. The
existing native fixture verifies recognized diagnostics are visible and secrets
in stdout, stderr and unrecognized status values stay absent. Focused tests,
syntax and strict offline production lint passed. A further controlled model
attempt remains a separately reviewed action.

## Allow the observed investigation to finish within the same timeout — 2026-11-06

Implementation `67a6e69` raises only the existing invocation turn limit from
24 to 48. A reviewed diagnostic episode exposed CLI exit code one and
`error_max_turns` after the selected native repair succeeded. Independent
service, fresh item and original-trigger recovery were verified, and the
activation was stopped before any further inference.

The existing 600-second hard timeout, at most two repair children, selected
target, prompts, deny hook and TLS checks are unchanged. The actual argument
fixture now asserts both 48 turns and the unchanged timeout. Focused native
tests, syntax and strict offline production lint passed. This publication does
not claim that a subsequent full remediation acceptance has passed; its live
test requires the separately reviewed finite window.

## Verify the complete controlled agent-remediation chain — 2026-11-06

The reviewed runtime at `3da21af`, including bounded-turn implementation
`67a6e69`, passed the real isolated service-outage rehearsal. One operator stop
on the identity-pinned selected guest produced a new agent problem, reached the
current Event Stream and intended EDA rule, and launched one native runner.
The single model invocation launched one saved repair, which succeeded. The
runner independently verified the child target, active service, fresh agent
sample and original-trigger recovery before reporting success.

The reviewed scoped agent activation remains enabled after success, alongside
the unchanged website activation; imported unfiltered forwarding stays disabled.
This matches the existing captured desired state without adding an autostart
framework. The generic importer still preserves existing activation runtime and
requires the explicit reviewed enable step for a fresh definition. The shared
writer window was released immediately after the actual success/proof.

The test exercised a stopped service rather than package removal. It establishes
this controlled demo flow, not a production migration, unrestricted remediation
catalogue or completed formal code review. The production tested-commit pin was
not changed.
