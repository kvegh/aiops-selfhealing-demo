"""Exercise the normal retirement playbook against a local native CLI fixture.

All native paths and external subscription CLI calls are redirected into a
private temporary directory. Production guards, ordering, real Ansible facts,
receipt writes, conditionals and returned stats still execute.
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import yaml
from test_subscription_owner import owner, CONSUMER
from test_mcp_deployment import deployment
ROOT=Path(__file__).resolve().parents[1]


class SubscriptionRetirementTests(unittest.TestCase):
    def fixture(self, folder, foreign=False):
        selected=owner.configuration(deployment())
        receipt=owner.owner(selected,CONSUMER)
        if foreign:receipt['consumer_uuid']='99999999-2222-4333-8444-555555555555'
        state=folder/'state';state.mkdir(mode=0o700)
        (state/'subscription-owner.json').write_text(json.dumps(receipt));(state/'subscription-owner.json').chmod(0o600)
        certificate=folder/'consumer.pem';certificate.write_text('synthetic-consumer')
        uuid=folder/'uuid';uuid.write_text(selected['tra']['uuid'])
        machine=folder/'machine-id';machine.write_text(selected['tra']['machine_id'])
        counter=folder/'unregister-count';command=folder/'subscription-manager'
        command.write_text('#!'+sys.executable+'\nimport pathlib,sys\n'
            +'certificate=pathlib.Path('+repr(str(certificate))+')\n'
            +'counter=pathlib.Path('+repr(str(counter))+')\n'
            +'if sys.argv[1]=="unregister":\n'
            +' assert certificate.exists()\n certificate.unlink()\n counter.write_text(counter.read_text()+"unregister\\n" if counter.exists() else "unregister\\n")\n print("System has been unregistered.")\n'
            +'elif certificate.exists():\n print("system identity: '+CONSUMER+'\\nname: '+selected['tra']['vm_name']+'")\n'
            +'else:\n print("This system is not yet registered.")\n raise SystemExit(1)\n')
        command.chmod(0o700)
        mapping={'/run/aiops-subscription.lock':str(folder/'subscription.lock'),'/var/lib/aiops-selfhealing':str(state),'/etc/pki/consumer/cert.pem':str(certificate),
                 '/usr/sbin/subscription-manager':str(command),'/sys/class/dmi/id/product_uuid':str(uuid),'/etc/machine-id':str(machine)}
        def localize(value):
            if isinstance(value,list):return[localize(item)for item in value]
            if isinstance(value,dict):
                result={key:localize(item)for key,item in value.items()}
                for action in ('ansible.builtin.file','ansible.builtin.copy'):
                    if action in result:
                        result[action].pop('owner',None);result[action].pop('group',None)
                if 'ansible.builtin.command'in result:
                    argv=result['ansible.builtin.command']['argv']
                    if argv[0]=='subscription-manager':argv[0]=str(command)
                    if 'import socket; print(socket.getfqdn())'in argv:
                        result['ansible.builtin.command']['argv']=[sys.executable,'-c',"print('"+selected['tra']['vm_name']+"')"]
                return result
            if isinstance(value,str):
                for old,new in mapping.items():value=value.replace(old,new)
                return value.replace('.stat.uid == 0','.stat.uid == '+str(os.getuid()))
            return value
        tasks_dir=folder/'tasks';tasks_dir.mkdir()
        for name in ('demo_subscription_owner_read.yml','demo_subscription_owner_write.yml'):
            value=localize(yaml.safe_load((ROOT/'playbooks/tasks'/name).read_text()))
            (tasks_dir/name).write_text(yaml.safe_dump(value,sort_keys=False))
        play=localize(yaml.safe_load((ROOT/'playbooks/retire_tra_subscription.yml').read_text()))
        play[0].update(hosts='localhost',connection='local',become=False,vars={
            'demo_mcp_deployment':deployment(),'ansible_host':selected['tra']['address'],
            'demo_subscription_teardown_confirmation':selected['instance_name'],
            'awx_job_id':23,'awx_job_template_id':12,'awx_project_revision':'a'*40})
        source=folder/'check.yml';source.write_text(yaml.safe_dump(play,sort_keys=False))
        environment=dict(os.environ,ANSIBLE_LOCAL_TEMP=str(folder/'local'),ANSIBLE_REMOTE_TEMP=str(folder/'remote'),
                         ANSIBLE_FILTER_PLUGINS=str(ROOT/'playbooks/filter_plugins'),ANSIBLE_NOCOLOR='1')
        return source,environment,state,counter

    def run_fixture(self,source,environment):
        return subprocess.run([sys.executable,'-m','ansible.cli.playbook','-i','localhost,',str(source)],
                              env=environment,capture_output=True,text=True,timeout=60)

    def test_exact_owned_native_retirement_and_idempotent_second_run(self):
        with tempfile.TemporaryDirectory(prefix='subscription-native-retirement-')as temp:
            source,env,state,counter=self.fixture(Path(temp))
            for attempt in range(2):
                result=self.run_fixture(source,env)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                self.assertIs(json.loads((state/'subscription-owner.json').read_text())['retired'],True)
                self.assertEqual(counter.read_text().splitlines(),['unregister'])
                self.assertIn('Return only exact noncredential native absence evidence',result.stdout)

    def test_another_consumer_receipt_refuses_before_native_unregister(self):
        with tempfile.TemporaryDirectory(prefix='subscription-native-foreign-')as temp:
            source,env,state,counter=self.fixture(Path(temp),foreign=True)
            result=self.run_fixture(source,env)
            self.assertNotEqual(result.returncode,0,result.stdout+result.stderr)
            self.assertFalse(counter.exists())
            self.assertIs(json.loads((state/'subscription-owner.json').read_text())['retired'],False)
