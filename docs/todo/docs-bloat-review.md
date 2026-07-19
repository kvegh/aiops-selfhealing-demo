# Docs Bloat Review — aiops-selfhealing-demo

Suggestions for trimming without losing technical content. Per-file, with quoted originals and tighter replacements.

---

## README.md — Significant bloat

The main issue: the same architectural constraint ("AI reads, AAP writes") is stated ~5 times in different registers, and two "Management summary" blocks are corporate-speak. Estimated cut: ~40% of prose, zero technical content lost.

### R1. "What this is" — over-written ✅ kept as-is (emphasis preferred)

**Current:**
> "A reproducible demo in which infrastructure incidents are detected, diagnosed, and remediated automatically — including incidents nobody wrote a runbook for. An AI agent investigates the unknown cases and resolves them, yet at no point holds the ability to change systems directly: every change, without exception, runs through the organization's governed automation platform."

**Tighter:**
> "A reproducible demo: infrastructure incidents are detected, diagnosed, and remediated automatically -- including ones nobody wrote a runbook for. The AI agent investigates and resolves, but every change runs through the governed automation platform. Never directly."

### R2. "Four response levels" intro — repeats core idea ✅ rewritten with level summary list

**Current:**
> "Every incident is handled at the lowest level capable of resolving it. Each level up grants the responding system more autonomy — and pays for it with more scrutiny. Where an incident lands is not a runtime decision made on a whim; it is defined by policy and enforced by architecture."

**Tighter:**
> "Each level up grants more autonomy and more scrutiny. Routing is defined by policy and enforced by architecture."

(First sentence is already stated verbatim earlier.)

### R3. Level 0 — over-explained ✅ trimmed, added EDA/AAP context

**Current:**
> "The incident matches a documented pattern in the knowledge base. A predefined remediation template executes deterministically — no intelligence involved, none needed. This is the operational runbook, executed by the automation platform instead of a person: identical response, every time, fully audited. If the fix does not clear the issue, the re-fired event escalates automatically to Level 1."

**Tighter:**
> "The incident matches a documented pattern. A predefined remediation template executes deterministically -- fully audited, no AI involved. If the fix doesn't clear the issue, escalation to Level 1 is automatic."

### R4. Level 1 — last two sentences say the same thing ✅ kept first, dropped second, reworded

**Current:**
> "The agent reasons freely, but acts only within the sanctioned repertoire. Diagnosis is creative; execution never is."

**Tighter:** Pick one. The second is punchier — delete the first.

### R5. Level 2 — padded ✅ trimmed analogy and redundant phrasing

**Current:**
> "An independent second agent instance reviews the proposal for sanity and policy compliance before it may enter the catalog, mirroring the author/reviewer separation of established code review practice. Whether machine review is sufficient here, or whether this level always requires a human gate, is an open question this project deliberately leaves open."

**Tighter:**
> "An independent second agent reviews for sanity and policy compliance before the proposal enters the catalog. Whether machine review suffices or a human gate is always required is an open question."

### R6. First management summary — delete or collapse ✅ kept, reworded autonomy sentence

**Current (full paragraph):**
> "**Management summary.** The bulk of incidents resolve at Level 0 — machine-speed, audit-grade, with no one paged at 3 a.m. The AI agent absorbs the long tail of unknowns at Level 1, working exclusively through the automation platform the organization already owns and governs — existing investment, extended rather than replaced. Escalations that do reach engineers arrive pre-analyzed, cutting time-to-resolution where expert time is scarcest. Autonomy grows only where control grows with it: every action, at every level, runs through the same governed, auditable execution path."

**Suggestion:** Delete entirely, or collapse to one sentence:
> "Most incidents resolve at Level 0 with no one paged. The AI handles the long tail through the automation platform the org already governs."

### R7. Guiding principles — 60% redundant with levels section ✅ deleted bullets 2 and 5, kept bullet 1 as-is

**Delete these two bullets entirely** (already said above):

> "**The AI agent changes nothing.** It analyses, correlates, summarizes — and requests fixes through the Trusted Execution Layer."

> "**Monitoring may trigger automation jobs directly** when an issue is well known and documented. Otherwise it triggers the AI agent to analyse the situation."

**Trim this one:**

Current:
> "**The automation platform is strictly the only component that changes configurations or executes jobs.** It is the **Trusted Execution Layer**. LLMs are exceptionally creative — and exactly for that reason not reliable enough to follow operational policy unconditionally. Creativity belongs in diagnosis, never in execution."

Tighter:
> "**The automation platform is the only component that changes state.** It is the Trusted Execution Layer."

### R8. Second management summary — delete ✅ kept as-is

> "**Management summary.** Control is not a promise made by the AI — it is a property of the architecture. The single governed execution path preserves every existing approval, audit, and compliance mechanism the organization already relies on. Adopting AI-driven operations this way carries no new class of privileged actor: the platform you already trust remains the only thing touching your systems."

Delete entirely. If you want to keep the first sentence, fold it into the architecture diagram caption as a one-liner.

### R9. Architecture diagram caption — trim throat-clearing ✅ trimmed

