"""Exercise the real DNS task includes and URI module against a local HTTP fixture."""
import copy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.parse import parse_qs, unquote, urlsplit

os.environ.setdefault('ANSIBLE_LOCAL_TEMP', '/tmp/aap-v3-dns-unit-local')
from ansible.errors import AnsibleFilterError
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('godaddy_v3_test', ROOT / 'playbooks/filter_plugins/godaddy_v3.py')
filters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(filters)


def record(identifier='fixture/id', name='appliance.v24-test2', address='192.0.2.10', ttl=600, kind='A'):
    return {'recordId': identifier, 'name': name, 'data': address, 'ttl': ttl, 'type': kind}


def page(records, total=None, pages=1, links=None):
    return {'items': records, 'totalItems': len(records) if total is None else total,
            'totalPages': pages, 'links': links or []}


class PageValidationTests(unittest.TestCase):
    def test_complete_pages_reject_truncation_malformed_totals_and_duplicate_ids(self):
        self.assertEqual(filters.godaddy_v3_records(page([])), [])
        self.assertEqual(filters.godaddy_v3_records({'items': [], 'links': []}), [])
        for invalid in [[], {}, {'items': [], 'totalItems': 0},
                        {'items': [], 'links': [{'rel': 'next'}]},
                        {'items': [record()]}, page([record()], total=2),
                        page([record()], pages=2), page([record()], links=[{'rel': 'next'}]),
                        page([record(), record()]), page([record('..')]),
                        page([record(ttl=True)]), page([record(ttl=0)]),
                        page([], total=True), page([], pages=-1)]:
            with self.subTest(invalid=invalid), self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_records(invalid)
        for invalid in [page([record(name='other')]), page([record(kind='AAAA')])]:
            with self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_records(invalid, 'appliance.v24-test2', 'A')

    def test_accumulation_requires_sequential_stable_exact_totals_and_unique_ids(self):
        first = page([record()], total=2, pages=2, links=[{'rel': 'next'}])
        state = filters.godaddy_v3_accumulate(first, 1)
        self.assertFalse(state['complete'])
        final = filters.godaddy_v3_accumulate(page([record('second')], total=2, pages=2), 2, state)
        self.assertTrue(final['complete'])
        self.assertEqual(len(final['records']), 2)
        for value, number in [(page([record('second')], total=3, pages=2), 2),
                              (page([record()], total=2, pages=2), 2),
                              (page([], total=2, pages=2), 2),
                              (page([record('second')], total=2, pages=2), 3),
                              (page([record('second')], total=2, pages=2,
                                    links=[{'rel': 'next'}]), 2)]:
            with self.subTest(value=value, number=number), self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_accumulate(value, number, state)
        self.assertTrue(filters.godaddy_v3_accumulate(page([], pages=0), 1)['complete'])
        self.assertTrue(filters.godaddy_v3_accumulate({'items': [], 'links': []}, 1)['complete'])


LEAF = 'appliance.v24-test2.example.invalid'
NAMES = ['ns1.example.invalid', 'ns2.example.invalid']
IPS = ['192.0.2.53', '192.0.2.54']
EXPECTED = '192.0.2.10'


def response(question=LEAF, kind='A', data=None, status='NOERROR', flags='qr aa', server=IPS[0], records=None):
    if records is None:
        records = [(question, kind, EXPECTED if data is None else data)] if status == 'NOERROR' else []
    return {'rc': 0, 'stdout': '\n'.join([
        ';; ->>HEADER<<- opcode: QUERY, status: ' + status + ', id: 11',
        ';; flags: ' + flags + '; QUERY: 1, ANSWER: ' + str(len(records)) + ', AUTHORITY: 0, ADDITIONAL: 0',
        ';; QUESTION SECTION:', ';' + question + '. IN ' + kind, '', ';; ANSWER SECTION:',
        *[name + '. 600 IN ' + rtype + ' ' + value for name, rtype, value in records],
        '', ';; SERVER: ' + server + '#53(' + server + ') (UDP)', ''])}


