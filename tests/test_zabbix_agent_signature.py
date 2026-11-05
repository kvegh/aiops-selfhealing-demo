"""Keep the real RPM-key fingerprint refusal ahead of package installation."""
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from ansible.modules import rpm_key
import yaml


ROOT = Path(__file__).resolve().parents[1]
KEY_URL = "https://repo.zabbix.com/RPM-GPG-KEY-ZABBIX-B5333005"
KEY_FINGERPRINT = "4C3D6F2CC75F5146754FC374D913219AB5333005"
# A synthetic public packet, not an account key or a private key. Native Ansible
# parses its actual fingerprint so a substituted download cannot satisfy the pin.
SYNTHETIC_FINGERPRINT = "930D6F779DC547F7DB7648516BA67743DE773D0A"
SYNTHETIC_KEY = """-----BEGIN PGP PUBLIC KEY BLOCK-----

xo0EX14QAAEEALOzs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Oz
s7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Oz
s7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7Ozs7OzABEBAAE=
=qLiy
-----END PGP PUBLIC KEY BLOCK-----
"""


class ModuleResult(Exception):
    def __init__(self, failed, values):
        self.failed = failed
        self.values = values


class KeyModule:
    """Confine native rpm_key's RPM command boundary to recorded calls."""

    def __init__(self, arguments):
        self.params = arguments
        self.check_mode = False
        self.imports = []
        self.temporary_files = []

    def get_bin_path(self, name, required):
        return "/usr/bin/" + name

    def run_command(self, command, **kwargs):
        if command == "/usr/bin/rpm -q gpg-pubkey":
            return 1, "", ""
        if isinstance(command, list) and command[:2] == ["/usr/bin/rpm", "--import"]:
            self.imports.append(command[2])
            return 0, "", ""
        raise AssertionError("Unexpected command: " + str(command))

    def add_cleanup_file(self, path):
        self.temporary_files.append(path)

    def cleanup(self, path):
        Path(path).unlink(missing_ok=True)

    def fail_json(self, **values):
        raise ModuleResult(True, values)

    def exit_json(self, **values):
        raise ModuleResult(False, values)


class ZabbixAgentSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = yaml.safe_load(
            (ROOT / "playbooks/deploy_zabbix_agent.yml").read_text()
        )[0]["tasks"]
        cls.key_task = next(task for task in cls.tasks if "ansible.builtin.rpm_key" in task)

    def run_key_task(self, fingerprint=None):
        arguments = dict(self.key_task["ansible.builtin.rpm_key"])
        if fingerprint is not None:
            arguments["fingerprint"] = fingerprint
        module = KeyModule(arguments)
        try:
            with patch.object(
                rpm_key, "fetch_url",
                return_value=(io.BytesIO(SYNTHETIC_KEY.encode()), {"status": 200}),
            ):
                with self.assertRaises(ModuleResult) as result:
                    rpm_key.RpmKey(module)
            return result.exception, module.imports
        finally:
            for filename in module.temporary_files:
                module.cleanup(filename)

    def test_substituted_key_is_refused_before_import(self):
        result, imports = self.run_key_task()
        self.assertTrue(result.failed)
        self.assertIn("does not match", result.values["msg"])
        self.assertEqual(imports, [])

    def test_matching_fingerprint_reaches_import_without_running_rpm(self):
        result, imports = self.run_key_task(SYNTHETIC_FINGERPRINT)
        self.assertFalse(result.failed)
        self.assertTrue(result.values["changed"])
        self.assertEqual(len(imports), 1)

    def test_pinned_https_key_precedes_both_signature_checked_packages(self):
        key = self.key_task["ansible.builtin.rpm_key"]
        self.assertEqual(key["key"], KEY_URL)
        self.assertEqual(key["fingerprint"], KEY_FINGERPRINT)
        self.assertIs(key["validate_certs"], True)
        self.assertNotIn("ignore_errors", self.key_task)
        self.assertNotIn("when", self.key_task)
        package_tasks = [task for task in self.tasks if "ansible.builtin.dnf" in task]
        self.assertEqual(len(package_tasks), 2)
        for task in package_tasks:
            self.assertLess(self.tasks.index(self.key_task), self.tasks.index(task))
            self.assertIs(task["ansible.builtin.dnf"]["disable_gpg_check"], False)


if __name__ == "__main__":
    unittest.main()