Current:
> "The critical property is visible in the diagram: **every arrow that changes state — on the managed server and in the ITSM system — originates from the Trusted Execution Layer.** The AI agent has no direct write path anywhere."

Tighter:
> "**Every arrow that changes state originates from the Trusted Execution Layer.** The AI agent has no direct write path anywhere."

---

## docs/00-starting-setup.md — Nearly clean

### S0-1. Opening paragraph ✅ trimmed

Current:
> "This document defines the baseline environment assumed by this demo. Everything in this document is a **prerequisite** — its installation is out of scope. The build guide starts from this state."

Tighter:
> "Baseline environment — all of this is a **prerequisite**. The build guide starts from this state."

---

## docs/01-aap-mcp.md — Three small trims

### S1-1. "sole write path" said twice

The intro says it, then the variable explanation repeats it. Trim the variable section to:
> "`mcp_allow_write_operations=true` — grants read-write access (launch job templates, create resources). The other MCP servers are read-only."

### S1-2. Idempotency over-explained

Current:
> "The installer is idempotent — re-running it against an existing deployment adds the MCP container without touching the rest of the stack."

Tighter:
> "The installer is idempotent — it adds the MCP container without touching the existing stack."

### S1-3. CA trust section — restructure

Current:
> "Copy the CA certificate — **not** the server cert from the TLS handshake, which does not include the signing CA — from the AAP host to the client VM:"

Tighter:
> "Copy the **CA certificate** (not the server cert) from the AAP host to the TRA VM:"

Move the diagnostic detail ("the TLS handshake does not include the signing CA") to a note below the command block if you want to keep it.

---

## docs/02-linux-mcp.md — Most bloat, ~25-30 lines removable

### S2-1. Intro paragraph 2 — delete

> "The server runs as a container on the TRA VM — the same host where Claude Code CLI runs — so the connection is a local stdio pipe, no network listener required."

Already covered by paragraph 1 ("MCP stdio transport") and doc 00. Delete.

### S2-2. Prerequisites section — delete entirely

Nearly verbatim repeat of the Environment section above it. Keep Environment, drop Prerequisites.

### S2-3. "no sudo" stated three times — keep once

Appears in: Environment, Target host preparation intro, and Out of scope. Keep it in Environment only, delete from the other two.

### S2-4. "Why an SSH config is needed" section — delete

Near-duplicate of Section 1 intro. Fold the one new detail (container detects containerization and refuses local execution) into Section 1:

> "The linux-mcp server runs inside a container — it detects this and refuses local execution, so all inspection happens over SSH. The container needs an SSH config to map hostnames to connection parameters."

Delete the entire end-of-file "Why an SSH config is needed" section.

### S2-5. Redundant mount explanation

Lines 117-118 explain what the `-v ~/.ssh` mount does, then the flags table says the same thing. Delete lines 117-118.

### S2-6. Obvious stdio note — trim

Current:
> "Claude Code launches the container automatically at startup via the stdio transport — no manual `podman run` needed."

Tighter:
> "Claude Code launches the container automatically at startup."

### S2-7. Target host preparation intro — delete preamble

Lines 34-37 are two sentences saying "no sudo needed" (already covered) before the actual actionable content. Delete them; the actionable intro "For full diagnostic access, the `mcp` user needs:" already exists at line 38.

---

## docs/03-zabbix-mcp.md — Very clean, three minor trims

### S3-1. Section 6 intro sentence — delete

> "The Zabbix MCP entry uses the same pattern as linux-mcp — Claude Code launches the container as a subprocess and communicates over stdio."

Already said in the intro. Just delete.

### S3-2. SELinux reminder — shorten

Current:
> "**No `:Z` flag** on the volume mount — the SELinux label was set in step 4. Using `:Z` here would fail for non-root users."

Tighter:
> **No `:Z` flag** — the SELinux label was set in step 4.

### S3-3. Tool filtering note — trim redundancy

Current:
> "**Tool filtering:** The `tools` list limits the tool catalog to the categories needed for incident diagnosis. Add more prefixes as needed (e.g. `"template"`, `"maintenance"`)."

Tighter:
> **Tool filtering:** Add more prefixes as needed (e.g. `"template"`, `"maintenance"`).

---

## docs/04-claude-agent.md — ~30% wordier than needed

### S4-1. Section 4 trailing paragraph — trim

Current:
> "The token is bound to the user that is logged in when it is created. That user's RBAC permissions determine what the MCP server can do — ensure the user has permission to launch the relevant job templates.
>
> Store the token securely. You will reference it in the Claude Code configuration on the TRA VM in the next step."

Tighter:
> The token inherits the creating user's RBAC permissions — ensure that user can launch the relevant job templates.

Delete "Store the token securely" and "You will reference it in the next step" — both obvious.

### S4-2. AAP config shown twice — deduplicate

The AAP MCP JSON block appears standalone, then again inside the full config ~13 lines later. Delete the standalone block, show the full combined config once with intro:

> "Add all MCP servers to `~/.claude.json` under `mcpServers` (if the file doesn't exist, `claude mcp add` creates it):"

### S4-3. Section 5 intro — trim

