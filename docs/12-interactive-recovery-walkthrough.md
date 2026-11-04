# Interactive recovery walkthrough

Version: **1.1.0**. This static presenter walkthrough illustrates the existing
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
**Technical detail** opens relevant Ansible/EDA excerpts or illustrations and
links to the complete repository source. Escape closes the dialog.

The continuous story has 17 stops: healthy baseline; package removal; Zabbix
detection; event delivery; EDA matching; the Controller investigation job; agent
startup; three separate MCP investigations; correlation and root cause;
catalog discovery; job launch request; AAP execution; job success with monitoring
still unresolved; monitoring confirmation; verified recovery.

**AAP is the Trusted Execution Layer.** AI investigates, reasons, discovers,
and selects. AAP executes changes through existing automation. Monitoring
confirms the result after the remediation job succeeds.

## What the diagram means

EDA is inside the AAP platform. An AAP job starts Claude Code CLI on its runtime
host. Every AI interaction with Zabbix, Linux, and AAP is drawn through the
corresponding MCP interface. Dashed blue paths are diagnostic requests and
responses. Purple paths request an AAP job. Event and job dispatch paths are
separate; the red execution path originates from Automation Controller and
terminates at the managed server.

The missing package is the injected demo failure, not an AI action. The server
can remain reachable while its monitoring agent is absent. Zabbix detection
follows its configured timeout, and its recovery follows a subsequent check;
the visualization does not promise any real elapsed time. Monitoring remains
red at the job-success stop. The verification stop includes fresh monitoring
checks and AI confirmation through Zabbix MCP and Linux MCP.

AAP supports RBAC, credential handling, job logging, and activity auditing.
Showing those capabilities does not establish that all possible controls are
configured in this demo. The actual launcher uses
`--dangerously-skip-permissions`; agent instructions prescribe AAP-only changes.
The repository documents remaining catalog-access and tool-restriction work.
This is a functionality demo, not an attestation of enforced isolation.

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
and GitHub Actions publishing pattern. This prepares publication; checking in
the workflow does not enable GitHub Pages in repository settings.

1. Merge the reviewed visualization changes into `main`.
2. In repository **Settings → Pages → Build and deployment**, select
   **GitHub Actions** as the source. Retain any repository/environment protection
   rules.
3. Run **Publish AIOps walkthrough** from Actions, or push a change to `demo/`.
4. Check that the validation and Pages deployment jobs both succeed. Use the
   deployment URL returned by the workflow.

Expected project-site URL after successful publication:
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
