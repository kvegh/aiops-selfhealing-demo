"""Exercise real Ansible build decisions without packages, Git access or containers."""

import copy
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class NativeTargetBuildTests(unittest.TestCase):
    def run_runtime(self, existing=False, build_succeeds=True, checkout_matches=True):
        with tempfile.TemporaryDirectory(prefix="mcp-native-build-test-") as temporary:
            root = Path(temporary)
            home = root / "home"
            home.mkdir()
            (home / "private-canary").write_text("Do not copy runtime configuration into a build.")
            revision = root / "image-revision"
            calls = root / "build-arguments"
            play = yaml.safe_load((ROOT / "playbooks/deploy_linux_mcp.yml").read_text())[0]
            image = play["vars"]["demo_mcp_build"]
            if existing:
                revision.write_text(image["revision"])
            binary = root / "bin"
            binary.mkdir()
            podman = binary / "podman"
            podman.write_text(
                "#!" + sys.executable + "\nimport json,sys\nfrom pathlib import Path\n"
                "state=Path(" + repr(str(revision)) + "); calls=Path(" + repr(str(calls)) + ")\n"
                "if sys.argv[1:3]==['image','inspect']:\n"
                " if not state.exists(): raise SystemExit(1)\n"
                " print(state.read_text()); raise SystemExit(0)\n"
                "if sys.argv[1]!='build': raise SystemExit(9)\n"
                "context=Path(sys.argv[-1])\n"
                "assert context.name=='source' and context.parent.name.startswith('.aiops-mcp-build-')\n"
                "assert not list(context.rglob('private-canary'))\n"
                "calls.write_text(json.dumps(sys.argv[1:]))\n"
                + ("state.write_text(" + repr(image["revision"]) + ")\n" if build_succeeds
                   else "raise SystemExit('Synthetic build failure')\n")
            )
            podman.chmod(0o700)
            uid, gid = os.getuid(), os.getgid()
            user = {"name": pwd.getpwuid(uid).pw_name, "uid": uid, "gid": gid, "home": str(home)}
            for name in ("subuid", "subgid"):
                (root / name).write_text(user["name"] + ":100000:65536\n")
            tasks = copy.deepcopy(yaml.safe_load((ROOT / "playbooks/tasks/demo_mcp_runtime.yml").read_text()))

            def prepare(items):
                for task in items:
                    # Test fixtures stay in the current account and temporary directory.
                    task["become"] = False
                    task.pop("become_user", None)
                    task.setdefault("environment", {})["PATH"] = str(binary) + ":" + os.environ["PATH"]
                    if task.get("ansible.builtin.include_tasks") == "demo_mcp_subscription.yml":
                        # RHSM routing is covered separately without registration.
                        task.pop("ansible.builtin.include_tasks")
                        task["ansible.builtin.set_fact"] = {"subscription_fixture_only": True}
                    if "ansible.builtin.dnf" in task:
                        task.pop("ansible.builtin.dnf")
                        task["ansible.builtin.set_fact"] = {"packages_fixture_only": True}
                    if "ansible.builtin.slurp" in task:
                        task["loop"] = [str(root / "subuid"), str(root / "subgid")]
                    if task.get("register") == "demo_mcp_disk_space":
                        task.pop("ansible.builtin.command")
                        task.pop("register")
                        task["ansible.builtin.set_fact"] = {"demo_mcp_disk_space": {
                            "stdout_lines": ["Filesystem 1K-blocks Used Available Use% Mounted", "fixture 0 0 8388608 0% /"]}}
                    if "ansible.builtin.git" in task:
                        task.pop("ansible.builtin.git")
                        task.pop("register")
                        source = "{{ demo_mcp_build_workspace.path }}/source"
                        task["block"] = [
                            {"name": "Create only a synthetic public source checkout", "ansible.builtin.file": {
                                "path": source, "state": "directory", "mode": "0700"}},
                            {"name": "Supply its regular public recipe", "ansible.builtin.copy": {
                                "dest": source + "/Containerfile", "content": "FROM scratch\n", "mode": "0600"}},
                            {"name": "Supply the immutable checkout result", "ansible.builtin.set_fact": {
                                "demo_mcp_source_checkout": {"after": image["revision"] if checkout_matches else "0" * 40}}},
                        ]
                    for field in ("block", "always", "rescue"):
                        prepare(task.get(field, []))

            prepare(tasks)
            playbook = root / "check.yml"
            playbook.write_text(yaml.safe_dump([{
                "name": "Exercise target-build task control flow with synthetic dependencies",
                "hosts": "localhost", "connection": "local", "gather_facts": False,
                "vars": {"demo_mcp_user": user, "demo_mcp_image": image}, "tasks": tasks,
            }], sort_keys=False))
            environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(root / "local"),
                               ANSIBLE_REMOTE_TEMP=str(root / "remote"),
                               ANSIBLE_FILTER_PLUGINS=str(ROOT / "playbooks/filter_plugins"), ANSIBLE_NOCOLOR="1")
            result = subprocess.run([sys.executable, "-m", "ansible.cli.playbook", "-i", "localhost,", str(playbook)],
                                    env=environment, text=True, capture_output=True, timeout=90)
            arguments = json.loads(calls.read_text()) if calls.exists() else None
            self.assertFalse(list(home.glob(".aiops-mcp-build-*")), result.stdout + result.stderr)
            self.assertTrue((home / "private-canary").exists())
            return result, arguments, revision.read_text() if revision.exists() else None

    def test_missing_image_builds_from_public_context_and_cleans_up(self):
        result, arguments, revision = self.run_runtime()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(arguments[0], "build")
        self.assertIn("org.opencontainers.image.revision=" + revision, arguments)
        self.assertNotIn("load", arguments)

    def test_matching_source_revision_skips_the_build(self):
        result, arguments, unused = self.run_runtime(existing=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIsNone(arguments)

    def test_build_failure_is_visible_and_still_removes_the_checkout(self):
        result, arguments, revision = self.run_runtime(build_succeeds=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIsNotNone(arguments)
        self.assertIsNone(revision)

    def test_wrong_checkout_commit_stops_before_building(self):
        result, arguments, revision = self.run_runtime(checkout_matches=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not return the pinned commit", result.stdout)
        self.assertIsNone(arguments)
        self.assertIsNone(revision)


if __name__ == "__main__":
    unittest.main()
