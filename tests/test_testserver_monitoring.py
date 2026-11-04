"""Verify selected Linux monitoring without copied Apache checks or AI inference."""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from ansible.errors import AnsibleFilterError
import yaml
import test_versioned_zabbix as versioned

deployment, policy = versioned.deployment, versioned.policy

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('testserver_policy', ROOT / 'playbooks/filter_plugins/demo_zabbix_testserver.py')
MONITOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MONITOR)


class MonitoringApi(versioned.Api):
    def __init__(self):
        super().__init__(False)
        host=self.tables['host'][1]
        host['interfaces']=[{'interfaceid':'20','type':'1','ip':'192.0.2.124','useip':'1','dns':''}]
        self.tables['hostinterface']=host['interfaces']
        host['parentTemplates']=[{'templateid':identifier,'name':name} for identifier,name in
            [('100','Linux by Zabbix agent'),('101','ICMP Ping'),('102','Apache by HTTP')]]
        self.tables['item']=[{'itemid':identifier,'hostid':'2','key_':key,'templateid':parent,
            'status':'0','type':'0','flags':'0','value_type':'3'} for identifier,key,parent in
            [('201','agent.ping','301'),('202','system.uptime','302'),('203','icmpping','303'),('204','apache.get_status','304')]]
        self.tables['item'] += [{'itemid':identifier,'hostid':hostid,'key_':key} for identifier,hostid,key in
            [('301','100','agent.ping'),('302','100','system.uptime'),('303','101','icmpping'),('304','102','apache.get_status')]]
        self.tables['trigger']=[{'triggerid':'401','hostid':'2','templateid':'501','description':'Linux health','status':'0'},
            {'triggerid':'402','hostid':'2','templateid':'502','description':'Apache health','status':'0'},
            {'triggerid':'501','hostid':'100','description':'Linux health'},
            {'triggerid':'502','hostid':'102','description':'Apache health'}]
        self.tables['discoveryrule']=[{'itemid':'601','hostid':'2','templateid':'701','key_':'net.if.discovery','status':'0'},
            {'itemid':'602','hostid':'2','templateid':'702','key_':'apache.mpm.event.discovery','status':'0'},
            {'itemid':'701','hostid':'100','key_':'net.if.discovery'},
            {'itemid':'702','hostid':'102','key_':'apache.mpm.event.discovery'}]
        self.ids['discoveryrule']='itemid'

    def operation(self,body):
        if body['method']=='history.get':
            self.calls.append((body['method'],deepcopy(body['params'])))
            return {'result':[{'itemid':identifier,'clock':str(int(time.time())),'value':'100' if identifier=='202' else '1'}
                for identifier in body['params']['itemids']]}
        return super().operation(body)


def snapshot():
    api=MonitoringApi()
    host=deepcopy(api.tables['host'][1]);host.update(host='testserver1-v07',status='1')
    return {'host':host,
        'items':[deepcopy(row) for row in api.tables['item'] if row['hostid']=='2'],
        'triggers':[dict(deepcopy(row),hosts=[{'hostid':'2'}]) for row in api.tables['trigger'] if row['hostid']=='2'],
        'discovery_rules':[deepcopy(row) for row in api.tables['discoveryrule'] if row['hostid']=='2'],
        'template_items':[deepcopy(row) for row in api.tables['item'] if row['hostid']!='2'],
        'template_triggers':[dict(deepcopy(row),hosts=[{'hostid':row['hostid']}]) for row in api.tables['trigger'] if row['hostid']!='2'],
        'template_discovery_rules':[deepcopy(row) for row in api.tables['discoveryrule'] if row['hostid']!='2']}


