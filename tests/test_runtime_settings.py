"""Exercise whole-file ciphertext in real Ansible extra-vars, with no services."""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ansible.parsing.vault import VaultLib, VaultSecret
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_settings", ROOT / "playbooks/filter_plugins/demo_runtime.py")
runtime = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runtime)


class RuntimeSchemaTests(unittest.TestCase):
    def test_only_the_selected_instance_and_reviewed_names_are_returned(self):
        data = {"schema_version": 1, "instances": {
            "aap27-test-7": {"demo_zabbix_mcp_api_token": "selected"},
            "aap27-test-8": {"demo_zabbix_mcp_api_token": "other"},
        }}
        self.assertEqual(runtime.selected_settings(data, "aap27-test-7"), data["instances"]["aap27-test-7"])

    def test_unknown_names_namespaces_and_schema_are_rejected(self):
        valid = {"schema_version": 1, "instances": {"aap27-test-7": {}}}
        cases = []
        for key in ["ansible_host", "ansible_user", "lookup", "demo_runtime_expected_instance"]:
            changed = copy.deepcopy(valid); changed["instances"]["aap27-test-7"][key] = "unreviewed"; cases.append(changed)
        cases += [{**valid, "extra": {}}, {**valid, "schema_version": True}, {**valid, "instances": {"production": {}}}]
        for value in cases:
            with self.subTest(value=value), self.assertRaises(Exception): runtime.selected_settings(value, "aap27-test-7")
        with self.assertRaises(Exception): runtime.selected_settings(valid, "aap27-test-8")

    def test_subscription_credentials_are_selected_from_only_the_matching_instance(self):
        settings = {"demo_mcp_subscription": {"instance_name": "aap27-test-7", "organization": "synthetic", "activation_keys": ["synthetic"]}}
        document = {"schema_version": 1, "instances": {"aap27-test-7": settings, "aap27-test-8": {}}}
        self.assertEqual(runtime.selected_settings(document, "aap27-test-7"), settings)
        self.assertEqual(runtime.selected_settings(document, "aap27-test-8"), {})


class NativeRuntimeExecutionTests(unittest.TestCase):
    def run_loader(self, *, wrong_instance=False, unknown_key=False, wrong_password=False, controller_unsafe=False):
        with tempfile.TemporaryDirectory(prefix="aiops-runtime-fixture-") as temporary:
            folder = Path(temporary)
            secret_text = "synthetic-protected-{{ forbidden_expression }}"
            settings = {"demo_zabbix_basic_auth_file": secret_text, "demo_zabbix_event_stream": {
                "url": "https://aap27.v07.example.invalid/eda-event-streams/api/eda/v1/external_event_stream/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/post/",
                "username": "synthetic-user", "password": secret_text,
            }}
            if unknown_key: settings["ansible_host"] = "unreviewed.invalid"
            document = {"schema_version": 1, "instances": {"aap27-test-7": settings}}
            vault = VaultLib([("default", VaultSecret(b"synthetic-test-password"))])
            from ansible.parsing.yaml.dumper import AnsibleDumper
            from ansible.utils.unsafe_proxy import AnsibleUnsafeText, wrap_var
            class LiteralDumper(AnsibleDumper):
                pass
            LiteralDumper.add_representer(AnsibleUnsafeText, lambda dumper, value: dumper.represent_scalar('!unsafe', value._strip_unsafe()))
            ciphertext = vault.encrypt(yaml.dump(wrap_var(document), Dumper=LiteralDumper).encode()).decode()
            password = folder / "password"; password.write_text("wrong-password" if wrong_password else "synthetic-test-password"); password.chmod(0o600)
            tasks = yaml.safe_load((ROOT / "playbooks/tasks/demo_runtime_settings.yml").read_text())
            block = tasks[0]["block"]
            next(t for t in block if "ansible.builtin.tempfile" in t)["ansible.builtin.tempfile"]["path"] = str(folder)
            include_index = next(i for i, t in enumerate(block) if "ansible.builtin.include_vars" in t)
            block[include_index:include_index] = [
                {"name": "Inspect fixture ciphertext mode", "ansible.builtin.stat": {"path": "{{ demo_runtime_temporary_file.path }}"}, "register": "fixture_cipher_stat"},
                {"name": "Read fixture ciphertext without decryption", "ansible.builtin.slurp": {"src": "{{ demo_runtime_temporary_file.path }}"}, "register": "fixture_cipher_bytes"},
                {"name": "Require private opaque file", "ansible.builtin.assert": {"that": ["fixture_cipher_stat.stat.mode == '0600'", "(fixture_cipher_bytes.content | b64decode).startswith('$ANSIBLE_VAULT;')"], "quiet": True}},
            ]
            expected = "aap27-test-8" if wrong_instance else "aap27-test-7"
            play = [{"name": "Test native selected runtime loading", "hosts": "localhost", "connection": "local", "gather_facts": False,
                     "vars": {"demo_runtime_expected_instance": expected}, "tasks": tasks + [
                         {"name": "Require selected scalar and structured secrets to stay literal", "ansible.builtin.assert": {"that": [
                             "demo_zabbix_basic_auth_file | hash('sha256') == '" + hashlib.sha256(secret_text.encode()).hexdigest() + "'",
                             "demo_zabbix_event_stream is mapping",
                             "demo_zabbix_event_stream.password | hash('sha256') == '" + hashlib.sha256(secret_text.encode()).hexdigest() + "'",
                         ], "quiet": True}, "no_log": True},
                     ]}]
            playbook = folder / "play.yml"; playbook.write_text(yaml.safe_dump(play, sort_keys=False))
            extra = folder / "extra.json"; values = {"demo_runtime_settings_vault": ciphertext}
            if controller_unsafe:
                from ansible.parsing.yaml.dumper import AnsibleDumper
                from ansible.utils.unsafe_proxy import wrap_var
                extra = folder / "extra.yml"; extra.write_text(yaml.dump(wrap_var(values), Dumper=AnsibleDumper))
            else: extra.write_text(json.dumps(values))
            extra.chmod(0o600)
            environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(folder / "local"), ANSIBLE_REMOTE_TEMP=str(folder / "remote"),
                               ANSIBLE_FILTER_PLUGINS=str(ROOT / "playbooks/filter_plugins"), ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", "--vault-password-file", str(password),
                                     "-e", "@" + str(extra), str(playbook)], env=environment, text=True, capture_output=True, timeout=90)
            self.assertNotIn(secret_text, result.stdout + result.stderr)
            self.assertNotIn(ciphertext, result.stdout + result.stderr)
            self.assertFalse(list(folder.glob("aiops-runtime-vault-*")), "Runtime tempfile must be removed on every outcome")
            return result

    def test_real_json_extra_vars_preserve_private_ciphertext_and_literal_secret(self):
        result = self.run_loader(); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_controller_unsafe_extra_vars_use_the_same_native_loader(self):
        result = self.run_loader(controller_unsafe=True); self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_wrong_instance_cleans_the_tempfile_without_exposing_the_secret(self):
        result = self.run_loader(wrong_instance=True); self.assertNotEqual(result.returncode, 0)

    def test_unknown_setting_cleans_the_tempfile_without_exposing_the_secret(self):
        result = self.run_loader(unknown_key=True); self.assertNotEqual(result.returncode, 0)

    def test_wrong_vault_password_cleans_the_tempfile(self):
        result = self.run_loader(wrong_password=True); self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
