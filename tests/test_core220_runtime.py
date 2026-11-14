"""Exercise native tagged data and DNS-tool output without hosts or services."""

import importlib.util
import os
from pathlib import Path
import unittest
import yaml

os.environ.setdefault('ANSIBLE_LOCAL_TEMP', '/tmp/aiops-core220-tests-local')

from ansible.errors import AnsibleFilterError
from ansible.parsing.yaml.loader import AnsibleLoader
from ansible.parsing.dataloader import DataLoader
from ansible.plugins.loader import filter_loader
from ansible.template import Templar, trust_as_template


ROOT = Path(__file__).resolve().parents[1]


def plugin(name):
    spec = importlib.util.spec_from_file_location('core220_' + name, ROOT / 'playbooks/filter_plugins' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RUNTIME = plugin('demo_runtime')
MCP = plugin('demo_mcp')
CLAUDE = plugin('demo_claude')
WEBSITE = plugin('demo_website')
ZABBIX = plugin('demo_zabbix')


class TaggedRuntimeTests(unittest.TestCase):
    def test_native_import_binding_ids_are_accepted_and_booleans_refused(self):
        value = {
            'instance_name': 'aap27-test-7', 'instance_number': 7,
            'aap_fqdn': 'aap27.v07.example.invalid', 'zone': 'example.invalid',
            'cac_import': {'controller_host': 'https://aap27.v07.example.invalid',
                           'inventory_id': 101, 'job_template_id': 102, 'group_id': 103,
                           'aap_instance_key': 'aap27-v07'},
            'hypervisor': {'name': 'recovery', 'address': '192.0.2.50', 'public_ipv4': '8.8.8.8',
                           'user': 'automation', 'port': 22, 'machine_id': '1' * 32,
                           'host_keys': ['ssh-ed25519 AAAA']},
            'source_image': {'path': '/opt/vms/zabbix-disk.qcow2', 'sha256': 'a' * 64},
            'vm_network': 'isolated',
            'testserver': {'verified': True, 'vm_name': 'testserver1-v07', 'address': '192.0.2.124',
                           'uuid': '22222222-2222-2222-2222-222222222222', 'machine_id': '2' * 32,
                           'hypervisor_machine_id': '1' * 32, 'user': 'automation', 'port': 22,
                           'host_keys': ['ssh-ed25519 AAAA']},
        }
        loaded = AnsibleLoader(yaml.safe_dump(value)).get_single_data()
        self.assertEqual(ZABBIX.configuration(loaded)['cac_import']['inventory_id'], 101)
        for key in ('inventory_id', 'job_template_id', 'group_id'):
            original = loaded['cac_import'][key]
            loaded['cac_import'][key] = True
            with self.subTest(field=key), self.assertRaises(AnsibleFilterError):
                ZABBIX.configuration(loaded)
            loaded['cac_import'][key] = original

    def test_native_schema_integer_is_accepted_and_secret_remains_literal(self):
        data = AnsibleLoader('schema_version: 1\ninstances:\n  aap27-test-19:\n    hactar_source_git_token: !unsafe "{{ forbidden_secret }}"\n').get_single_data()
        result = RUNTIME.selected_settings(data, 'aap27-test-19')
        self.assertEqual(Templar(variables={'forbidden_secret': 'must-not-expand'}).template(result),
                         {'hactar_source_git_token': '{{ forbidden_secret }}'})
        for invalid in (True, False, 0, '1'):
            data['schema_version'] = invalid
            with self.subTest(value=invalid), self.assertRaises(AnsibleFilterError):
                RUNTIME.selected_settings(data, 'aap27-test-19')

    def test_native_uid_is_accepted_but_boolean_owner_is_refused(self):
        uid = AnsibleLoader('uid: 1000').get_single_data()['uid']
        self.assertTrue(MCP.safe_directories([{'stat': {'exists': False}}], uid))
        for invalid in (True, False, '1000'):
            with self.subTest(value=invalid), self.assertRaises(AnsibleFilterError):
                MCP.safe_directories([{'stat': {'exists': False}}], invalid)

    def test_native_release_size_keeps_exact_pin_and_boolean_rejection(self):
        pin = AnsibleLoader('version: 2.1.316\nplatform: linux-x64\nbytes: 4096\n').get_single_data()
        pin.update(sha256='a' * 64, url='https://downloads.claude.ai/claude-code-releases/2.1.316/linux-x64/claude')
        self.assertEqual(CLAUDE.release(pin)['bytes'], 4096)
        for invalid in (True, False, 0, '4096'):
            pin['bytes'] = invalid
            with self.subTest(value=invalid), self.assertRaises(AnsibleFilterError):
                CLAUDE.release(pin)

    def test_native_repair_identifiers_preserve_saved_target_guards(self):
        values = AnsibleLoader('inventory: 2\nproject: 3\nid: 17').get_single_data()
        row = dict(values, name='Deploy Zabbix Agent', playbook='playbooks/deploy_zabbix_agent.yml', limit='testserver1')
        row.update({name: False for name in ('ask_inventory_on_launch', 'ask_limit_on_launch',
                                           'ask_variables_on_launch', 'ask_credential_on_launch')})
        response = {'count': 1, 'next': None, 'results': [row]}
        self.assertEqual(CLAUDE.repair_template(response, values['inventory'], values['project']), 17)
        for key in ('inventory', 'project', 'id'):
            before = row[key]
            row[key] = True
            with self.subTest(field=key), self.assertRaises(AnsibleFilterError):
                CLAUDE.repair_template(response, row['inventory'], row['project'])
            row[key] = before


NAMES = ['website.v19.example.invalid', 'aap.v19.example.invalid']
ADDRESS = '192.0.2.200'


def answer(name, kind, records=None, status='NOERROR'):
    # BIND comments can include an OPT pseudo-section; it is not a question or
    # an answer. The same fixed output format is requested by the native task.
    lines = [f';; ->>HEADER<<- opcode: QUERY, status: {status}, id: 7',
             ';; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1',
             ';; OPT PSEUDOSECTION:', '; EDNS: version: 0, flags:; udp: 1232',
             ';; QUESTION SECTION:', f';{name}. IN {kind}', ';; ANSWER SECTION:']
    lines.extend(f'{name}. 300 IN {kind} {value}' for value in (records or []))
    return '\n'.join(lines) + '\n'


def batch():
    return ''.join(answer(name, kind, [ADDRESS] if kind == 'A' else [])
                   for name in NAMES for kind in ('A', 'AAAA'))


class NativeDnsBatchTests(unittest.TestCase):
    def test_actual_tasks_keep_one_batch_and_the_existing_whole_probe_budgets(self):
        loader = DataLoader()
        filter_loader.add_directory(str(ROOT / 'playbooks/filter_plugins'))
        for role, filename, budget in (
                ('website', 'demo_website_infrastructure.yml', 30),
                ('zabbix', 'demo_zabbix_frontend.yml', 65)):
            source = loader.load_from_file(str(ROOT / 'playbooks/tasks' / filename))
            probe = next(child for task in source for child in task.get('block', [])
                         if child.get('name') == 'Wait for public DNS to identify only the selected hypervisor')
            self.assertEqual((probe['retries'], probe['delay']), (budget, 10))
            self.assertNotIn('loop', probe)
            config = {'hostname': NAMES[0], 'aap_hostname': NAMES[1],
                      'hypervisor': {'public_ipv4': ADDRESS}}
            name = 'demo_' + role + '_dns_propagation'
            values = {'demo_' + role + '_config': config, name: {'rc': 0, 'stdout': batch()}}
            templar = Templar(loader=loader, variables=values)
            argv = templar.template([trust_as_template(value)
                                     for value in probe['ansible.builtin.command']['argv']])
            self.assertEqual(argv[-8:], [NAMES[0] + '.', 'A', NAMES[0] + '.', 'AAAA',
                                         NAMES[1] + '.', 'A', NAMES[1] + '.', 'AAAA'])
            self.assertFalse(templar.evaluate_conditional(trust_as_template(probe['failed_when'])))
            values[name]['rc'] = 9
            self.assertTrue(Templar(loader=loader, variables=values).evaluate_conditional(trust_as_template(probe['failed_when'])))

    def test_exact_batch_succeeds_and_duplicate_identical_answers_are_allowed(self):
        self.assertTrue(WEBSITE.dns_batch_ready(batch(), NAMES, ADDRESS))
        doubled = batch().replace(f'{NAMES[0]}. 300 IN A {ADDRESS}',
                                 f'{NAMES[0]}. 300 IN A {ADDRESS}\n{NAMES[0]}. 100 IN A {ADDRESS}')
        self.assertTrue(WEBSITE.dns_batch_ready(doubled, NAMES, ADDRESS))

    def test_missing_extra_wrong_or_ipv6_answers_fail_closed(self):
        cases = [batch().replace(ADDRESS, '192.0.2.201', 1),
                 batch().replace(f'{NAMES[0]}. 300 IN A {ADDRESS}', ''),
                 batch() + answer(NAMES[0], 'A', [ADDRESS]),
                 batch().replace(answer(NAMES[0], 'AAAA'), answer(NAMES[0], 'AAAA', ['2001:db8::1'])),
                 batch().replace(f';{NAMES[0]}. IN A', ';other.example.invalid. IN A', 1),
                 '', batch().split(';; ->>HEADER<<-')[1]]
        for text in cases:
            with self.subTest(output=text):
                self.assertFalse(WEBSITE.dns_batch_ready(text, NAMES, ADDRESS))

    def test_failed_ipv6_query_never_counts_as_no_ipv6_route(self):
        for status in ('SERVFAIL', 'NXDOMAIN', 'REFUSED'):
            text = batch().replace(answer(NAMES[0], 'AAAA'), answer(NAMES[0], 'AAAA', status=status))
            with self.subTest(status=status):
                self.assertFalse(WEBSITE.dns_batch_ready(text, NAMES, ADDRESS))


if __name__ == '__main__':
    unittest.main()