class ParserTests(unittest.TestCase):
    def test_exact_response_requires_real_AA_question_status_and_direct_owned_A(self):
        good = response()
        self.assertEqual(filters.godaddy_v3_dns_response(good, LEAF, 'A', True, IPS[0]), [EXPECTED])
        referral = response(flags='qr', records=[])
        referral['stdout'] = referral['stdout'].replace('AUTHORITY: 0', 'AUTHORITY: 1').replace(
            ';; SERVER:', ';; AUTHORITY SECTION:\nexample.invalid. 600 IN NS ns1.example.invalid.\n;; SERVER:')
        invalid = [response(status='NXDOMAIN'), response(flags='qr'), response(flags='qr aa tc'),
                   referral,
                   response(flags='qr aa rd'), response(question='other.example.invalid'),
                   response(server=IPS[1]), response(records=[(LEAF, 'CNAME', 'alias.example.invalid')]),
                   response(records=[('other.example.invalid', 'A', EXPECTED)]),
                   response(records=[]), {'rc': 9, 'stdout': ''}, {'rc': False, 'stdout': good['stdout']},
                   {'rc': 0, 'stdout': good['stdout'].replace('ANSWER: 1', 'ANSWER: 2')},
                   {'rc': 0, 'stdout': good['stdout'].replace('; QUERY: 1', '; QUERY: 2')},
                   {'rc': 0, 'stdout': 'malformed'}, {'rc': 0, 'stdout': good['stdout'] * 2}]
        for value in invalid:
            with self.subTest(value=value), self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_dns_response(value, LEAF, 'A', True, IPS[0])

    def test_public_apex_NS_must_match_provider_and_all_NS_addresses_are_retained(self):
        records = [record(str(i), '@', name, kind='NS') for i, name in enumerate(NAMES)]
        ns = response('example.invalid', 'NS', flags='qr rd ra', server='8.8.8.8',
                      records=[('example.invalid', 'NS', name) for name in NAMES])
        self.assertEqual(filters.godaddy_v3_dns_nameservers(records, ns, 'example.invalid'), NAMES)
        with self.assertRaises(AnsibleFilterError):
            filters.godaddy_v3_dns_nameservers(records[:1], ns, 'example.invalid')
        resolved = [dict(response(name, 'A', data=ip, flags='qr rd ra', server='8.8.8.8'), item=name)
                    for name, ip in zip(NAMES, IPS)]
        self.assertEqual(filters.godaddy_v3_dns_endpoints(resolved, NAMES),
                         [{'nameserver': n, 'address': i} for n, i in zip(NAMES, IPS)])
        with self.assertRaises(AnsibleFilterError):
            filters.godaddy_v3_dns_endpoints(resolved[:1], NAMES)

    def test_round_requires_all_authorities_and_rejects_wrong_IP_or_incomplete_observations(self):
        endpoints = [{'nameserver': n, 'address': i} for n, i in zip(NAMES, IPS)]
        good = [dict(response(server=ip), item=endpoint) for endpoint, ip in zip(endpoints, IPS)]
        self.assertTrue(filters.godaddy_v3_dns_authority_round(good, endpoints, LEAF, EXPECTED)['ready'])
        for bad in [response(server=IPS[1], status='NXDOMAIN'), response(server=IPS[1], data='192.0.2.99'),
                    response(server=IPS[1], flags='qr'), response(server=IPS[1], question='other.example.invalid')]:
            changed = copy.deepcopy(good)
            changed[1] = dict(bad, item=endpoints[1])
            self.assertFalse(filters.godaddy_v3_dns_authority_round(changed, endpoints, LEAF, EXPECTED)['ready'])
        with self.assertRaises(AnsibleFilterError):
            filters.godaddy_v3_dns_authority_round(good[:1], endpoints, LEAF, EXPECTED)


