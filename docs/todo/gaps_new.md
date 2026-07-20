# Gaps

Missing content, broken references, undocumented divergences.

---

## 1. ✅ README repository layout is wrong

The `Repository layout` section in the README claims directories that don't exist and omits ones that do.

| README claims | Actual |
|---------------|--------|
| `docs/build/` — "sequential reimplementation guide" | Does not exist. The build docs live directly in `docs/` (00 through 06) |
| `rulebooks/` — "EDA rulebooks" | Does not exist. Actual path is `extensions/eda/rulebooks/` |
| `config/` — "sanitized reference configuration" | Does not exist |
| — | `AI_Instructions_Guardrails/` exists, not listed |
| — | `docs/todo/` exists, not listed |
| — | `docs/troubleshooting.md` exists, not listed |

## 2. ✅ CLAUDE.md: repo version never referenced from docs — fixed in inconsistency #10

`AI_Instructions_Guardrails/CLAUDE.md` is the refined, battle-tested agent instruction file (~90 lines, 6 sections including phase discipline, SSH alias rules, RHEL prerequisites, memory hygiene). Doc 04 section 6 contains a separate simplified template (~30 lines, 4 sections) and says "This is a starting point" but never mentions that a refined version exists in the repo. The reader doesn't know to look for it.

## 3. ✅ Incident memory MCP still in architecture diagram

The README architecture diagram still shows `MEM[(Incident memory<br>MCP)]` connected to Claude Code with a bidirectional arrow. This was removed from docs and config in gap 7 of the previous round, but the diagram was not updated. The component doesn't exist.

## 4. ✅ No cross-reference from doc 06 to actual rulebook file

Doc 06 reproduces the rulebook inline (and it has already drifted — see inconsistencies #2). It never references `extensions/eda/rulebooks/` as the canonical source, so the reader has no way to find the actual deployed file.

## 5. ✅ No cross-reference from doc 06 to actual playbook file

Same problem: doc 06 reproduces the playbook inline but doesn't reference `playbooks/run_claude_analyse_fix.yml`. The inline copy will continue to drift.

## 6. Doc 04 section 9 references "a later section" without a link

"The exact EDA-to-agent integration (rulebook, webhook handler, alert payload format) is covered in a later section." — no link to doc 06. The reader doesn't know which section.

## 7. Doc 04 CLAUDE.md template lacks verification steps

The template in doc 04 section 6 includes a "Remediation procedure" that says to identify and launch the right template, but doesn't include the verification steps we added to it (review past job runs, read playbook source, clone repo). The actual `AI_Instructions_Guardrails/CLAUDE.md` has phase discipline with verification built in, but the doc 04 template doesn't reflect any of this.

## 8. Playbook lacks --max-turns safety limit

The actual `playbooks/run_claude_analyse_fix.yml` doesn't use `--max-turns`. Doc 04 section 9 recommends `--max-turns 25`, and the CLAUDE.md has a 2-cycle loop limit, but the playbook itself has no turn cap — meaning a misbehaving agent could run indefinitely.
