# Changelog

Versions here track **what has been demonstrated and proven**, not an API
surface:

| Bump | Meaning |
|---|---|
| **Major** | A new demo scenario, complete and tested end to end |
| **Minor** | New functionality within the current scenario |
| **Patch** | Fixes to existing functionality |

History starts at `v1.0.0`. The pre-split history was moved to a private
archive during the repository split and is not part of this timeline.

## [Unreleased] — towards 2.0.0

The audience-facing button demo: the room causes the outage from their
phones and watches the platform put it back. Not yet end to end — the
nginx vhost, Zabbix web scenario, EDA rule, fault-injection and restore
templates, and the status page are still outstanding.

### Added

- Versioned website infrastructure in the existing Enable job: reuse the
  selected AAP allocation for DNS, existing-account certificates and a dedicated
  nginx virtual host, with pinned hypervisor SSH/machine identity and verified
  HTTPS forwarding to that AAP. Initial recovery deployments keep monitoring,
  shared fail2ban changes and audience button arming disabled until their own
  monitoring/repair integration is ready. DNS authorization and the target's
  generated webhook information have no saved secret defaults; their protected
  runtime settings use the existing private whole-file Vault and runtime
  credential, with native loading and unconditional temporary-file cleanup.
- Separate versioned Zabbix deployment: immutable saved-image cloning,
  quarantine before monitoring starts, target-local website monitoring and a
  trusted HTTPS frontend retaining Basic authentication. Event delivery stays
  disabled until explicitly released.
- Two requested MCP deployment playbooks retain the existing on-demand
  Podman/stdio servers on the matching new TRA. They build pinned public
  upstream sources on that TRA, pin fresh guest SSH keys and perform
  read-only protocol checks. Linux MCP generates its private key only on TRA;
  Zabbix MCP requires the new target's explicit API token. Neither opens a
  public MCP port or installs or launches the agent.
- Exact reviewed `community.general` collection pin for the public DNS checks.

- `demo-web/index.html` — outer shell that polls `content.html` every 2s
  and renders either the site or a 404. Untouched by the fault, so every
  phone flips to the outage and back without a refresh.
- `demo-web/content.html` — the corporate page mockup, built to Red Hat
  brand standards (red-50 `#ee0000`, Red Hat Display/Text), with the
  **Secret Red Hat Button**. This is the file the fault moves aside, so the
  404 the audience sees is a real one.
- `demo-web/disabled.html` — inert placeholder served while the demo is
  switched off. No JavaScript, no external requests.
- `playbooks/demo_website.yml` — switches the site on and off around a
  demo session. Disabling swaps the page rather than deleting the site, so
  the URL keeps answering.

### Changed

- Fresh-target inventory data comes from the AIOps private capture's selected
  allocation and verified guest artifacts. Guest jobs reuse the target's existing base Machine
  credential; hypervisor jobs retain their separate Machine credential.
- Website and monitoring checks use the permitted configured DNS resolver and
  pinned hypervisor route. Managed website monitoring requires explicit new
  target inputs instead of using production monitoring defaults.
- CaC import and application execution are documented separately. The ten
  template definitions can be imported independently of application execution;
  missing settings stop dependent jobs before managed writes. Unsupported inline
  Vault launch scalars and JSON Vault-marker mappings are not advertised as a
  Controller transport.
- MCP runtime preparation uses the target's configured trusted RHEL package
  repositories with package GPG checks enabled, without an offline RPM closure.

- `playbooks/demo_website.yml` — Enable removes rate limiting for the whole
  audience site; Disable restores its previous button limit through a
  dedicated nginx include. Reloads verify actual worker replacement.

- `playbooks/run_claude_analyse_fix.yml` — the user Claude Code runs as is
  now `claude_agent_user` from inventory instead of being hardcoded.
  **Breaking:** the job template fails its assert until that variable is
  supplied.
- `playbooks/deploy_zabbix_agent.yml` — dropped the `myvars` vault
  dependency in favour of asserting `zabbix_server` from inventory.
  Removes `playbooks/myvars.example`.
- Docs — remaining environment-specific identifiers replaced with
  placeholders (`AGENT_USER`, role names for hypervisor and TRA hosts).
- `demo-web/` — dropped the Google Fonts dependency for a system font
  stack. All three pages now make zero external requests, so they render
  identically on an audience phone with nothing but venue wifi.

## [1.6.3] — 2026-11-10

### Fixed

- A failed bounded agent invocation now reports an ordered, limited summary of
  allowed tool names, call counts and returned/error outcomes. Raw arguments,
  results and model prose remain protected. This makes a future turn-limit
  failure diagnosable without storing a transcript or starting another run.
  The 48-turn budget, timeout, permissions and recovery checks are unchanged.