DIG_STUB = r'''import sys,os,json
from pathlib import Path
p=Path(os.environ['FIXTURE_AUTHORITY_STATE']);s=json.loads(p.read_text());args=sys.argv[1:]
server=next(x[1:]for x in args if x.startswith('@'));name=next(x for x in args if x.endswith('.')and not x.startswith('@')).rstrip('.');kind=args[args.index(name+'.')+1]
s['calls'].append({'server':server,'name':name,'kind':kind,'norecurse':'+norecurse'in args})
flags='qr rd ra';status='NOERROR';rows=[];question=name
names=['ns1.example.invalid','ns2.example.invalid'];ips=['192.0.2.53','192.0.2.54'];leaf='appliance.v24-test2.example.invalid'
if server=='8.8.8.8'and name=='example.invalid'and kind=='NS':
 rows=[('example.invalid','NS',n)for n in names]
 if s.get('mismatch'):rows=rows[:1]
elif server=='8.8.8.8'and name in names and kind=='A':rows=[(name,'A',ips[names.index(name)])]
elif name==leaf and kind=='A'and server in ips:
 assert '+norecurse'in args
 flags='qr aa';s['counts'][server]=s['counts'].get(server,0)+1
 ok=s['counts'][server]>=s['ready_after'].get(server,1)
 if not ok:status='NXDOMAIN'
 else:rows=[(leaf,'A','192.0.2.10')]
 s['latest'][server]=ok
elif server=='8.8.8.8'and name==leaf and kind=='A':
 s['premature_recursive']=not all(s['latest'].get(ip,False)for ip in ips)
 p.write_text(json.dumps(s));print('192.0.2.10');raise SystemExit(0)
else:raise SystemExit(74)
p.write_text(json.dumps(s))
print(';; ->>HEADER<<- opcode: QUERY, status: '+status+', id: 11')
print(';; flags: '+flags+'; QUERY: 1, ANSWER: '+str(len(rows))+', AUTHORITY: 0, ADDITIONAL: 0')
print(';; QUESTION SECTION:');print(';'+question+'. IN '+kind);print('');print(';; ANSWER SECTION:')
for owner,typ,value in rows:print(owner+'. 600 IN '+typ+' '+value)
print('');print(';; SERVER: '+server+'#53('+server+') (UDP)')
'''

class NativeTaskTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.executable = os.environ.get('ANSIBLE_PLAYBOOK') or shutil.which('ansible-playbook')
        if not cls.executable:
            raise unittest.SkipTest('Native ansible-playbook is unavailable; no dependencies installed')
        cls.state = {}
        class API(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, status, data=None):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json')
                if status == 302:
                    self.send_header('Location', '/must-not-follow')
                self.end_headers()
                if data is not None:
                    self.wfile.write(json.dumps(data).encode())

            def do_GET(self):
                parsed = urlsplit(self.path)
                q = parse_qs(parsed.query)
                cls.state['calls'].append(('GET', self.path, None))
                if cls.state.get('get_error'):
                    return self.send(cls.state['get_error'], {'error': 'fixture refusal'})
                if cls.state.get('replace_on_recheck') and len(cls.state['calls']) == 4:
                    for value in cls.state['records']:
                        if value['type'] == 'A' and value['name'] == 'appliance.v24-test2':
                            value['recordId'] = 'different-owner-id'
                values = copy.deepcopy(cls.state['records'])
                if 'name' in q:
                    values = [r for r in values if r['name'] == q['name'][0] and r['type'] == q['type'][0]]
                    body = page(values)
                    if not values:
                        body = {'items': [], 'links': []}
                    if cls.state.get('filtered_truncated'):
                        body['totalItems'] = len(values) + 1
                        body['totalPages'] = 2
                else:
                    number = int(q['page'][0])
                    size = cls.state.get('page_size', 100)
                    body = page(values[(number-1)*size:number*size], total=len(values),
                                pages=max(1, (len(values)+size-1)//size))
                    if number > 1 and cls.state.get('duplicate_page'):
                        body['items'] = values[:size]
                    if cls.state.get('truncated_total'):
                        body['totalItems'] += 1
                    if not values:
                        body = {'items': [], 'links': []}
                self.send(200, body)

            def body(self):
                return json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))

            def do_POST(self):
                body = self.body()
                cls.state['calls'].append(('POST', self.path, body))
                new = dict(body, recordId='created/id')
                cls.state['records'].append(new)
                self.send(cls.state.get('post_status', 201), new)

            def do_PUT(self):
                body = self.body()
                cls.state['calls'].append(('PUT', self.path, body))
                identifier = unquote(urlsplit(self.path).path.split('/dns-records/', 1)[1])
                for i, old in enumerate(cls.state['records']):
                    if old['recordId'] == identifier:
                        cls.state['records'][i] = dict(body, recordId=identifier)
                        return self.send(200, cls.state['records'][i])
                self.send(404)

            def do_DELETE(self):
                cls.state['calls'].append(('DELETE', self.path, None))
                identifier = unquote(urlsplit(self.path).path.split('/dns-records/', 1)[1])
                matches = [r for r in cls.state['records'] if r['recordId'] == identifier]
                cls.state['records'][:] = [r for r in cls.state['records'] if r['recordId'] != identifier]
                self.send(404 if cls.state.get('delete_race') or not matches else 204)
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), API)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        self.state.clear()
        self.state.update(records=[record('ns1', '@', 'ns1.example.invalid', kind='NS'),
                                   record('ns2', '@', 'ns2.example.invalid', kind='NS')], calls=[])

    def run_tasks(self, tasks, check=False, **overrides):
        values = {'demo_public_dns_config': {'zone': 'example.invalid', 'record_name': 'appliance.v24-test2',
                  'hostname': 'appliance.v24-test2.example.invalid', 'hypervisor': {'public_ipv4': '192.0.2.10'}},
                  'demo_public_dns_api_token': 'fixture-not-a-secret',
                  'demo_public_dns_authority_max_rounds': 3, 'demo_public_dns_authority_poll_delay': 0,
                  'demo_public_dns_authority_timeout': 60}
        values.update(overrides.pop('values', {}))
        values.update(overrides)
        with tempfile.TemporaryDirectory(prefix='aap-v3-dns-native-') as folder:
            folder = Path(folder)
            fixture_tasks = folder / 'tasks'
            fixture_tasks.mkdir()
            for source in (ROOT / 'playbooks/tasks').glob('demo_public_dns*.yml'):
                # Fixture-only transport substitution; production has a fixed HTTPS origin.
                copied = source.read_text().replace('https://api.godaddy.com',
                                                    'http://127.0.0.1:' + str(self.server.server_port))
                (fixture_tasks / source.name).write_text(copied)
            tasks = copy.deepcopy(tasks)
            for task in tasks:
                include = task.get('ansible.builtin.include_tasks')
                if isinstance(include, str) and include.startswith(str(ROOT / 'playbooks/tasks') + '/'):
                    task['ansible.builtin.include_tasks'] = str(fixture_tasks / Path(include).name)
            state_path = folder / 'dns-state.json'
            state_path.write_text(json.dumps({'calls': [], 'counts': {}, 'latest': {},
                'ready_after': self.state.get('ready_after', {}), 'mismatch': self.state.get('mismatch', False)}))
            executable = folder / 'dig'
            executable.write_text('#!' + sys.executable + '\n' + DIG_STUB)
            executable.chmod(0o700)
            play = folder / 'play.yml'
            play.write_text(yaml.safe_dump([{'hosts': 'localhost', 'connection': 'local',
                                            'gather_facts': False, 'vars': values, 'tasks': tasks}], sort_keys=False))
            cfg = folder / 'ansible.cfg'
            cfg.write_text('[defaults]\nfilter_plugins=' + str(ROOT / 'playbooks/filter_plugins') + '\n')
            command = [self.executable, '-i', 'localhost,', str(play)]
            if check:
                command.append('--check')
            result = subprocess.run(command,
                                  capture_output=True, text=True, timeout=90,
                                  env=dict(os.environ, PATH=str(folder)+os.pathsep+os.environ['PATH'],
                                           FIXTURE_AUTHORITY_STATE=str(state_path),
                                           ANSIBLE_CONFIG=str(cfg), ANSIBLE_NOCOLOR='1',
                                           ANSIBLE_LOCAL_TEMP=str(folder / 'local'),
                                           ANSIBLE_REMOTE_TEMP=str(folder / 'remote')))
            self.state['dns'] = json.loads(state_path.read_text())
            return result

    def reconcile(self):
        return self.run_tasks([{'ansible.builtin.include_tasks': str(ROOT / 'playbooks/tasks/demo_public_dns.yml')}])

    def retire(self, **overrides):
        return self.run_tasks([{'ansible.builtin.include_tasks': str(ROOT / 'playbooks/tasks/demo_public_dns_delete.yml')}],
                              demo_public_dns_delete_confirm='appliance.v24-test2.example.invalid', **overrides)

    def writes(self):
        return [x for x in self.state['calls'] if x[0] != 'GET']

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def selected(self):
        return [r for r in self.state['records'] if r['name'] == 'appliance.v24-test2']

    def test_create_repeat_ttl_update_and_delete_preserve_unrelated_zone_records(self):
        unrelated = record('unrelated', 'other', '192.0.2.20')
        self.state['records'].append(unrelated)
        baseline = copy.deepcopy(self.state['records'])
        self.assert_ok(self.reconcile())
        self.assertEqual([x[0] for x in self.writes()], ['POST'])
        self.assert_ok(self.reconcile())
        self.assertEqual([x[0] for x in self.writes()], ['POST'])
        self.selected()[0]['ttl'] = 3600
        self.assert_ok(self.reconcile())
        self.assertEqual([x[0] for x in self.writes()], ['POST', 'PUT'])
        self.assertIn('created%2Fid', self.writes()[-1][1])
        self.assert_ok(self.retire())
        self.assertEqual(self.state['records'], baseline)
        self.assert_ok(self.retire())
        self.assertEqual([x[0] for x in self.writes()], ['POST', 'PUT', 'DELETE'])
        self.assertIn('created%2Fid', self.writes()[-1][1])

    def test_conflicting_address_alias_ipv6_duplicate_and_truncated_pages_stop_before_writes(self):
        base = copy.deepcopy(self.state['records'])
        for records in [[record(address='192.0.2.20')],
                        [record(kind='AAAA', address='2001:db8::1')],
                        [record(kind='CNAME', address='other.example.invalid')],
                        [record(), record('second')]]:
            with self.subTest(records=records):
                self.state.update(records=base+records, calls=[])
                self.assertNotEqual(self.reconcile().returncode, 0)
                self.assertEqual(self.writes(), [])
                self.assertEqual(self.state['dns']['calls'], [])
        self.state.update(records=base, calls=[], filtered_truncated=True)
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertEqual(self.writes(), [])

    def test_uncertain_POST_is_never_replayed_and_retains_created_record_for_reconciliation(self):
        self.state['post_status'] = 500
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertEqual([x[0] for x in self.writes()], ['POST'])
        self.assertEqual(len(self.selected()), 1)
        self.assertEqual(self.state['dns']['calls'], [])

    def test_provider_redirect_or_authentication_error_never_queries_DNS_or_writes(self):
        for status in (302, 401):
            with self.subTest(status=status):
                self.state.update(get_error=status, calls=[])
                self.assertNotEqual(self.reconcile().returncode, 0)
                self.assertEqual(self.writes(), [])
                self.assertFalse(any('/must-not-follow' in x[1] for x in self.state['calls']))
                self.assertEqual(self.state['dns']['calls'], [])

    def test_changed_record_ID_between_preimage_and_recheck_refuses_deletion(self):
        self.state['records'].append(record())
        self.state['replace_on_recheck'] = True
        self.assertNotEqual(self.retire().returncode, 0)
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.selected()[0]['recordId'], 'different-owner-id')

    def test_delete_confirmation_and_foreign_address_are_required(self):
        tasks = [{'ansible.builtin.include_tasks': str(ROOT / 'playbooks/tasks/demo_public_dns_delete.yml')}]
        self.assertNotEqual(self.run_tasks(tasks, demo_public_dns_delete_confirm='other.example.invalid').returncode, 0)
        self.assertEqual(self.state['calls'], [])
        self.state['records'].append(record(address='192.0.2.99'))
        self.assertNotEqual(self.retire().returncode, 0)
        self.assertEqual(self.writes(), [])

    def test_already_deleted_race_is_read_back_and_idempotent(self):
        self.state['records'].append(record())
        self.state['delete_race'] = True
        self.assert_ok(self.retire())
        self.assertEqual(self.selected(), [])
        self.assertEqual([x[0] for x in self.writes()], ['DELETE'])

    def public_gate(self):
        return {'name': 'Fixture final recursive selected-name gate',
                'ansible.builtin.command': {'argv': ['dig', '-r', '@8.8.8.8',
                    'appliance.v24-test2.example.invalid.', 'A']},
                'changed_when': False}

    def test_negative_authorities_converge_before_the_first_recursive_leaf_query(self):
        self.state['ready_after'] = {'192.0.2.53': 1, '192.0.2.54': 2}
        self.assert_ok(self.run_tasks([
            {'ansible.builtin.include_tasks': str(ROOT / 'playbooks/tasks/demo_public_dns.yml')},
            self.public_gate()]))
        dns = self.state['dns']
        direct = [x for x in dns['calls'] if x['server'] in ['192.0.2.53', '192.0.2.54']]
        self.assertEqual(len(direct), 4)
        self.assertTrue(all(x['norecurse'] for x in direct))
        self.assertFalse(dns['premature_recursive'])
        self.assertEqual(dns['calls'][-1]['name'], 'appliance.v24-test2.example.invalid')
        self.assertEqual(dns['calls'][-1]['server'], '8.8.8.8')
        self.assertFalse(any(x['name'] == 'v24-test2.example.invalid' for x in dns['calls']))

    def test_authority_exhaustion_prevents_recursive_leaf_and_preserves_provider_record(self):
        self.state['ready_after'] = {'192.0.2.53': 99, '192.0.2.54': 99}
        result = self.run_tasks([
            {'ansible.builtin.include_tasks': str(ROOT / 'playbooks/tasks/demo_public_dns.yml')},
            self.public_gate()], demo_public_dns_authority_max_rounds=2)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len([x for x in self.state['dns']['calls'] if x['server'] != '8.8.8.8']), 4)
        self.assertFalse(any(x['server'] == '8.8.8.8' and x['name'].startswith('appliance.')
                             for x in self.state['dns']['calls']))
        self.assertEqual(len(self.selected()), 1)
        self.assertEqual([x[0] for x in self.writes()], ['POST'])

    def test_nameserver_disagreement_never_queries_the_selected_leaf(self):
        self.state['mismatch'] = True
        self.assertNotEqual(self.reconcile().returncode, 0)
        self.assertTrue(all(x['name'] == 'example.invalid' for x in self.state['dns']['calls']))

    def test_check_mode_reads_preimage_but_never_writes_or_queries_leaf(self):
        self.assert_ok(self.run_tasks([
            {'ansible.builtin.include_tasks': str(ROOT / 'playbooks/tasks/demo_public_dns.yml')}], check=True))
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.state['dns']['calls'], [])
        self.state['records'].append(record())
        self.assert_ok(self.retire(check=True))
        self.assertEqual(self.writes(), [])
        self.assertEqual(self.state['dns']['calls'], [])
        self.assertEqual(len(self.selected()), 1)


class SelectedIdentityTests(unittest.TestCase):
    def test_selected_zone_record_and_hostname_must_match_exactly(self):
        config = {'zone': 'example.invalid', 'record_name': 'appliance.v24-test2',
                  'hostname': 'appliance.v24-test2.example.invalid',
                  'hypervisor': {'public_ipv4': '192.0.2.10'}}
        self.assertEqual(filters.godaddy_v3_selected_config(config), config)
        for change in [{'record_name': '@'}, {'record_name': '../foreign'},
                       {'hostname': 'other.example.invalid'}, {'zone': 'other.invalid'},
                       {'zone': 'example.invalid/other'}, {'hypervisor': {'public_ipv4': 'bad'}}]:
            with self.subTest(change=change), self.assertRaises(AnsibleFilterError):
                filters.godaddy_v3_selected_config(dict(config, **change))


if __name__ == '__main__':
    unittest.main()
