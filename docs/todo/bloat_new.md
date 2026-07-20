# Bloat

Duplicated content, redundant sections, content that should be consolidated.

---

## 1. ✅ PAT creation duplicated (doc 01 + doc 04)

AAP OAuth2 Application and Personal Access Token creation is fully described in both doc 01 (section 6) and doc 04 (section 4). The two descriptions use different UI navigation paths (see inconsistencies_new.md #4). One should be canonical and the other should cross-reference.

## 2. ✅ linux-mcp config in two docs (doc 02 + doc 04) — NOT AN ISSUE

Both docs need the config block: doc 02 for setup and verification, doc 04 for the combined MCP wiring. The conflicting details were fixed in inconsistency #1.

## 3. ✅ Zabbix MCP config in two docs (doc 03 + doc 04) — NOT AN ISSUE

Same as #2. Doc 03 needs it for setup, doc 04 for the combined wiring.

## 4. Rulebook reproduced inline in doc 06

Doc 06 reproduces the full rulebook content that already exists at `extensions/eda/rulebooks/`. The inline copy has already drifted (see mistakes_new.md #1). Should reference the file, not duplicate it.

## 5. Playbook reproduced inline in doc 06

Doc 06 reproduces the playbook that already exists at `playbooks/run_claude_analyse_fix.yml`. Same drift risk.

## 6. Environment-specific values in doc 05

Doc 05 contains specific IPs, domains, GCP project IDs, and service account paths from the demo environment. These should be replaced with placeholders like the other docs use (`AAP_SERVER`, `TARGET_IP`, etc.).