- An earlier controlled test repaired the selected agent and recovered its
  monitoring, but its parent invocation exhausted the turn limit. Its retained
  logs lack a tool trace; the cause remains unproved, and this diagnostics patch
  does not establish a fix for that failure.

### Validated

- The later normal event-driven v17 rehearsal passed on tested source
  `41166495d72264e882bafe9ec2721649b0d70d9e` (implementation
  `02627ba8ff0044d89b8abad92a62177f5f0973c6`). The bounded agent invocation
  succeeded in 342.760 seconds and its saved repair in 12.318 seconds, with
  unchanged 48-turn/600-second limits and native permissions. Target and saved
  input checks passed, followed by an active service, a fresh agent ping and
  recovery of the original trigger. The EDA event and invocation were correlated;
  both test activations were disabled and stopped afterward, with no active test
  jobs in the final audit. Teardown and successor reinstallation are not claimed.

## [1.6.2] — 2026-11-09

### Fixed

- Pass the existing importer's optional `debug_logging` choice as the exact
  declared string `false`, rather than a YAML Boolean. Protected logging,
  target selection, saved credentials and the survey itself are unchanged.
  This aligns the request with the inspected schema; it is not a newly observed
  live deployment failure.
- Match the existing producer fixture to the actual generic multiple-choice
  schema and require the launch value's type and declared choice. The fixture
  rejects the prior Boolean value.

### Verification

- The strengthened existing success fixture fails with the prior Boolean and
  passes after the one-value correction. All four focused producer cases,
  scoped strict lint, deployment syntax and whitespace checks pass. Controller
  operations remain substituted; the parent owns the normal live retry.

## [1.6.1] — 2026-11-09

### Fixed

- Parse native Controller lookup inventory variables when Ansible marks the
  outer text as unsafe. LibYAML requires a base string, so the filter strips
  only that transport marker immediately before native YAML loading and keeps
  its result protected. Existing ownership, target and conflict checks remain.
  The observed job stopped at this parsing step, before source-host writes or
  the child importer; no query-shape or credential change is needed.
- Exercise marked lookup text with an existing source inventory, retained
  literal values, unrelated-host preservation and conflicting owner rejection.

### Verification

- The saved authenticated input from the failed deployment now passes the pure
  filter with native lookup wrappers. Focused Ansible producer and configuration
  tests, scoped strict lint, syntax and whitespace checks cover this correction.
  Controller operations remain substituted in fixtures. A normal AAP retry is
  still required to verify the live handoff.

## [1.6.0] — 2026-11-09

### Added

- Publish the authenticated Zabbix VM and observed gateway into the existing
  native source inventory, preserving unrelated variables and placement members.
  Run the existing CaC importer with its saved credentials, then reload the
  rendered host, protected runtime ciphertext and cached complete firewall policy
  before the existing grant transaction. No firewall lock is held during import.
- Keep the importer and firewall configuration inside the existing per-instance
  Zabbix VM definition. Native IDs come from the importer; no additional Job
  Template, publisher, credential type or state store is introduced.

### Verification

- Focused tests cover the data migration and planned VM projection, protected
  publication, selected native Controller sequence, importer failure and owner
  conflicts, refreshed runtime values and preserved explicit grant removal.
  Controller operations are substituted in orchestration fixtures. A normal
  fresh-clone AAP run remains required for live acceptance.
- On the combined source, three producer sequence fixtures, nine runtime/Vault
  tests and four Zabbix configuration/provenance tests pass. Matching importer
  checks cover 39 settings/publication and five native policy tests. Scoped
  strict production lint, deployment syntax and whitespace checks pass. Native
  Controller calls are substituted in producer fixtures; these results do not
  establish live AAP acceptance.
- Upgrade the matching AutoDeploy source, protected layout and all common-source
  pins together while affected jobs are stopped. Older readers cannot consume
  the nested VM configuration. Existing MCP and CloudCLI corrections are retained.

## [1.5.2] — 2026-11-09

### Fixed

- Use the pinned Linux MCP recipe's documented `BUILD_FROM_SOURCE=0` argument
  so dependencies may use wheels. The source-only build reached application
  installation but failed because a dependency required Rust 1.97 while the
  image supplied Rust 1.92. The application and container still build from the
  same pinned source on TRA; Zabbix's command, trusted downloads, protected
  failure logs and temporary-source cleanup are unchanged.
- Accept the two explicitly declared CloudCLI application accounts independently
  of the existing MCP transport account. Remove the unrelated membership check
  while retaining instance, account, private-listener and required-input checks.

### Verification

- Six native MCP build fixtures, ten CloudCLI fixtures and nine runtime/Vault
  checks passed on the combined source. Scoped strict production lint passed
  across five encountered files, retaining the existing local
  `community.general`/ansible-core compatibility warning. Combined-playbook
  syntax and diff checks passed. No real container build or application-service
  test ran during this local integration.

