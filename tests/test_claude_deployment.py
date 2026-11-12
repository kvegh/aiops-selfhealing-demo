"""Check native Claude release boundaries and the actual download/cleanup tasks."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile
import unittest

import yaml
from ansible.errors import AnsibleFilterError


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("claude_deployment_filters", ROOT / "playbooks/filter_plugins/demo_claude.py")
FILTERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FILTERS)
MCP_SPEC = importlib.util.spec_from_file_location("claude_workspace_filters", ROOT / "playbooks/filter_plugins/demo_mcp.py")
MCP = importlib.util.module_from_spec(MCP_SPEC)
MCP_SPEC.loader.exec_module(MCP)


class LiteralText(str):
    """Synthetic data explicitly kept literal by the native YAML loader."""


class LiteralDumper(yaml.SafeDumper):
    pass


LiteralDumper.add_representer(LiteralText,
    lambda dumper, value: dumper.represent_scalar("!unsafe", str(value)))


def literal_values(value):
    if isinstance(value, dict):
        return {str(key): literal_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [literal_values(item) for item in value]
    return LiteralText(value) if isinstance(value, str) else value


def release():
    return {"version": "2.1.316", "platform": "linux-x64", "sha256": "a" * 64, "bytes": 4096,
            "url": "https://downloads.claude.ai/claude-code-releases/2.1.316/linux-x64/claude"}


def vertex():
    return {"project_id": "synthetic-project", "region": "global", "adc": {
        "type": "authorized_user", "client_id": "synthetic-client", "client_secret": "synthetic-private-secret-{{ forbidden_expression }}",
        "refresh_token": "synthetic-private-refresh", "quota_project_id": "synthetic-quota",
        "universe_domain": "googleapis.com", "account": "",
    }}


class ClaudeReleaseTests(unittest.TestCase):
    def test_exact_native_release_is_selected(self):
        self.assertEqual(FILTERS.release(release()), release())

    def test_moving_or_noncanonical_versions_are_refused(self):
        for version in ("latest", "stable", "2.1", "02.1.3", "2.01.3", "2.1.03", "2.1.3/other", 2):
            data = release(); data["version"] = version
            with self.subTest(version=version), self.assertRaises(AnsibleFilterError):
                FILTERS.release(data)

    def test_other_hosts_protocols_platforms_and_paths_are_refused(self):
        for key, value in (("url", "http://downloads.claude.ai/claude-code-releases/2.1.316/linux-x64/claude"),
                           ("url", "https://other.example.com/claude"), ("platform", "linux-arm64"),
                           ("url", release()["url"] + "?redirect=other"),
                           ("url", release()["url"].replace("2.1.316", "2.1.315"))):
            data = release(); data[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AnsibleFilterError):
                FILTERS.release(data)

    def test_missing_checksums_and_invalid_sizes_are_refused(self):
        for key, value in (("sha256", ""), ("sha256", "A" * 64), ("bytes", 0), ("bytes", True),
                           ("bytes", "4096"), ("bytes", 2 ** 30 + 1)):
            data = release(); data[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(AnsibleFilterError):
                FILTERS.release(data)

    def test_absent_or_exact_root_owned_command_is_safe(self):
        self.assertTrue(FILTERS.existing_program({"exists": False}, release()))
        stat = {"exists": True, "isreg": True, "islnk": False, "uid": 0, "mode": "0755",
                "checksum": "a" * 64, "size": 4096}
        self.assertTrue(FILTERS.existing_program(stat, release()))

    def test_unrelated_drifted_or_user_owned_command_is_preserved(self):
        baseline = {"exists": True, "isreg": True, "islnk": False, "uid": 0, "mode": "0755",
                    "checksum": "a" * 64, "size": 4096}
        for key, value in (("islnk", True), ("isreg", False), ("uid", 1000), ("mode", "0777"),
                           ("checksum", "b" * 64), ("size", 4095)):
            data = dict(baseline, **{key: value})
            with self.subTest(key=key), self.assertRaises(AnsibleFilterError):
                FILTERS.existing_program(data, release())


class NativeDownloadTests(unittest.TestCase):
    def test_actual_native_tasks_require_hash_and_size_before_managed_writes_and_always_clean_up(self):
        play = yaml.safe_load((ROOT / "playbooks/deploy_claude.yml").read_text())[0]
        deployment = play["tasks"][0]
        selected = [copy.deepcopy(task) for task in deployment["block"] if task["name"] in (
            "Allocate a private execution-environment download directory",
            "Download the exact native binary in AAP with trusted HTTPS",
            "Check binary size and SHA-256 before any managed write")]
        self.assertEqual(len(selected), 3)
        cleanup = copy.deepcopy(deployment["always"][0])
        with tempfile.TemporaryDirectory(prefix="claude-native-download-") as temporary:
            directory = Path(temporary)
            payload = directory / "synthetic-native-program"; payload.write_bytes(b"synthetic program, not executable\n")
            digest = hashlib.sha256(payload.read_bytes()).hexdigest()
            for native in ("false", "true"):
                for failure in ("none", "size", "checksum", "download"):
                    case = directory / (native + "-" + failure); case.mkdir()
                    tasks = copy.deepcopy(selected)
                    tasks[0]["ansible.builtin.tempfile"]["path"] = str(case)
                    marker = case / "managed-write"
                    pin = {"url": payload.as_uri(), "sha256": digest, "bytes": payload.stat().st_size}
                    if failure == "size": pin["bytes"] += 1
                    if failure == "checksum": pin["sha256"] = "f" * 64
                    if failure == "download": pin["url"] = (directory / "missing").as_uri()
                    fixture = case / "play.yml"
                    fixture.write_text(yaml.safe_dump([{
                        "hosts": "localhost", "connection": "local", "gather_facts": False,
                        "vars": {"demo_claude_pin": pin}, "tasks": [{
                            "name": "Exercise actual native download boundaries",
                            "block": tasks + [{"name": "Write only after native integrity checks",
                                               "ansible.builtin.copy": {"dest": str(marker), "content": "verified", "mode": "0600"}}],
                            "always": [cleanup],
                        }],
                    }], sort_keys=False))
                    environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(case / "local"),
                                       ANSIBLE_REMOTE_TEMP=str(case / "remote"), ANSIBLE_JINJA2_NATIVE=native,
                                       ANSIBLE_NOCOLOR="1")
                    result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                                            env=environment, capture_output=True, text=True, timeout=60)
                    with self.subTest(native=native, failure=failure):
                        self.assertEqual(result.returncode == 0, failure == "none", result.stdout + result.stderr)
                        self.assertEqual(marker.exists(), failure == "none")
                        self.assertEqual(list(case.glob("aiops-claude-*")), [])

    def test_entry_point_reuses_both_existing_mcp_playbooks(self):
        plays = yaml.safe_load((ROOT / "playbooks/deploy_claude.yml").read_text())
        imports = [p["ansible.builtin.import_playbook"] for p in plays if "ansible.builtin.import_playbook" in p]
        self.assertEqual(imports, ["deploy_linux_mcp.yml", "deploy_zabbix_mcp.yml"])


class VertexAndWorkspaceTests(unittest.TestCase):
    def test_vertex_settings_preserve_unrelated_configuration(self):
        config = FILTERS.vertex(vertex(), "/home/synthetic")
        old = {"theme": "preserve", "env": {"UNRELATED": "preserve"}, "hooks": {"keep": []}}
        merged = FILTERS.vertex_settings(json.dumps(old), config)
        self.assertEqual(merged["theme"], "preserve")
        self.assertEqual(merged["hooks"], old["hooks"])
        self.assertEqual(merged["env"]["UNRELATED"], "preserve")
        self.assertEqual(merged["env"]["GOOGLE_APPLICATION_CREDENTIALS"],
                         "/home/synthetic/.config/gcloud/application_default_credentials.json")
        self.assertEqual(FILTERS.vertex_settings(json.dumps(merged), config), merged)
        self.assertEqual(FILTERS.vertex_settings(json.dumps(merged), config, True), merged)
        with self.assertRaises(AnsibleFilterError): FILTERS.vertex_settings(json.dumps(old), config, True)

    def test_other_provider_or_conflicting_account_configuration_is_refused(self):
        config = FILTERS.vertex(vertex(), "/home/synthetic")
        for env in ({"CLAUDE_CODE_USE_BEDROCK": "1"}, {"CLAUDE_CODE_USE_FOUNDRY": "1"},
                    {"ANTHROPIC_API_KEY": "synthetic"}, {"ANTHROPIC_AUTH_TOKEN": "synthetic"},
                    {"ANTHROPIC_BASE_URL": "https://gateway.example.invalid"},
                    {"ANTHROPIC_VERTEX_PROJECT_ID": "different-project"}):
            with self.subTest(env=env), self.assertRaises(AnsibleFilterError):
                FILTERS.vertex_settings(json.dumps({"env": env}), config)
        different = dict(config["adc"], refresh_token="different")
        with self.assertRaises(AnsibleFilterError): FILTERS.existing_adc(json.dumps(different), config)
        self.assertTrue(FILTERS.existing_adc(json.dumps(config["adc"]), config))

    def test_unsupported_google_authentication_is_refused(self):
        for key, value in (("type", "service_account"), ("token_uri", "https://unrelated.example.invalid/token"),
                           ("refresh_token", ""), ("universe_domain", "unrelated.invalid")):
            data = vertex(); data["adc"][key] = value
            with self.subTest(key=key), self.assertRaises(AnsibleFilterError):
                FILTERS.vertex(data, "/home/synthetic")

    def test_workspace_override_and_each_existing_component_are_validated(self):
        user = {"home": "/home/synthetic"}
        selected = MCP.workspace(user, "/home/synthetic/projects/incident")
        self.assertEqual(selected["directories"], ["/home/synthetic", "/home/synthetic/projects", "/home/synthetic/projects/incident"])
        for value in ("/tmp/other", "/home/synthetic/../other", "/home/synthetic", "relative"):
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError): MCP.workspace(user, value)
        valid = [{"stat": {"exists": True, "isdir": True, "islnk": False, "uid": 1000}}, {"stat": {"exists": False}}]
        self.assertTrue(MCP.safe_directories(valid, 1000))
        for key, value in (("islnk", True), ("isdir", False), ("uid", 1001)):
            changed = copy.deepcopy(valid); changed[0]["stat"][key] = value
            with self.subTest(key=key), self.assertRaises(AnsibleFilterError): MCP.safe_directories(changed, 1000)

    def native_run(self, directory, tasks, variables, native):
        fixture = directory / "play.yml"
        fixture.write_text(yaml.dump([{"hosts": "localhost", "connection": "local", "gather_facts": False,
                                      "vars": literal_values(variables), "tasks": tasks}], Dumper=LiteralDumper, sort_keys=False))
        environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(directory / "local"),
                           ANSIBLE_REMOTE_TEMP=str(directory / "remote"), ANSIBLE_JINJA2_NATIVE=native,
                           ANSIBLE_FILTER_PLUGINS=str(ROOT / "playbooks/filter_plugins"), ANSIBLE_NOCOLOR="1")
        return subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(fixture)],
                              env=environment, capture_output=True, text=True, timeout=60)

    def test_native_workspace_refuses_links_and_preserves_existing_modes_and_instructions(self):
        tasks = yaml.safe_load((ROOT / "playbooks/tasks/demo_mcp_workspace.yml").read_text())
        account = pwd.getpwuid(os.getuid())
        for native in ("false", "true"):
            for linked in (False, True):
                with tempfile.TemporaryDirectory(prefix="claude-workspace-") as temporary:
                    folder = Path(temporary); home = folder / "home"; home.mkdir()
                    outside = folder / "outside"; outside.mkdir(mode=0o755)
                    workspace = home / "projects" / "incident"
                    (home / "projects").mkdir(mode=0o755)
                    if linked: workspace.symlink_to(outside, target_is_directory=True)
                    else:
                        workspace.mkdir(mode=0o755)
                        (workspace / "CLAUDE.md").write_text("keep personal instructions")
                    variables = {"demo_mcp_user": {"home": str(home), "name": account.pw_name,
                                                  "uid": account.pw_uid, "gid": account.pw_gid},
                                 "claude_agent_workdir": str(workspace)}
                    result = self.native_run(folder, tasks, variables, native)
                    with self.subTest(native=native, linked=linked):
                        self.assertEqual(result.returncode == 0, not linked, result.stdout + result.stderr)
                        self.assertEqual(outside.stat().st_mode & 0o777, 0o755)
                        self.assertEqual((home / "projects").stat().st_mode & 0o777, 0o755)
                        if not linked:
                            self.assertEqual(workspace.stat().st_mode & 0o777, 0o755)
                            self.assertEqual((workspace / "CLAUDE.md").read_text(), "keep personal instructions")

    def test_native_vertex_provisioning_is_idempotent_and_refuses_conflicts_and_races(self):
        preflight = yaml.safe_load((ROOT / "playbooks/tasks/demo_claude_vertex_preflight.yml").read_text())
        apply = yaml.safe_load((ROOT / "playbooks/tasks/demo_claude_vertex_apply.yml").read_text())
        account = pwd.getpwuid(os.getuid())
        for native in ("false", "true"):
            for failure in ("none", "adc", "provider", "race"):
                with tempfile.TemporaryDirectory(prefix="claude-vertex-") as temporary:
                    folder = Path(temporary); home = folder / "home"; home.mkdir()
                    (home / ".claude").mkdir(); settings = home / ".claude/settings.json"
                    original = {"theme": "preserve", "env": {"UNRELATED": "preserve"}}
                    if failure == "provider": original["env"]["CLAUDE_CODE_USE_BEDROCK"] = "1"
                    settings.write_text(json.dumps(original))
                    adc = home / ".config/gcloud/application_default_credentials.json"
                    if failure == "adc":
                        adc.parent.mkdir(parents=True); adc.write_text(json.dumps(dict(vertex()["adc"], refresh_token="other-account")))
                    tasks = copy.deepcopy(preflight)
                    if failure == "race":
                        tasks.append({"name": "Simulate a concurrent user settings change", "ansible.builtin.copy": {
                            "dest": str(settings), "content": json.dumps({"user_changed": True}), "mode": "0600"}})
                    tasks += copy.deepcopy(apply)
                    variables = {"demo_mcp_user": {"home": str(home), "name": account.pw_name,
                                                  "uid": account.pw_uid, "gid": account.pw_gid},
                                 "demo_claude_vertex_auth": vertex()}
                    result = self.native_run(folder, tasks, variables, native)
                    with self.subTest(native=native, failure=failure):
                        self.assertEqual(result.returncode == 0, failure == "none", result.stdout + result.stderr)
                        self.assertNotIn("synthetic-private-secret", result.stdout + result.stderr)
                        self.assertNotIn("synthetic-private-refresh", result.stdout + result.stderr)
                        if failure == "none":
                            self.assertEqual(json.loads(adc.read_text()), vertex()["adc"])
                            merged = json.loads(settings.read_text())
                            self.assertEqual(merged["theme"], "preserve")
                            self.assertEqual(merged["env"]["UNRELATED"], "preserve")
                            self.assertEqual(adc.stat().st_mode & 0o777, 0o600)
                            again = self.native_run(folder, tasks, variables, native)
                            self.assertEqual(again.returncode, 0, again.stdout + again.stderr)
                            self.assertEqual(json.loads(settings.read_text()), merged)
                        elif failure == "race": self.assertEqual(json.loads(settings.read_text()), {"user_changed": True})
                        else: self.assertEqual(json.loads(settings.read_text()), original)


if __name__ == "__main__":
    unittest.main()
