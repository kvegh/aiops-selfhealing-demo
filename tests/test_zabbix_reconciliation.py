"""Preserve copied IDs while replacing only selected deployment references."""
from copy import deepcopy
import unittest
from ansible.errors import AnsibleFilterError
from test_versioned_zabbix import policy, deployment


def fixture():
    config=policy.configuration(deployment())
    hosts=[
      {'hostid':'1','host':'demo-website-v07','name':'demo-website-v07','status':'0'},
      {'hostid':'2','host':'demo-website-redhat','name':'redhat.example.invalid','status':'1'},
      {'hostid':'3','host':'testserver1','name':'testserver1','status':'1','interfaces':[{'interfaceid':'30','type':'1','ip':'192.0.2.11','dns':'testserver1','useip':'1'}]},
      {'hostid':'4','host':'Zabbix server','name':'Zabbix server','status':'1','interfaces':[{'interfaceid':'40','type':'1','ip':'127.0.0.1','dns':'','useip':'1'}]},
      {'hostid':'5','host':'demo-aap-dashboard','name':'AAP demo monitoring','status':'1','macros':[
        {'hostmacroid':'51','macro':'{$BBB.AAP.URL}','value':'https://aap.example.invalid','type':'0'},
        {'hostmacroid':'52','macro':'{$BBB.AAP.TOKEN}','value':'******','type':'1'},
        {'hostmacroid':'53','macro':'{$BBB.AAP.STREAM_ID}','value':'42','type':'0'},
        {'hostmacroid':'54','macro':'{$BBB.AAP.JOB_TEMPLATES}','value':'62,63','type':'0'}]},
      {'hostid':'9','host':'unrelated','name':'Unrelated','status':'1'}]
    items=[
      {'itemid':'11','hostid':'1','templateid':'0','key_':'demo.website.http_status','name':'Demo website content HTTP status','url':'https://redhat.v07.example.invalid/content.html','status':'0'},
      {'itemid':'21','hostid':'2','templateid':'0','key_':'demo.website.http_status','name':'Demo website content HTTP status','url':'https://redhat.example.invalid/content.html','status':'0'},
      {'itemid':'31','hostid':'3','templateid':'123','name':'Get status','url':'http://{$APACHE.STATUS.HOST}/server-status'},
      {'itemid':'55','hostid':'5','templateid':'0','name':'AAP recent jobs','url':'{$BBB.AAP.URL}/api/controller/v2/jobs/'},
      {'itemid':'99','hostid':'9','templateid':'0','name':'External','url':'https://external.example.invalid/'}]
    triggers=[{'triggerid':str(100+i),'templateid':'0','hosts':[{'hostid':str(i)}],
               'description':'Demo website content unavailable','status':'0'} for i in (1,2)]
    return config,{'hosts':hosts,'items':items,'triggers':triggers}


def apply(snapshot,operations):
    result=deepcopy(snapshot)
    for operation in operations:
        kind,verb=operation['method'].split('.')
        params=deepcopy(operation['params'])
        if kind=='host':rows=result['hosts'];identity='hostid'
        elif kind=='hostinterface':rows=[row for host in result['hosts'] for row in host.get('interfaces',[])];identity='interfaceid'
        elif kind=='usermacro':
            if verb=='create':
                host_id=params.pop('hostid')
                host=next(row for row in result['hosts'] if row['hostid']==host_id)
                host.setdefault('macros',[]).append(dict(params,hostmacroid='created-macro'));continue
            rows=[row for host in result['hosts'] for row in host.get('macros',[])];identity='hostmacroid'
        else:rows=result['items' if kind=='item' else 'triggers'];identity=kind+'id'
        next(row for row in rows if row[identity]==params[identity]).update(params)
    return result


