"""Exercise allocation validation and the actual managed nginx template offline."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from ansible.errors import AnsibleFilterError
from jinja2 import Environment, StrictUndefined
import yaml


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "website_filters", ROOT / "playbooks/filter_plugins/demo_website.py"
)
FILTERS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FILTERS)


def deployment(number=16):
    return {
        "instance_name": f"aap27-test-{number}", "instance_number": number,
        "zone": "example.com", "aap_fqdn": f"aap27.v{number:02d}.example.com",
        "hypervisor": {
            "name": "recovery-hypervisor", "address": "8.8.8.8", "public_ipv4": "8.8.8.8",
            "user": "automation", "port": 22, "machine_id": "a" * 32,
            "host_keys": ["ssh-ed25519 c3ludGhldGljLXRlc3Qta2V5"],
        },
    }


class VersionedWebsiteTests(unittest.TestCase):
    def test_website_and_aap_reuse_the_same_existing_allocation(self):
        for number in (1, 16, 100):
            with self.subTest(number=number):
                config = FILTERS.website_configuration(deployment(number))
                self.assertEqual(config["hostname"], f"redhat.v{number:02d}.example.com")
                self.assertEqual(config["aap_hostname"], f"aap27.v{number:02d}.example.com")
                self.assertEqual(config["record_name"], f"redhat.v{number:02d}")
                self.assertEqual(config["instance_number"], number)

    def test_conflicting_or_absent_identity_is_rejected_before_remote_actions(self):
        variants = []
        for field, value in (
            ("instance_name", "aap27-test-99"), ("instance_number", True),
            ("instance_number", 0), ("aap_fqdn", "production.example.com"),
            ("zone", "example.com; include /tmp/other;"), ("hypervisor", {}),
        ):
            item = deployment()
            item[field] = value
            variants.append(item)
        for field, value in (
            ("address", "host; command"), ("public_ipv4", "192.168.1.1"),
            ("port", 70000), ("user", "root;command"), ("machine_id", ""),
            ("host_keys", []), ("host_keys", ["ssh-ed25519 !!!"]),
        ):
            item = deployment()
            item["hypervisor"][field] = value
            variants.append(item)
        for item in variants:
            with self.subTest(item=item), self.assertRaises(AnsibleFilterError):
                FILTERS.website_configuration(item)

    def test_separate_allocations_use_distinct_content_cache_and_nginx_paths(self):
        first = FILTERS.website_configuration(deployment(16))
        second = FILTERS.website_configuration(deployment(17))
        for field in ("root", "rate_limit_file", "rate_limit_zone", "cache_zone", "cache_path", "vhost_file"):
            self.assertNotEqual(first[field], second[field])

    def test_dns_guard_allows_only_absent_or_identical_ipv4_records(self):
        check = FILTERS.safe_dns_records
        self.assertTrue(check([], "8.8.8.8"))
        self.assertTrue(check([{"type": "A", "data": "8.8.8.8"}], "8.8.8.8"))
        self.assertFalse(check([{"type": "A", "data": "1.1.1.1"}], "8.8.8.8"))
        self.assertFalse(check([{"type": "AAAA", "data": "8.8.8.8"}], "8.8.8.8"))
        self.assertFalse(check({"data": "8.8.8.8"}, "8.8.8.8"))

    def render(self, tls):
        config = FILTERS.website_configuration(deployment())
        environment = Environment(undefined=StrictUndefined, keep_trailing_newline=True)
        template = environment.from_string(
            (ROOT / "playbooks/templates/demo-website-vhost.conf.j2").read_text()
        )
        return template.render(
            demo_website_config=config, demo_website_tls_ready=tls,
            demo_website_root=config["root"], demo_button_marker=config["root"] + "/.armed",
            demo_website_rate_limit_file=config["rate_limit_file"],
            demo_website_webhook_key="synthetic-test-key-for-nginx-only", demo_website_fault_template_id=42,
        )

    def test_initial_http_challenge_config_has_no_webhook_secret_or_tls_dependency(self):
        config = self.render(False)
        self.assertIn("server_name redhat.v16.example.com;", config)
        self.assertIn("location /.well-known/acme-challenge/", config)
        self.assertNotIn("synthetic-test-key", config)
        self.assertNotIn("listen 443", config)
        self.assertNotIn("ssl_certificate", config)

    def test_https_template_pins_the_matching_target_and_verifies_both_tls_connections(self):
        config = self.render(True)
        self.assertIn("ssl_certificate /etc/letsencrypt/live/redhat.v16.example.com/fullchain.pem;", config)
        self.assertIn("proxy_pass https://aap27.v16.example.com/api/controller/v2/job_templates/42/gitlab/;", config)
        self.assertIn("proxy_ssl_name aap27.v16.example.com;", config)
        self.assertIn("proxy_ssl_verify on;", config)
        self.assertIn("proxy_ssl_trusted_certificate /etc/pki/tls/certs/ca-bundle.crt;", config)
        self.assertNotIn("proxy_ssl_verify off", config)
        self.assertIn("if (!-f /var/www/redhat-v16/.armed) { return 423; }", config)
        self.assertIn("proxy_cache_key \"$request_method|$uri|$request_body\";", config)
        self.assertIn("keys_zone=redhat_v16_deliveries:1m", config)


class ManagedTargetTaskTests(unittest.TestCase):
    def run_target_tasks(self, address="8.8.8.8", machine_id="a" * 32):
        with tempfile.TemporaryDirectory(prefix="demo-target-test-") as temporary:
            root = Path(temporary)
            (root / "bin").mkdir()
            log = root / "identity-check"
            cat = root / "bin/cat"
            cat.write_text(
                "#!/usr/bin/python3\nimport os\nfrom pathlib import Path\n"
                "Path(os.environ['DEMO_IDENTITY_LOG']).write_text('checked')\n"
                "print(os.environ['DEMO_TEST_MACHINE_ID'])\n"
            )
            cat.chmod(0o700)
            inventory = root / "inventory.yml"
            inventory.write_text(yaml.safe_dump({"all": {"hosts": {"localhost": {
                "ansible_connection": "local", "ansible_host": address,
                "ansible_python_interpreter": sys.executable,
            }}}}))
            play = root / "preflight.yml"
            play.write_text(yaml.safe_dump([{
                "hosts": "all", "become": False, "gather_facts": False,
                "vars": {"demo_website_manage_infrastructure": True,
                         "demo_website_public_hostname": "redhat.v16.example.com",
                         "demo_website_deployment": deployment()},
                "tasks": [{"ansible.builtin.include_tasks": str(
                    ROOT / "playbooks/tasks/demo_website_target.yml")},
                          {"ansible.builtin.assert": {"that": [
                              "demo_website_root == '/var/www/redhat-v16'",
                              "demo_button_marker == '/var/www/redhat-v16/.armed'",
                              "ansible_host_key_checking | bool",
                              "ansible_ssh_host_key_checking | bool",
                              "'StrictHostKeyChecking=yes' in ansible_ssh_common_args",
                          ]}},
                          {"ansible.builtin.file": {
                              "path": "{{ demo_website_known_hosts.path }}", "state": "absent"}}],
            }], sort_keys=False))
            environment = dict(
                os.environ, PATH=str(root / "bin") + os.pathsep + os.environ["PATH"],
                ANSIBLE_FILTER_PLUGINS=str(ROOT / "playbooks/filter_plugins"),
                ANSIBLE_LOCAL_TEMP=str(root / "local"), ANSIBLE_REMOTE_TEMP=str(root / "remote"),
                ANSIBLE_NOCOLOR="1", DEMO_IDENTITY_LOG=str(log), DEMO_TEST_MACHINE_ID=machine_id,
            )
            result = subprocess.run(
                [sys.executable, "-m", "ansible.cli.playbook", "-i", str(inventory), str(play)],
                env=environment, text=True, capture_output=True, timeout=45,
            )
            return result, log.exists()

    def test_actual_preflight_checks_identity_and_selects_versioned_paths(self):
        result, identity_checked = self.run_target_tasks()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(identity_checked)

    def test_wrong_destination_is_rejected_before_any_remote_identity_command(self):
        result, identity_checked = self.run_target_tasks(address="1.1.1.1")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(identity_checked)

    def test_wrong_live_machine_identity_stops_the_real_preflight(self):
        result, identity_checked = self.run_target_tasks(machine_id="b" * 32)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(identity_checked)


if __name__ == "__main__":
    unittest.main()
