"""Refuse foreign RHSM consumers and preserve uncertain unregister outcomes."""
import copy
import importlib.util
from pathlib import Path
import unittest

from ansible.errors import AnsibleFilterError
from test_mcp_deployment import deployment

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('tested_subscription_owner', ROOT / 'playbooks/filter_plugins/demo_subscription.py')
owner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(owner)
CONSUMER = '11111111-2222-4333-8444-555555555555'


class SubscriptionOwnershipTests(unittest.TestCase):
    def setUp(self):
        value = deployment()
        value.pop('testserver')
        self.config = owner.configuration(value)
        self.registered = {'registered': True, 'consumer_uuid': CONSUMER, 'consumer_name': 'tra-v07'}
        self.absent = {'registered': False, 'consumer_uuid': None, 'consumer_name': None}

    def test_partial_deployment_needs_only_the_exact_tra(self):
        self.assertEqual(self.config['tra']['vm_name'], 'tra-v07')
        self.assertNotIn('testserver', self.config)

    def test_native_identity_binds_current_consumer_name_and_uuid(self):
        result = {'rc': 0, 'stdout': 'system identity: ' + CONSUMER + '\nname: tra-v07\norg ID: synthetic\n'}
        self.assertEqual(owner.identity(result, self.config), self.registered)
        for old, new in [('tra-v07', 'golden-image'), ('tra-v07', 'tra-v08'), (CONSUMER, '00000000-0000-0000-0000-000000000000')]:
            bad = copy.deepcopy(result)
            bad['stdout'] = bad['stdout'].replace(old, new)
            with self.subTest(new=new), self.assertRaises(AnsibleFilterError):
                owner.identity(bad, self.config)

    def test_error_is_not_native_absence(self):
        self.assertEqual(owner.identity({'rc': 1, 'stdout': 'This system is not yet registered. Try register.'}, self.config), self.absent)
        for result in [{'rc': 1, 'stderr': 'Network failure'}, {'rc': True, 'stdout': 'This system is not yet registered.'}]:
            with self.assertRaises(AnsibleFilterError):
                owner.identity(result, self.config)

    def test_existing_unowned_registration_is_neither_claimed_nor_unregistered(self):
        with self.assertRaises(AnsibleFilterError):
            owner.before_registration(self.registered, None, self.config)
        with self.assertRaises(AnsibleFilterError):
            owner.before_retirement(self.registered, None, self.config)
        self.assertTrue(owner.before_registration(self.absent, None, self.config))
        self.assertTrue(owner.before_retirement(self.absent, None, self.config))

    def test_current_matching_owner_can_be_reused_and_retired(self):
        receipt = owner.owner(self.config, CONSUMER)
        self.assertTrue(owner.before_registration(self.registered, receipt, self.config))
        self.assertTrue(owner.before_retirement(self.registered, receipt, self.config))

    def test_copied_consumer_or_vm_receipt_is_never_reused(self):
        good = owner.owner(self.config, CONSUMER)
        for field, value in [('consumer_uuid', '99999999-2222-4333-8444-555555555555'),
                             ('guest_uuid', '99999999-2222-4333-8444-555555555555'),
                             ('guest_name', 'tra-v08'), ('machine_id', '9' * 32), ('instance_name', 'aap27-test-8')]:
            bad = copy.deepcopy(good)
            bad[field] = value
            for operation in [owner.before_registration, owner.before_retirement]:
                with self.subTest(field=field, operation=operation.__name__), self.assertRaises(AnsibleFilterError):
                    operation(self.registered, bad, self.config)

    def test_crash_after_unregister_before_receipt_is_ambiguous_and_retains_owner(self):
        receipt = owner.owner(self.config, CONSUMER)
        original = copy.deepcopy(receipt)
        with self.assertRaisesRegex(AnsibleFilterError, 'recover the original native job evidence'):
            owner.before_retirement(self.absent, receipt, self.config)
        self.assertEqual(receipt, original)

    def test_verified_retirement_is_idempotent_but_cannot_silently_reregister(self):
        receipt = owner.owner(self.config, CONSUMER, retired=True)
        self.assertTrue(owner.before_retirement(self.absent, receipt, self.config))
        with self.assertRaises(AnsibleFilterError):
            owner.before_registration(self.absent, receipt, self.config)
        with self.assertRaises(AnsibleFilterError):
            owner.before_retirement(self.registered, receipt, self.config)