Live image-build/protocol and CloudCLI service acceptance remain pending.

## [1.5.1] — 2026-11-09

### Fixed

- Label only the job-created public MCP source checkout `container_file_t`
  before building. The actual enforcing SELinux AVC denied execution of the
  upstream script labeled `user_home_t`; its executable mode was already correct.
  Native file attributes preserve owners/modes and do not follow symlinks.
  Home/storage labels, enforcement, rootless builds and upstream recipes remain
  unchanged. A labeling failure stops before building and still cleans up.

### Verification

- Five native build fixtures, nine CloudCLI checks and nine runtime/Vault
  checks pass on the combined source. Scoped strict lint, combined-playbook
  syntax and diff checks pass. Fixtures verify exact labeling scope/order and
  failure cleanup without relabeling the operator host. Actual corrected
  image builds, private MCP use and CloudCLI runtime acceptance remain open.

## [1.5.0] — 2026-11-09

### Added

- Optional installation of one exact protected CloudCLI release for two local
  accounts through the existing Claude/MCP installer. Native account, npm and
  systemd tasks preserve separate workspaces, private listeners and explicitly
  selected service lifecycle settings; no new Job Template, proxy or DNS route.
- An account may receive its own captured Codex MCP connection without
  substituting the selected demo's AAP URL or token. A native private TOML
  template supports absent or exactly matching managed files; different content,
  links and foreign ownership are preserved and refused.

### Verification

- Nine native CloudCLI checks and nine runtime-loader checks pass, covering
  selected-account and input refusal, private service/environment rendering,
  standard-library TOML parsing, repeat idempotence and preservation failures.
  Syntax, compilation, whitespace and scoped strict lint checks pass. The local
  collection/core compatibility warning remains visible; declared-EE execution,
  package installation and authenticated browser/MCP/model acceptance are not
  established by these fixtures. Production installations remain unchanged.

## [1.4.1] — 2026-11-09

### Fixed

- Retrieve the reviewed private Hactar firewall source using its existing reader
  from the selected encrypted runtime settings. The previous unauthenticated
  checkout failed before policy changes. Authentication is scoped to that fixed
  repository in Git's process environment; source pins, TLS verification,
  redirect refusal and temporary checkout cleanup remain enforced.
- Focused native fixtures check private runtime delivery, Git header scoping,
  missing/multiline credential refusal and absence of secret output. Real v17
  source retrieval and monitoring/repair acceptance remain pending.

## [1.4.0] — 2026-11-09

### Changed

- Zabbix deployment consumes the reviewed native Hactar Ansible firewall tasks
  instead of the retired helper checks. It verifies complete CaC policy and
  saved guest ownership before adding only the declared bridge HTTPS permission
  through the certified firewall role and native nftables tasks.
- The existing temporary transaction lock, production exclusions, active and
  persistent isolation checks, exact-rule restoration and temporary-file cleanup
  are retained. No custom host JSON policy or new credential/job chain is added.
- Eight firewall orchestration fixtures and fifteen existing Zabbix regressions
  pass, together with scoped strict lint and syntax checks resolving the actual
  certified role. These are source/fixture results; live application and the
  outage/restore loop remain unverified. Fresh instances still need their
  verified owner and grant published in per-instance CaC before access is opened;
  an unattended fresh-instance producer remains unresolved.

## [1.3.1] — 2026-11-09

### Fixed

- Preserve failed container-build stdout and stderr in the selected runtime
  user's server `logs/build.log`, with directory mode `0700` and file mode
  `0600`, while retaining protected job logging and temporary-source cleanup.
  The job still fails; successful builds create no diagnostic file.
- Four native build fixtures pass, including failure output/mode/ownership,
  cleanup, successful builds and cache reuse. Strict scoped lint and combined
  playbook syntax pass. This diagnostic change does not fix or establish the
  cause of the observed live build failure.

## [1.3.0] — 2026-11-09

### Added

- Prepare the selected TRA's RHEL 9 registration and required BaseOS/AppStream
  repositories before MCP package installation, using protected per-instance
  RHSM inputs and certified RHEL System Roles 1.120.5. Preserve existing
  registration, unrelated repositories, Insights configuration and release pins.
- Load the existing whole-file runtime Vault in the standalone Linux MCP job,
  matching the other secret-dependent application jobs.

### Verification

- Three native subscription tests resolve the actual pinned role task entries,
  check registration/repository arguments and reject missing or mismatched inputs.
  Four target-build fixtures, eight runtime/Vault checks, strict production lint
  and combined-playbook syntax pass. No live registration, container build or
  complete repair result is claimed by this release.

## [1.2.0] — 2026-11-09

### Changed