class ReconciliationTests(unittest.TestCase):
    def test_in_place_mapping_is_idempotent_and_retains_history_and_unrelated_objects(self):
        config,snapshot=fixture();original=deepcopy(snapshot)
        operations=policy.reconcile(config,snapshot)
        self.assertEqual(snapshot,original)
        self.assertTrue(all(operation['method'].endswith(('.update','.create')) for operation in operations))
        updated=apply(snapshot,operations)
        self.assertEqual(policy.reconcile(config,updated),[])
        self.assertEqual([x['hostid'] for x in updated['hosts']],[x['hostid'] for x in snapshot['hosts']])
        self.assertEqual(updated['hosts'][-1],snapshot['hosts'][-1]);self.assertEqual(updated['items'][-1],snapshot['items'][-1])
        self.assertEqual(updated['hosts'][0]['host'],'demo-website-v07')
        self.assertEqual(updated['hosts'][0]['name'],'redhat.v07.example.invalid')
        self.assertEqual(updated['hosts'][1]['host'],'demo-website-v07-imported')
        self.assertEqual(updated['hosts'][1]['name'],'Imported website v07 (disabled)')
        self.assertEqual(str(updated['hosts'][1]['status']),'1')
        self.assertEqual(updated['hosts'][2]['interfaces'][0]['ip'],config['testserver']['address'])
        self.assertEqual(updated['hosts'][2]['host'],'testserver1-v07')
        self.assertEqual(updated['hosts'][3]['host'],'zabbix-v07')
        self.assertEqual(updated['items'][1]['url'],'https://redhat.v07.example.invalid/content.html')
        self.assertEqual(str(updated['items'][1]['status']),'1')
        self.assertIn('Demo website content unavailable',updated['triggers'][0]['description'])
        self.assertIn('redhat.v07.example.invalid',updated['triggers'][0]['description'])
        self.assertEqual(str(updated['triggers'][1]['status']),'1')
        macros={row['macro']:row for row in updated['hosts'][4]['macros']}
        self.assertEqual(macros['{$BBB.AAP.URL}']['value'],'https://aap27.v07.example.invalid')
        for key in ('TOKEN','STREAM_ID','JOB_TEMPLATES'):
            self.assertEqual(macros['{$BBB.AAP.'+key+'}']['value'],'')
        self.assertEqual(macros['{$BBB.AAP.TOKEN}']['hostmacroid'],'52')
        apache=next(row for row in updated['hosts'][2]['macros'] if row['macro']=='{$APACHE.STATUS.HOST}')
        self.assertEqual(apache['value'],config['testserver']['address'])
        self.assertEqual(updated['items'][2],snapshot['items'][2])  # Template items are not edited directly.

    def test_collisions_and_foreign_testserver_identity_fail_before_any_plan_is_returned(self):
        config,snapshot=fixture()
        snapshot['hosts'].append({'hostid':'88','host':'demo-website-v07-imported','name':'conflict'})
        with self.assertRaises(AnsibleFilterError):policy.reconcile(config,snapshot)
        for key,value in (('vm_name','testserver1-v08'),('hypervisor_machine_id','9'*32),('verified',False)):
            data=deployment();data['testserver'][key]=value
            with self.subTest(key=key),self.assertRaises(AnsibleFilterError):policy.configuration(data)

    def test_admin_media_removes_only_stale_eda_destinations_and_keeps_association_ids(self):
        path='/eda-event-streams/api/eda/v1/external_event_stream/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/post/'
        rows=[{'mediaid':'701','mediatypeid':'72','sendto':['https://source.example.invalid'+path],'active':'0','severity':'63','period':'1-7,00:00-24:00'},
              {'mediaid':'702','mediatypeid':'104','sendto':['https://old.example.invalid'+path],'active':'0','severity':'63','period':'1-7,00:00-24:00'},
              {'mediaid':'703','mediatypeid':'5','sendto':['operator@example.invalid'],'active':'0','severity':'63','period':'1-7,00:00-24:00'}]
        result=policy.recipient_medias(rows,'104','https://target.example.invalid'+path,['72'])
        self.assertEqual([row['mediaid'] for row in result],['703','702'])
        self.assertEqual(result[0]['sendto'],rows[2]['sendto']);self.assertEqual(result[0]['active'],1)
        self.assertEqual(result[1]['sendto'],'https://target.example.invalid'+path)
        self.assertEqual(policy.recipient_medias(result,'104','https://target.example.invalid'+path,['72']),result)

    def test_imported_media_keeps_id_and_is_disabled_with_current_basic_settings(self):
        config,_=fixture();definition={'type':4,'status':0,'script':'controlled Basic script','parameters':[{'name':'password','value':'synthetic-password'}]}
        result=policy.imported_media([{'mediatypeid':'72','name':'Event-Driven Ansible','type':'4'}],'104',config,definition)
        self.assertEqual(result[0]['mediatypeid'],'72');self.assertEqual(result[0]['status'],1)
        self.assertEqual(result[0]['parameters'],definition['parameters'])
        self.assertEqual(result[0]['name'],'Imported EDA event stream v07 (disabled)')

    def test_auth_and_action_readbacks_refuse_wrong_credentials_or_unselected_forwarding(self):
        endpoint='https://aap27.v07.example.invalid/eda-event-streams/api/eda/v1/external_event_stream/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/post/'
        definition={'script':'controlled Basic script','parameters':[{'name':'endpoint','value':endpoint},{'name':'password','value':'synthetic-private-password'}]}
        media=[dict(definition,mediatypeid='104',status='0',type='4')]
        operation={'operationtype':'0','opmessage':{'mediatypeid':'104'},'opmessage_usr':[{'userid':'1'}]}
        actions=[{'actionid':'10','status':'1','filter':{'conditions':[{'conditiontype':'2','value':'101'}]},'operations':[operation],'recovery_operations':[operation]}, {'actionid':'7','status':'1'}]
        admin=[{'userid':'1','medias':[{'mediaid':'702','mediatypeid':'104','sendto':[endpoint],'active':'0','severity':'63','period':'1-7,00:00-24:00'}]}]
        self.assertTrue(policy.delivery_ready(media,actions,admin,definition,'104','10','101',endpoint,['72']))
        wrong=deepcopy(media);wrong[0]['parameters'][1]['value']='wrong'
        with self.assertRaises(AnsibleFilterError) as error:policy.delivery_ready(wrong,actions,admin,definition,'104','10','101',endpoint,['72'])
        self.assertNotIn('synthetic-private-password',str(error.exception))
        actions[1]['status']='0'
        with self.assertRaises(AnsibleFilterError):policy.delivery_ready(media,actions,admin,definition,'104','10','101',endpoint,['72'])


if __name__=='__main__':unittest.main()