class RegistrationReceiptOrderingTests(unittest.TestCase):
    def test_repository_failure_keeps_real_atomic_receipt_and_allows_owned_retry(self):
        """Execute the production post-register tasks with synthetic native identity.

        Only the external identity read and repository call are substituted;
        real filters and the native atomic receipt-writing tasks still run.
        """
        import json
        import os
        import subprocess
        import sys
        import tempfile
        import yaml
        with tempfile.TemporaryDirectory(prefix='subscription-repository-failure-') as temp:
            folder = Path(temp)
            selected = owner.configuration(deployment())
            selected['registration_name'] = selected['tra']['vm_name']
            tasks = yaml.safe_load((ROOT / 'playbooks/tasks/demo_mcp_subscription.yml').read_text())[0]['block']
            start = next(index for index, task in enumerate(tasks) if 'demo_subscription_registered_identity' == task.get('register'))
            sequence = copy.deepcopy(tasks[start:])
            self.assertEqual(sequence[-1]['redhat.rhel_system_roles.rhsm_repository']['purge'], False)
            sequence[0] = {'name': 'Use the actual successful registration identity fixture', 'ansible.builtin.set_fact': {
                'demo_subscription_registered_identity': {'rc': 0, 'stdout': 'system identity: ' + CONSUMER + '\nname: ' + selected['tra']['vm_name'] + '\n'}}}
            writer = copy.deepcopy(yaml.safe_load((ROOT / 'playbooks/tasks/demo_subscription_owner_write.yml').read_text()))
            target = str(folder / 'receipt')
            for task in writer:
                for action in ('ansible.builtin.stat', 'ansible.builtin.file', 'ansible.builtin.copy'):
                    if action in task:
                        for field in ('path', 'dest'):
                            if field in task[action]:
                                task[action][field] = task[action][field].replace('/var/lib/aiops-selfhealing', target)
                        task[action].pop('owner', None)
                        task[action].pop('group', None)
                if 'ansible.builtin.assert' in task:
                    task['ansible.builtin.assert']['that'] = task['ansible.builtin.assert']['that'].replace('== 0', '== ' + str(os.getuid()))
            writer_path = folder / 'writer.yml'
            writer_path.write_text(yaml.safe_dump(writer, sort_keys=False))
            for task in sequence:
                if task.get('ansible.builtin.include_tasks') == 'demo_subscription_owner_write.yml':
                    task['ansible.builtin.include_tasks'] = str(writer_path)
            sequence[-1] = {'name': 'Simulate repository enable failure after successful native registration',
                            'ansible.builtin.fail': {'msg': 'synthetic repository failure'}}
            play = [{'hosts': 'localhost', 'connection': 'local', 'gather_facts': False,
                     'vars': {'demo_subscription_config': selected}, 'tasks': [
                         {'block': sequence, 'rescue': [{'ansible.builtin.debug': {'msg': 'Repository failure retained for retry'}}]},
                         {'ansible.builtin.set_fact': {'saved_receipt': '{{ lookup("ansible.builtin.file", ' + json.dumps(target + '/subscription-owner.json') + ') | from_json }}'}},
                         {'ansible.builtin.assert': {'that': 'demo_subscription_registered | demo_subscription_before_registration(saved_receipt, demo_subscription_config)', 'quiet': True}}]}]
            source = folder / 'check.yml'
            source.write_text(yaml.safe_dump(play, sort_keys=False))
            environment = dict(os.environ, ANSIBLE_LOCAL_TEMP=str(folder / 'local'), ANSIBLE_REMOTE_TEMP=str(folder / 'remote'),
                               ANSIBLE_FILTER_PLUGINS=str(ROOT / 'playbooks/filter_plugins'), ANSIBLE_NOCOLOR='1')
            result = subprocess.run([sys.executable, '-m', 'ansible.cli.playbook', '-i', 'localhost,', str(source)],
                                    env=environment, capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = json.loads((Path(target) / 'subscription-owner.json').read_text())
            self.assertEqual(receipt['consumer_uuid'], CONSUMER)
            self.assertIs(receipt['retired'], False)
