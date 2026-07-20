# Bloat

Duplicated content, redundant sections, content that should be consolidated.

---

## 1. ✅ PAT creation duplicated (doc 01 + doc 04)

AAP OAuth2 Application and Personal Access Token creation is fully described in both doc 01 (section 6) and doc 04 (section 4). The two descriptions use different UI navigation paths (see inconsistencies_new.md #4). One should be canonical and the other should cross-reference.

## 2. linux-mcp config in two docs with conflicting details (doc 02 + doc 04)

Doc 02 is the dedicated linux-mcp setup doc. Doc 04 section 5 reproduces a full linux-mcp config block — but with a different container image, different argument style, and different paths (see inconsistencies_new.md #1). The canonical config should live in doc 02 only; doc 04 should reference it.

## 3. Zabbix MCP config in two docs (doc 03 + doc 04)

Doc 03 is the dedicated Zabbix MCP setup doc. Doc 04 section 5 reproduces the Zabbix MCP config block. Same duplication risk as linux-mcp.

## 4. Rulebook reproduced inline in doc 06

Doc 06 reproduces the full rulebook content that already exists at `extensions/eda/rulebooks/`. The inline copy has already drifted (see mistakes_new.md #1). Should reference the file, not duplicate it.

## 5. Playbook reproduced inline in doc 06

Doc 06 reproduces the playbook that already exists at `playbooks/run_claude_analyse_fix.yml`. Same drift risk.

## 6. Environment-specific values in doc 05

Doc 05 contains specific IPs, domains, GCP project IDs, and service account paths from the demo environment. These should be replaced with placeholders like the other docs use (`AAP_SERVER`, `TARGET_IP`, etc.).
