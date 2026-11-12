# Interactive recovery walkthrough

**[Open the interactive AIOps visualization](https://kvegh.github.io/aiops-selfhealing-demo/)**

Version: **1.6.7**. This static presenter walkthrough illustrates the existing
missing-`zabbix-agent2` recovery scenario. It is separate from the live audience
website and makes no infrastructure connections. All findings, status changes,
and timing are simulated; a successful walkthrough is not live recovery proof.

## Present it

Open `demo/index.html` directly, or serve only the frontend:

```sh
python3 -m http.server 8080 --directory demo
```

Use **Next**, **Previous**, **Restart**, or select a step in the story. Keyboard
shortcuts: left/right arrows, Home/End, and R to restart. The presenter chooses
when each step advances; there is no autoplay. **Motion on/off** controls finite
flow animations. Reduced-motion preferences default to motion off. On narrow
screens, the architecture scrolls sideways so its text remains legible.
**Technical detail** opens relevant Ansible/EDA excerpts or illustrations, the
current diagnostic evidence, and links to complete repository source. Escape
closes the dialog.

At **Rule condition matched** and **Correlating three sources**, a tinted
status band, bold label and stronger component outline draw attention to the
transition. A single 0.9-second border emphasis settles into that static cue.
The cue stays visible while paused; **Motion off** suppresses animation, and
reduced-motion preferences keep their existing motion-off default. Leaving
the relevant step removes its cue; revisiting the step replays the emphasis.

On viewports at least 1100 CSS pixels wide and 650 high, the current-step
explanation sits above the workflow in the left column. **Previous** and
**Next** sit in the architecture header, with **Next** immediately to the left
of **Motion on/off**. On narrow screens the heading wraps above these controls.
The architecture uses the remaining viewport height in the right column; its SVG
keeps its aspect ratio and includes the complete AAP platform. The workflow
and unusually long explanations scroll within their own space. Narrow or
short windows retain the naturally scrolling page and horizontal diagram
panning. No body-overflow clipping or forced fullscreen mode is used.

The continuous story has 17 stops: healthy baseline; “An error suddenly arises.”
(the missing agent package); Zabbix
detection; event delivery; EDA matching; the Controller investigation job; agent
startup; three separate MCP investigations; correlation and root cause;
catalog discovery; job launch request; AAP execution; job success with monitoring
still unresolved; monitoring confirmation; verified recovery.

**AAP is the Trusted Execution Layer.** AI investigates, reasons, discovers,
and selects. AAP executes changes through existing automation. Monitoring
confirms the result after the remediation job succeeds.

## What the diagram means

**Ansible Automation Platform** is the dominant platform name, using bold
32 px SVG text with a 20 px **TRUSTED EXECUTION LAYER** label alongside it.
The title has a bounded width so job-dispatch and MCP paths remain clear.
The other components keep functionality as the primary label: **PROD SERVER**,
**MONITORING**, and **AGENTIC AI**, using 22 px headings with 11–13 px product
captions: Red Hat Enterprise Linux, Zabbix in this case, and Claude in this case.

EDA is inside the AAP platform. An AAP job starts the AI agent runtime. The
current repository implementation still launches Claude Code CLI; Codex,
Copilot, and other runtimes remain examples of the broader role, not
additional implemented integrations. Technical excerpts and source links retain
the real launcher and job-template names. Every AI interaction with Zabbix,
Linux, and AAP is drawn through the
corresponding MCP interface. Dashed blue paths are diagnostic requests and
responses. Purple paths request an AAP job. Event and job dispatch paths are
separate; the teal execution path originates from Automation Controller and
terminates at the managed server.

The missing package is the injected demo failure, not an AI action. The server
can remain reachable while its monitoring agent is absent. Zabbix detection
follows its configured timeout, and its recovery follows a subsequent check;
the visualization does not promise any real elapsed time. Monitoring remains
red at the job-success stop. The verification stop includes fresh monitoring
checks and AI confirmation through Zabbix MCP and Linux MCP.

AAP supports RBAC, credential handling, job logging, and activity auditing.
Showing those capabilities does not establish that all possible controls are
configured in this demo. The maintained launcher uses native permissions,
read-only diagnostic tools and an invocation-only deny hook restricting changes
to the selected saved AAP repair. It verifies native child-job success and fresh
monitoring recovery. The API token retains its configured AAP permissions;
client-side restrictions do not establish narrower server-side RBAC.

Source references:

- [EDA event matching and job launch](../extensions/eda/rulebooks/zabbix-webhook.yml)
- [AAP job that starts Claude Code CLI](../playbooks/run_claude_analyse_fix.yml)
- [Existing agent remediation](../playbooks/deploy_zabbix_agent.yml)
- [Agent investigation instructions](../AI_Instructions_Guardrails/CLAUDE.md)
- [MCP deployment and verification](10-mcp-deployment.md)
- [Event Stream integration](06-eda-zabbix-integration.md)
- [Documented hardening work](todo/demo-design.md)

The frontend contains only this recovery story. It has no infrastructure
credentials, live MCP connections, alternative response levels, content
generation, incident memory, ITSM, or audience website controls.

## Color and status

AAP uses a slate-blue header, pale blue platform, and light internal panels
with a thin Red Hat red (`#ee0000`) brand accent. The headline remains dark; red is limited to small fixed brand
details rather than large surfaces. Brand color does not change with the
incident state. White surfaces and crisp
blue interactions keep the presentation light. The AI runtime uses a quiet
slate-grey surface (`#eef2f6`), border/constellation (`#94a3b8`) and dark slate
text (`#334155`). Its active and reasoning cues use muted steel blue, including
the diagnostic strip, leaving AAP more visually prominent. Teal identifies
the labeled AAP execution path and EDA rule-match cue. Diagnostic paths are dashed blue, job
requests are solid purple, and event/job dispatch is slate.

Failure uses darker crimson with explicit Problem text, while recovery uses
green with explicit Recovered text. The monitoring status stays unresolved
until verification. These labels, route captions, dash patterns and line widths
carry meaning alongside color. The Red Hat accent follows its
[official brand color reference](https://www.redhat.com/en/about/brand/standards/color);
this visualization retains its original red/green monitoring story and does
not claim to be an official Red Hat product interface.

## Validate it

No build tool, package installation, or network connection is needed for the
frontend or its model checks. Use an already installed Node.js runtime with the
built-in test runner:

```sh
node --check demo/src/scenario.js
node --check demo/src/app.js
node --test demo/tests/*.test.cjs
```

The tests cover event/job ordering, all three MCP investigations, the reasoning
boundary, AAP-originated execution, distinct job-success and monitoring recovery,
rewind/restart, source-file availability, and local runtime dependencies.
A minimal DOM harness also exercises the actual application handlers, dialogs,
rapid navigation, keyboard navigation, deep links, and reduced-motion defaults.
It does not verify layout or replace rendered browser inspection.
Browser validation should also cover the entire story, every detail dialog,
keyboard controls, rapid navigation, reduced motion, and desktop/mobile layouts.

## Publish with GitHub Pages

At inspection, this repository had no configured Pages site or Pages workflow.
The implementation follows the existing Windows walkthrough's buildless folder
and GitHub Actions publishing pattern. Pages was subsequently enabled with
GitHub Actions as the build source. The deployment at `777ec46` succeeded on
2026-11-04 after the initially missing Pages setting was configured; the public
HTML returned HTTP 200 and matched the committed frontend byte for byte.
[Open the published visualization](https://kvegh.github.io/aiops-selfhealing-demo/).

For future updates or recreation:

1. Merge the reviewed visualization changes into `main`.
2. In repository **Settings → Pages → Build and deployment**, select
   **GitHub Actions** as the source. Retain any repository/environment protection
   rules.
3. Run **Publish AIOps walkthrough** from Actions, or push a change to `demo/`.
4. Check that the validation and Pages deployment jobs both succeed. Use the
   deployment URL returned by the workflow.

Published project-site URL:
<https://kvegh.github.io/aiops-selfhealing-demo/>.

The workflow stages an explicit allowlist: `index.html`, `icon.svg`, the three
runtime JS/CSS files, and `.nojekyll`. It never uploads the repository root,
playbooks, Vault files, tests, or runtime configuration. Pull requests run the
model checks without deploying. The browser frontend requires no secrets.

Reference presentation and source:
[Windows + AAP walkthrough](https://kvegh.github.io/disconnected-windows-patching/demo-with-aap/)
and its [repository](https://github.com/kvegh/disconnected-windows-patching).
The [GitHub Pages workflow guide](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
describes the publishing actions and required permissions.

## Validation outcome

All 14 model and application-handler tests passed locally and in GitHub Actions.
The user declined installing Chromium on the server. Playwright's temporary QA
library was installed with approval, but no browser was installed or run.
Rendered desktop/mobile layout and real-browser accessibility behavior remain
unverified; the minimal DOM harness is an interaction check only.

For release 1.6.4, the user requested publication with the existing checks.
No additional browser-test job or dependency was added. The 14 existing
model/application-handler tests and text-contrast checks pass; rendered
laptop/desktop fit and real-browser accessibility remain unverified.

Release 1.6.5 keeps that layout and palette, and restores navigation to the
right-hand architecture header, immediately before the motion control, following
the user’s manual feedback. Browser verification remains unperformed.

Release 1.6.6 adds the two status highlights with SVG/CSS and existing step
state, without changing runtime JavaScript or adding dependencies. Existing
model/handler checks do not establish rendered animation or layout behavior.

Release 1.6.7 replaces AI-specific green styling with the approved neutral
slate/steel-blue palette, including glow, status band and finite animations.
EDA and AAP execution colours and the walkthrough layout remain unchanged.
Browser-rendered colour balance remains unverified.
