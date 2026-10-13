# Design decisions history

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