- Build both MCP containers on the selected TRA from immutable public upstream
  revisions and their existing recipes. Native Ansible installs trusted RHEL
  runtime packages and prepares a temporary public-only build context.
- Reuse matching images through their standard OCI source-revision label.
  Preserve instance identity checks, private stdio transport, runtime accounts,
  protected configuration and authenticated read-only MCP checks.
- Remove the obsolete custom artifact validator and image/RPM staging requirement.
  Focused native build-decision, failure-cleanup and existing MCP tests pass;
  actual target builds and the complete repair demo remain unverified.

## [1.1.8] — 2026-11-08

### Fixed

- Require a fresh successful website HTTP sample from the selected Zabbix server
  before enabling event forwarding. Unsupported or unreachable checks stop
  deployment instead of treating configuration readback as monitoring readiness.
  Website and testserver polls use normal retry exhaustion, so an unsupported
  sample cannot be reported successful by an overriding failure expression.
  The existing exact guest-to-host HTTPS permission remains an operator-prepared
  recovery-policy prerequisite, not an automatic publisher.

## [1.1.7] — 2026-11-08

### Fixed

- Keep the monitoring frontend's existing DNS readiness check bounded while
  allowing the controlled zone's ten-minute negative cache to expire. Address,
  IPv6 and certificate checks stay unchanged; retry reuses the owned clone.

## [1.1.6] — 2026-11-04

### Changed

- Made **Ansible Automation Platform** the dominant 32 px bold platform title,
  with a prominent 20 px **TRUSTED EXECUTION LAYER** label alongside it.
  The other components retain their function-first hierarchy. Existing
  colors, connection paths, and walkthrough behavior are preserved.

## [1.1.5] — 2026-11-04

### Changed

- Renamed the failure step to **An error suddenly arises.** The existing Next
  arrow is retained, and the missing-Zabbix-agent example remains in the
  step explanation and technical detail.

## [1.1.4] — 2026-11-04

### Changed

- Made functionality the primary diagram label: **PROD SERVER**, **MONITORING**,
  **AGENTIC AI**, and **TRUSTED EXECUTION LAYER**. Product names are smaller
  secondary captions: Red Hat Enterprise Linux, Zabbix in this case, Claude
  in this case, and Ansible Automation Platform. Existing colors, architecture
  routes, controls, and monitoring-verification behavior are retained.

## [1.1.3] — 2026-11-04

### Changed

- Generalized the displayed AI runtime label to **Codex/Claude/Copilot etc**,
  split across two lines inside the existing agent node. Walkthrough narration
  describes the agent role; technical detail retains the actual Claude Code
  CLI launcher and does not imply new runtime integrations were implemented.

## [1.1.2] — 2026-11-04

### Changed

- Replaced the dominant red AAP header with deep navy and reduced red to a
  thin brand accent. The headline returns to dark ink. The user found the
  large red area visually harsh; blue/teal interactions and explicit
  incident-status colors are retained.

## [1.1.1] — 2026-11-04

### Changed

- Refined the walkthrough palette with fixed Red Hat red AAP branding, a
  dark navy platform, white surfaces, crisp blue interactions, and teal AI
  and execution accents. Dark crimson failures and green recovery remain
  labeled explicitly; brand color does not indicate incident state.
- Matched SVG arrows and path legends, increased muted-text contrast,
  and retained the existing recovery story, controls, and motion behavior.

## [1.1.0] — 2026-11-04

### Added

- A static interactive visualization of the existing missing-Zabbix-agent
  recovery scenario, with 17 presenter-paced stops, a persistent SVG architecture,
  all three MCP investigations, distinct reasoning and catalog discovery,
  AAP-only remediation execution, and subsequent monitoring confirmation.
- Keyboard and direct-step navigation, motion controls, reduced-motion support,
  responsive architecture scrolling, and source-linked technical detail.
- Built-in Node model checks and an allowlisted GitHub Pages workflow that
  validates pull requests and prepares publication from `main`.
- Presenter/publication documentation with explicit simulated-evidence and
  functionality-demo limitations. No live infrastructure configuration changes.

## [1.0.0] — 2026-10-05

First proven version: Zabbix-agent self-healing (Level 1), demonstrated
working end to end.

A package is removed from the managed host, breaking monitoring. Zabbix
detects agent unavailability and fires an alert through the Event-Driven
Ansible media type to an EDA Event Stream. The rulebook matches and
launches an AAP job template, which invokes Claude Code CLI headless. The
agent investigates through Phases 1–4 (Zabbix MCP → linux-mcp → AAP MCP),
identifies the missing package, and launches the **Deploy Zabbix Agent**
template through AAP MCP. Zabbix confirms recovery.

Includes the build guide (docs 00–06), troubleshooting, the EDA rulebook,
and the agent guardrails.