Current:
> "Claude Code reads MCP configuration from `~/.claude.json`. The AAP MCP server uses Streamable HTTP transport with Bearer token authentication.
>
> Edit `~/.claude.json` and add the AAP MCP entry under your project's `mcpServers` section. If the file does not exist yet, running `claude mcp add` once will create it (see alternative below)."

Tighter:
> Add all MCP servers to `~/.claude.json` under `mcpServers` (if the file doesn't exist, `claude mcp add` creates it):

Transport and auth type are visible in the JSON itself.

### S4-4. Placeholder list — wrong values mentioned

Current:
> "Replace the placeholder values (`AAP_SERVER`, `YOUR_AAP_TOKEN`, `TARGET_IP`, `ZABBIX_SERVER`, `ZABBIX_TOKEN`) with your environment."

`ZABBIX_SERVER` and `ZABBIX_TOKEN` don't appear in this config block. Fix to:
> Replace `AAP_SERVER`, `YOUR_AAP_TOKEN`, and `TARGET_IP` with your environment values.

### S4-5. Section 6 intro — redundant second sentence

Current:
> "Claude Code reads `CLAUDE.md` from the working directory on every invocation. This file defines the agent's role, constraints, and operating procedures."

Tighter:
> Claude Code reads `CLAUDE.md` from the working directory on every invocation.

### S4-6. Tuning note — delete

> "**Tuning:** This is a starting point. Refine the instructions based on observed agent behavior during testing."

Says nothing actionable. Delete.

### S4-7. Section 7 intro — trim -p explanation

Current:
> "Claude Code runs headlessly with `--print` (`-p`) mode: it reads a prompt from the command line, executes the task, prints the result, and exits. No interactive terminal required."

Tighter:
> For headless execution, use `--print` (`-p`) mode — no interactive terminal required.

### S4-8. Section 2 — over-explains why a directory exists

Current:
> "Create a dedicated directory for the agent. Claude Code reads its configuration (MCP connections, instructions, tool policy) from the working directory it is launched in."

Tighter:
> Create a dedicated directory for the agent. Claude Code loads configuration from the working directory.

---

## docs/05-cloudcli-web-ui.md — Already lean, three minor trims

### S5-1. Intro — "mobile" said twice

Current:
> "...making agent sessions viewable and drivable from a browser — including mobile. ... interactive sessions from a phone, and live streaming of headless (EDA-triggered) Claude runs during demos."

Tighter:
> "Optional web frontend for Claude Code. The self-healing pipeline works without it -- CloudCLI adds browser/mobile access to agent sessions and live streaming of headless runs during demos."

### S5-2. "Headless runs stream live" — said in intro AND section 5

Keep the section 5 version (it's more complete), drop the duplicate from the intro.

### S5-3. npm audit note — trim risk-acceptance filler

Current:
> "most sit in dev-only dependencies not present in a production install (`npm audit --omit=dev` gives the relevant picture). Accepted for this environment: internal network, on-demand runtime, unprivileged user on a VM."

Tighter:
> "`npm audit` reports vulnerabilities in the dependency tree; `npm audit --omit=dev` shows the relevant picture (most are dev-only)."

---

## docs/06-eda-zabbix-integration.md — Solid, minor trims

### S6-1. AAP 2.7 paragraph — "authenticated" said twice

Current:
> "AAP 2.7 uses **Event Streams** -- managed, token-authenticated endpoints that replace raw `ansible.eda.webhook` port listeners. Event Streams provide credential-based authentication and a gateway-managed URL, so no extra ports need to be exposed."

Tighter:
> "AAP 2.7 uses **Event Streams** -- authenticated, gateway-managed endpoints that replace raw `ansible.eda.webhook` port listeners. No extra ports need to be exposed."

### S6-2. Delete four lead-in sentences that restate headings

These one-liners before steps 2, 3, 5, and 6 add nothing — the heading and the table/procedure that follow are self-explanatory:

- Step 2: "The Event Stream credential defines how external systems (Zabbix) authenticate when sending events." — delete
- Step 3: "The Event Stream provides the authenticated webhook URL that Zabbix will POST alerts to." — delete
- Step 5: "This credential lets EDA connect to Controller to launch job templates." — delete
- Step 6: "The activation binds the rulebook to the Event Stream and starts listening for events." — delete

### S6-3. Step 8 intro — trim

Current:
> "In production, create a dedicated Zabbix user for EDA notifications with minimal permissions (read access to the relevant host groups). In demo environments, an existing user with the required permissions can be reused."

Tighter:
> "Use a dedicated Zabbix user for EDA (minimal permissions: read access on the relevant host groups). In demo setups, any user with those permissions works."

### S6-4. "One user is enough" note — trim history

Current:
> "The Zabbix documentation for the old `ansible.eda.webhook` approach says to create a separate user per rulebook (because each rulebook listens on a different port). With Event Streams this does not apply -- the gateway routes by the UUID in the URL, not by port. A single user can have multiple media entries pointing to different Event Stream URLs if needed."

Tighter:
> "The old `ansible.eda.webhook` docs say one user per rulebook (different ports). With Event Streams this doesn't apply -- routing is by UUID, not port. One user with multiple media entries is fine."
