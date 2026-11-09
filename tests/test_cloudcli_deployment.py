"""Run CloudCLI input checks and unit rendering locally without changing users/services."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class CloudCliDeploymentTests(unittest.TestCase):
    def settings(self):
        accounts = []
        for name, port in [("synthetic_primary", 12001), ("synthetic_web", 12002)]:
            accounts.append({
                "name": name, "home": "/home/" + name,
                "workdir": "/home/" + name + "/workspace", "listen_address": "127.0.0.1",
                "port": port, "enabled": True, "start": True, "linger": True,
                "runtime_max_sec": "infinity", "restart": "on-failure",
                "environment": {"SYNTHETIC_SECRET": 'literal $value "quoted" \\path'},
            })
        return {"instance_name": "aap27-test-7", "version": "2.3.4", "node_bin_dir": "/usr/bin",
                "health_path": "/health", "accounts": accounts}

    def run_preflight(self, settings, render=False, check_node=False, mcp_user="synthetic_primary"):
        with tempfile.TemporaryDirectory(prefix="aiops-cloudcli-test-") as temporary:
            folder = Path(temporary)
            tasks = yaml.safe_load((ROOT / "playbooks/tasks/demo_cloudcli.yml").read_text())[:4 if check_node else 3]
            if render:
                for source in ["demo-cloudcli.service.j2", "demo-cloudcli.env.j2"]:
                    tasks.append({"name": "Render native CloudCLI configuration", "ansible.builtin.template": {
                        "src": str(ROOT / "playbooks/templates" / source), "dest": str(folder / source), "mode": "0600"}})
            play = [{"name": "Validate CloudCLI without deployment", "hosts": "localhost", "connection": "local", "gather_facts": False,
                     "vars": {"demo_cloudcli_deployment": settings, "demo_cloudcli_account": settings["accounts"][0],
                              "demo_mcp_deployment": {"instance_name": "aap27-test-7"}, "demo_mcp_user": {"name": mcp_user},
                              "demo_mcp_config": {"tra": {"address": "127.0.0.1"}}, "ansible_host": "127.0.0.1"}, "tasks": tasks}]
            source = folder / "play.yml"; source.write_text(yaml.safe_dump(play, sort_keys=False))
            environment = dict(os.environ, ANSIBLE_HOME=str(folder / "ansible-home"), ANSIBLE_LOCAL_TEMP=str(folder / "local"),
                               ANSIBLE_REMOTE_TEMP=str(folder / "remote"), ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(source)],
                                    env=environment, capture_output=True, text=True, timeout=60)
            rendered = {p.name: p.read_text() for p in folder.glob("*.j2")}
            return result, rendered

    def test_explicit_two_account_settings_render_private_service_and_literal_environment(self):
        result, rendered = self.run_preflight(self.settings(), render=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("/home/synthetic_primary/.npm-global/bin/cloudcli --port 12001", rendered["demo-cloudcli.service.j2"])
        self.assertIn("Environment=HOST=127.0.0.1", rendered["demo-cloudcli.service.j2"])
        self.assertIn('SYNTHETIC_SECRET="literal $value \\"quoted\\" \\\\path"', rendered["demo-cloudcli.env.j2"])

    def test_missing_exact_release_or_wrong_instance_stops_before_remote_work(self):
        missing = self.settings(); del missing["version"]
        wrong = self.settings(); wrong["instance_name"] = "aap27-test-8"
        moving = self.settings(); moving["version"] = "latest"
        for settings in [missing, wrong, moving]:
            with self.subTest(settings=settings):
                result, _ = self.run_preflight(settings)
                self.assertNotEqual(result.returncode, 0)

    def test_two_explicit_cloudcli_accounts_can_differ_from_the_existing_mcp_account(self):
        result, _ = self.run_preflight(self.settings(), mcp_user="synthetic_transport")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_selected_node_runtime_stops_before_account_creation(self):
        settings = self.settings(); settings["node_bin_dir"] = "/nonexistent-synthetic-runtime/bin"
        result, _ = self.run_preflight(settings, check_node=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("No such file or directory", result.stdout + result.stderr)

    def test_bad_second_account_or_environment_is_rejected_before_any_account_write(self):
        settings = self.settings()
        cases = []
        for field, value in [("listen_address", "0.0.0.0"), ("home", "/root"), ("port", 443),
                             ("environment", {"HOST": "override"}), ("environment", {"BAD-NAME": "value"}),
                             ("environment", {"VALUE": "line\nbreak"})]:
            changed = copy.deepcopy(settings); changed["accounts"][1][field] = value; cases.append(changed)
        for settings in cases:
            with self.subTest(settings=settings):
                result, _ = self.run_preflight(settings)
                self.assertNotEqual(result.returncode, 0)

    def connection(self):
        return {"url": "https://source-controller.example.test/mcp",
                "http_headers": {"Authorization": "Bearer synthetic-account-token"},
                "default_tools_approval_mode": "never"}

    def test_only_an_explicit_matching_account_can_receive_its_captured_connection(self):
        valid = self.settings()
        valid["codex_mcp_accounts"] = {"synthetic_web": {"mcp_servers": {"aap": self.connection()}}}
        result, _ = self.run_preflight(valid)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        wrong = copy.deepcopy(valid)
        wrong["codex_mcp_accounts"]["other_account"] = wrong["codex_mcp_accounts"].pop("synthetic_web")
        insecure = copy.deepcopy(valid)
        insecure["codex_mcp_accounts"]["synthetic_web"]["mcp_servers"]["aap"]["url"] = "http://source-controller.example.test/mcp"
        missing = copy.deepcopy(valid)
        del missing["codex_mcp_accounts"]["synthetic_web"]["mcp_servers"]["aap"]["http_headers"]
        for settings in [wrong, insecure, missing]:
            with self.subTest(settings=settings):
                result, _ = self.run_preflight(settings)
                self.assertNotEqual(result.returncode, 0)

    def run_codex_configuration(self, *, existing=False, linked=False, foreign_owner=False):
        with tempfile.TemporaryDirectory(prefix="aiops-cloudcli-codex-test-") as temporary:
            folder = Path(temporary)
            home = folder / "home"; home.mkdir()
            storage = home / ".codex"
            config = storage / "config.toml"
            original = 'model = "synthetic-model"\n[mcp_servers.other]\nurl = "https://unrelated.example.test/mcp"\n'
            if existing or linked or foreign_owner:
                storage.mkdir()
            if linked:
                target = folder / "unrelated.toml"; target.write_text(original); config.symlink_to(target)
            elif existing:
                config.write_text(original)
            templates = folder / "templates"; templates.mkdir()
            template = ROOT / "playbooks/templates/demo-cloudcli-codex.toml.j2"
            (templates / template.name).write_text(template.read_text())
            play = [{"name": "Configure only synthetic local Codex settings", "hosts": "localhost", "connection": "local",
                     "gather_facts": False, "vars": {"demo_cloudcli_account": {"name": "synthetic_web", "home": str(home)},
                     "demo_cloudcli_codex": self.connection(),
                     "ansible_facts": {"getent_passwd": {"synthetic_web": ["x", str(os.getuid() + int(foreign_owner))]}}},
                     "tasks": [{"name": "Use the actual native Codex configuration tasks",
                                "ansible.builtin.include_tasks": str(ROOT / "playbooks/tasks/demo_cloudcli_codex.yml")}]}]
            source = folder / "play.yml"; source.write_text(yaml.safe_dump(play, sort_keys=False))
            environment = dict(os.environ, ANSIBLE_HOME=str(folder / "ansible-home"),
                               ANSIBLE_LOCAL_TEMP=str(folder / "local"), ANSIBLE_REMOTE_TEMP=str(folder / "remote"), ANSIBLE_NOCOLOR="1")
            def apply():
                return subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(source)],
                                      env=environment, capture_output=True, text=True, timeout=60)
            first = apply()
            if existing or linked or foreign_owner:
                self.assertNotEqual(first.returncode, 0)
                self.assertIn("Preserve the different existing Codex configuration or storage for explicit review.", first.stdout)
                if linked:
                    self.assertEqual(target.read_text(), original)
                elif existing:
                    self.assertEqual(config.read_text(), original)
                else:
                    self.assertFalse(config.exists())
                return
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            expected = {"mcp_servers": {"aap": self.connection()}}
            self.assertEqual(tomllib.loads(config.read_text()), expected)
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            second = apply()
            self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
            self.assertRegex(second.stdout, r"changed=0\s")

    def test_native_codex_template_preserves_captured_destination_and_is_idempotent(self):
        self.run_codex_configuration()

    def test_different_existing_codex_configuration_is_preserved_and_refused(self):
        self.run_codex_configuration(existing=True)

    def test_linked_codex_configuration_is_preserved_and_refused(self):
        self.run_codex_configuration(linked=True)

    def test_foreign_codex_directory_is_preserved_and_refused(self):
        self.run_codex_configuration(foreign_owner=True)


if __name__ == "__main__":
    unittest.main()
