"""Check native RHSM input/role routing without registering or modifying a host."""

import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class NativeSubscriptionTests(unittest.TestCase):
    def settings(self):
        return {"instance_name": "aap27-test-7", "organization": "synthetic-org", "activation_keys": ["synthetic-key"],
                "repositories": [{"name": "rhel-9-for-x86_64-baseos-rpms", "state": "enabled"},
                                 {"name": "rhel-9-for-x86_64-appstream-rpms", "state": "enabled"}]}

    def run_tasks(self, tasks, settings=None, list_only=False):
        with tempfile.TemporaryDirectory(prefix="mcp-rhsm-test-") as temporary:
            folder = Path(temporary)
            play = [{"name": "Check the subscription plan without host changes", "hosts": "localhost", "connection": "local",
                     "gather_facts": False, "vars": {"demo_mcp_deployment": {"instance_name": "aap27-test-7"},
                                                    "demo_mcp_subscription": self.settings() if settings is None else settings}, "tasks": tasks}]
            source = folder / "check.yml"; source.write_text(yaml.safe_dump(play, sort_keys=False))
            environment = dict(os.environ, ANSIBLE_HOME=str(folder / "ansible-home"), ANSIBLE_LOCAL_TEMP=str(folder / "local"),
                               ANSIBLE_REMOTE_TEMP=str(folder / "remote"), ANSIBLE_NOCOLOR="1")
            command = [sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(source)]
            if list_only: command.append("--list-tasks")
            return subprocess.run(command, env=environment, text=True, capture_output=True, timeout=60)

    def deployment_tasks(self):
        return yaml.safe_load((ROOT / "playbooks/tasks/demo_mcp_subscription.yml").read_text())[0]["block"]

    def test_complete_selected_inputs_pass_and_wrong_or_missing_credentials_stop(self):
        tasks = self.deployment_tasks()[:1]
        result = self.run_tasks(tasks)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cases = []
        for key, value in [("instance_name", "aap27-test-8"), ("organization", ""), ("activation_keys", []),
                           ("activation_keys", [""]), ("activation_keys", {"synthetic-key": "wrong type"}), ("repositories", [])]:
            settings = self.settings(); settings[key] = value; cases.append(settings)
        for settings in cases:
            with self.subTest(settings=settings):
                result = self.run_tasks(tasks, settings)
                self.assertNotEqual(result.returncode, 0)

    def test_real_pinned_role_entries_resolve_without_insights_registration_or_unregistration(self):
        # Static imports let Ansible list the real vendor task graph without
        # executing package installation, registration or repository changes.
        tasks = []
        for task in self.deployment_tasks():
            if "ansible.builtin.include_role" in task:
                value = copy.deepcopy(task["ansible.builtin.include_role"]); value.pop("apply", None)
                tasks.append({"name": task["name"], "ansible.builtin.import_role": value, "vars": task.get("vars", {})})
        self.assertEqual(len(tasks), 2)
        result = self.run_tasks(tasks, list_only=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Call subscription-manager", result.stdout)
        self.assertIn("Configure repositories", result.stdout)
        self.assertNotIn("Register insights-client", result.stdout)
        self.assertNotIn("Unregister insights-client", result.stdout)
        self.assertNotIn("Configure autoupdate", result.stdout)
        self.assertNotIn("Disable remediation", result.stdout)

    def test_actual_vendor_arguments_preserve_registration_and_unrelated_repositories(self):
        from ansible.plugins.loader import init_plugin_loader
        from ansible.utils.collection_loader._collection_finder import _get_collection_role_path
        init_plugin_loader()
        role = _get_collection_role_path("redhat.rhel_system_roles.rhc")
        self.assertIsNotNone(role, "The pinned certified collection must already be installed for this check")
        role_path = role[1]
        vendor = yaml.safe_load((Path(role_path) / "tasks/subscription-manager.yml").read_text())
        registration = next(t["redhat.rhel_system_roles.redhat_subscription"] for t in vendor
                            if "redhat.rhel_system_roles.redhat_subscription" in t)
        repositories = next(t for t in vendor if "block" in t)["block"][-1]["redhat.rhel_system_roles.rhsm_repository"]
        self.assertIs(repositories["purge"], False)
        role_vars = self.deployment_tasks()[-1]["vars"]
        selected_arguments = {key: registration[key] for key in ["state", "force_register", "org_id", "activationkey"]}
        tasks = [{"name": "Render actual vendor registration parameters using the selected native role inputs",
                  "ansible.builtin.set_fact": {"fixture_registration": selected_arguments}, "vars": role_vars, "no_log": True},
                 {"name": "Require existing registration preservation and selected credential routing", "ansible.builtin.assert": {
                     "that": ["fixture_registration.state == 'present'", "fixture_registration.force_register is sameas false",
                              "fixture_registration.org_id == demo_mcp_subscription.organization",
                              "fixture_registration.activationkey == demo_mcp_subscription.activation_keys | join(',')"], "quiet": True}}]
        result = self.run_tasks(tasks)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