class SelectedTestserverTests(unittest.TestCase):
    def test_status_only_plan_preserves_ids_and_history_and_is_idempotent(self):
        config=policy.configuration(deployment());data=snapshot();before=deepcopy(data)
        plan=MONITOR.monitoring_plan(config,data)
        self.assertEqual(data,before)
        self.assertEqual(plan['health_items'],{'agent.ping':'201','system.uptime':'202','icmpping':'203'})
        self.assertEqual({operation['method'] for operation in plan['operations']},
            {'host.update','item.update','trigger.update','discoveryrule.update'})
        self.assertTrue(all(set(operation['params']) in ({'hostid','status'},{'itemid','status'},{'triggerid','status'}) for operation in plan['operations']))
        for operation in plan['operations']:
            kind=operation['method'].split('.')[0];params=operation['params']
            if kind=='host': data['host'].update(params)
            else:
                field,identifier={'item':('items','itemid'),'trigger':('triggers','triggerid'),'discoveryrule':('discovery_rules','itemid')}[kind]
                next(row for row in data[field] if row[identifier]==params[identifier]).update(params)
        self.assertEqual(MONITOR.monitoring_plan(config,data)['operations'],[])
        self.assertEqual(len(data['items']),len(before['items']))

    def test_unknown_template_foreign_interface_and_unclassified_or_crosshost_checks_fail_closed(self):
        config=policy.configuration(deployment())
        for change in ('template','interface','item','crosshost','health-missing'):
            value=snapshot()
            if change=='template': value['host']['parentTemplates'][0]['name']='Unreviewed template'
            elif change=='interface': value['host']['interfaces'][0]['ip']='192.0.2.125'
            elif change=='item': value['items'][0]['templateid']='999'
            elif change=='crosshost': value['triggers'][0]['hosts'].append({'hostid':'99'})
            else: value['items'][0]['key_']='other.ping'
            with self.subTest(change=change),self.assertRaises(AnsibleFilterError): MONITOR.monitoring_plan(config,value)

    def test_discovered_checks_require_their_actual_reviewed_parent_rule(self):
        config=policy.configuration(deployment());value=snapshot()
        value['items'].append({'itemid':'250','hostid':'2','templateid':'0','key_':'net.if.in[eth0]',
            'status':'0','value_type':'3','discoveryRule':{'itemid':'601'}})
        self.assertEqual(MONITOR.monitoring_plan(config,value)['item_counts']['linux'],3)
        value['items'][-1]['discoveryRule']['itemid']='999'
        with self.assertRaises(AnsibleFilterError): MONITOR.monitoring_plan(config,value)

    def test_old_or_failed_samples_never_establish_live_monitoring(self):
        items={'agent.ping':'201','system.uptime':'202','icmpping':'203'}
        rows=[{'itemid':identifier,'clock':'101','value':'100' if identifier=='202' else '1'} for identifier in items.values()]
        self.assertTrue(MONITOR.samples_ready(rows,items,100))
        self.assertFalse(MONITOR.samples_ready(rows,items,102))
        self.assertFalse(MONITOR.samples_ready(rows[:2],items,100))
        rows[0]['value']='0'
        self.assertFalse(MONITOR.samples_ready(rows,items,100))

    def test_domain_proof_rejects_different_uuid_disk_mac_or_network(self):
        config=policy.configuration(deployment())
        guest=config['testserver'];guest.update(disk='/opt/vms/testserver1-v07.disk.qcow2',mac='52:54:00:12:34:56',network='internal')
        xml=f'<domain><name>{guest["vm_name"]}</name><uuid>{guest["uuid"]}</uuid><devices><disk device="disk"><source file="{guest["disk"]}"/></disk><interface type="network"><mac address="{guest["mac"]}"/><source network="internal"/></interface></devices></domain>'
        self.assertTrue(MONITOR.domain_matches(config,xml))
        for old,new in [(guest['uuid'],'9'*36),(guest['disk'],'/tmp/foreign'),(guest['mac'],'52:54:00:12:34:57'),('internal','foreign')]:
            with self.subTest(change=old),self.assertRaises(AnsibleFilterError): MONITOR.domain_matches(config,xml.replace(old,new))

    def test_normal_monitoring_tasks_enable_only_selected_linux_host_and_website_forwarding(self):
        api=MonitoringApi()
        runner=versioned.QuarantineExecutionTests()
        result,started,api=runner.run_tasks(api=api,finalize=True,delivery=True,monitor=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertTrue(started)
        selected=next(row for row in api.tables['host'] if row.get('host')=='testserver1-v07')
        self.assertEqual(int(selected['status']),0)
        self.assertEqual(next(row for row in api.tables['item'] if row['itemid']=='204')['status'],1)
        self.assertEqual(next(row for row in api.tables['trigger'] if row['triggerid']=='402')['status'],1)
        self.assertEqual(next(row for row in api.tables['discoveryrule'] if row['itemid']=='602')['status'],1)
        self.assertEqual([row['name'] for row in api.tables['action'] if str(row['status'])=='0'],['AIOps v07 website events'])
        self.assertEqual(len([method for method,_ in api.calls if method=='history.get']),1)
        again,started,api=runner.run_tasks(api=api,finalize=True,delivery=True,monitor=True)
        self.assertEqual(again.returncode,0,again.stdout+again.stderr)
        self.assertEqual(len([row for row in api.tables['host'] if row.get('host')=='testserver1-v07']),1)


if __name__=='__main__': unittest.main()
