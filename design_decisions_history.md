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
TCP 443 rule admits only the monitoring VM. Its address stays in the AAP job
template, not this repository. A separate EDA rulebook routes the dedicated
website-content problem event to the existing deterministic restoration
template; this avoids sending a known repair through the agent diagnosis path.

Implementation commit: `1ead8a2`.
