"""Bind a monitoring clone to the existing AAP allocation and hypervisor."""
import copy
import importlib.util
import ipaddress
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from ansible.errors import AnsibleFilterError
from ansible.parsing.yaml.objects import AnsibleVaultEncryptedUnicode

spec = importlib.util.spec_from_file_location('zabbix_website_configuration', Path(__file__).with_name('demo_website.py'))
website = importlib.util.module_from_spec(spec)
spec.loader.exec_module(website)


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def configuration(value):
    result = website.website_configuration(value)
    source = value.get('source_image', {})
    require(source.get('path') == '/opt/vms/zabbix-disk.qcow2'
            and re.fullmatch(r'[0-9a-f]{64}', source.get('sha256', '')),
            'Supply the verified saved monitoring image and its SHA-256.')
    require(re.fullmatch(r'[A-Za-z0-9_-]+', value.get('vm_network', '')),
            'Choose the isolated libvirt network explicitly.')
    user = value.get('guest_user', '')
    require(re.fullmatch(r'[a-z_][a-z0-9_-]*', user) and user != 'root',
            'Supply the cloned guest non-root management account.')
    key = value.get('guest_authorized_public_key', '')
    require(isinstance(key, str) and len(key.split()) == 2,
            'Supply the public counterpart of the attached Machine key.')
    website.website_configuration(dict(value, hypervisor=dict(value['hypervisor'], host_keys=[key])))
    version = f"v{result['instance_number']:02d}"
    result.update(hostname=f"zabbix.{version}.{result['zone']}", record_name=f'zabbix.{version}',
                  website_hostname=f"redhat.{version}.{result['zone']}", version=version,
                  vm_name=f'zabbix-{version}', disk=f'/opt/vms/zabbix-{version}.disk.qcow2',
                  vhost_file=f'/etc/nginx/conf.d/demo-zabbix-{version}.conf',
                  auth_file=f'/etc/nginx/demo-zabbix-{version}.htpasswd', source_image=copy.deepcopy(source),
                  vm_network=value['vm_network'], guest_user=user, guest_authorized_public_key=key,
                  memory_mb=4096, vcpus=2)
    return result


def metadata(config, host_keys):
    require(isinstance(host_keys, list) and len(host_keys) == 3, 'Retain the newly generated public guest host keys.')
    host_keys = [' '.join(str(key).split()[:2]) for key in host_keys]
    website.website_configuration(dict(config, instance_name=config['instance_name'],
                                      aap_fqdn=config['aap_hostname'],
                                      hypervisor=dict(config['hypervisor'], host_keys=host_keys)))
    return {'schema_version': 1, 'purpose': 'aiops-zabbix', 'instance_name': config['instance_name'],
            'instance_number': config['instance_number'], 'hostname': config['hostname'],
            'hypervisor_machine_id': config['hypervisor']['machine_id'],
            'source_sha256': config['source_image']['sha256'], 'guest_host_keys': host_keys}


def domain_record(xml, config):
    try:
        root = ET.fromstring(xml)
        record = json.loads(root.findtext('description') or '{}')
        expected = metadata(config, record.get('guest_host_keys'))
        require(record == expected, 'The existing domain does not belong to this selected deployment.')
        disks = root.findall("./devices/disk[@device='disk']/source")
        interfaces = root.findall('./devices/interface')
        require(root.findtext('name') == config['vm_name'] and len(disks) == 1
                and disks[0].get('file') == config['disk'] and set(disks[0].attrib) <= {'file', 'index'}
                and ('index' not in disks[0].attrib or re.fullmatch(r'[1-9][0-9]*', disks[0].get('index', ''))),
                'The monitoring domain does not own exactly its expected clone disk.')
        require(len(interfaces) == 1 and interfaces[0].get('type') == 'network'
                and interfaces[0].find('source').get('network') == config['vm_network'],
                'The monitoring domain must use only its declared isolated network.')
        mac = interfaces[0].find('mac').get('address')
        require(re.fullmatch(r'(?:[0-9a-f]{2}:){5}[0-9a-f]{2}', mac), 'Require its actual normalized guest MAC.')
        identity = root.findtext('uuid')
        require(re.fullmatch(r'[0-9a-f-]{36}', identity or ''), 'Require the actual domain UUID.')
        return dict(record, uuid=identity, mac=mac, vm_name=config['vm_name'], disk=config['disk'])
    except (ET.ParseError, ValueError, TypeError, AttributeError):
        raise AnsibleFilterError('Invalid or foreign monitoring domain; preserve it for review.') from None


def guest_address(output, mac):
    addresses = re.findall(r'\b' + re.escape(mac) + r'\s+ipv4\s+([0-9.]+)/[0-9]+', output)
    require(len(set(addresses)) == 1, 'Read one DHCP address belonging to this domain MAC.')
    address = ipaddress.IPv4Address(addresses[0])
    require(address.is_private and not address.is_loopback, 'Require the isolated guest private IPv4 address.')
    return str(address)


def network_details(xml, expected):
    try:
        root = ET.fromstring(xml)
        require(root.findtext('name') == expected, 'Inspect exactly the selected guest network.')
        address = ipaddress.IPv4Address(root.find('ip').get('address'))
        bridge = root.find('bridge').get('name')
        require(address.is_private and not address.is_loopback and re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', bridge),
                'Require a local isolated bridge and gateway.')
        return {'gateway': str(address), 'bridge': bridge}
    except (ET.ParseError, ValueError, TypeError, AttributeError):
        raise AnsibleFilterError('Invalid selected guest network.') from None


def quarantine(objects, kind, origin):
    require(isinstance(objects, list), 'Read the cloned monitoring integrations before changing them.')
    key = {'action':'actionid', 'mediatype':'mediatypeid', 'drule':'druleid',
           'host':'hostid', 'httptest':'httptestid', 'script':'scriptid'}[kind]
    updates = []
    for item in objects:
        require(str(item.get(key, '')).isdigit(), 'Require a valid cloned integration identifier.')
        if kind == 'script':
            desired = ({key:item[key], 'url':origin + '/'} if str(item.get('type')) == '6' else
                       {key:item[key], 'type':5, 'scope':1,
                        'command':'throw "Inherited clone integration disabled";', 'timeout':'1s', 'parameters':[]})
        else:
            desired = {key:item[key], 'status':1}
        if any(str(item.get(k)) != str(v) for k,v in desired.items()):
            updates.append(desired)
    return updates


def event_stream(config, value):
    from urllib.parse import urlsplit
    require(isinstance(value, dict), 'Supply the selected AAP event-stream endpoint and Basic authentication.')
    require(set(value) == {'url', 'username', 'password'} and
            all(isinstance(value[k], (str, AnsibleVaultEncryptedUnicode)) for k in value),
            'Supply only the selected event-stream URL and Basic credentials.')
    value = {key: str(item) for key, item in value.items()}
    parsed = urlsplit(value['url'])
    require(parsed.scheme == 'https' and parsed.hostname == config['aap_hostname']
            and parsed.port in (None,443) and not parsed.username and not parsed.password
            and not parsed.query and not parsed.fragment
            and re.fullmatch(r'/eda-event-streams/api/eda/v1/external_event_stream/[0-9a-f-]{36}/post/', parsed.path),
            'Send monitoring events only to the selected AAP instance event stream.')
    require(all(isinstance(value.get(k),str) and value[k] for k in ('username','password')),
            'Require explicit target event-stream Basic credentials.')
    return copy.deepcopy(value)



def recipient_medias(existing, media_id, endpoint):
    require(isinstance(existing, list), 'Read the existing cloned notification recipient media.')
    result = []
    for entry in existing:
        if str(entry['mediatypeid']) != str(media_id):
            require(not int(entry.get('provisioned', 0)), 'Review directory-provisioned notification media separately.')
            result.append({key: entry[key] for key in ('mediatypeid', 'sendto', 'active', 'severity', 'period')})
    result.append({'mediatypeid':str(media_id), 'sendto':endpoint, 'active':0,
                   'severity':63, 'period':'1-7,00:00-24:00'})
    return result



def provenance(config, record, address=None, network=None, machine_id=None):
    result = {'schema_version':1, 'instance_name':config['instance_name'],
              'instance_number':config['instance_number'], 'vm_name':config['vm_name'],
              'uuid':record['uuid'], 'disk':config['disk'], 'mac':record['mac'],
              'guest_host_keys':record['guest_host_keys'], 'host_keys':record['guest_host_keys'],
              'network':config['vm_network'], 'user':config['guest_user'], 'port':22, 'verified':False,
              'source_sha256':config['source_image']['sha256'],
              'hypervisor_machine_id':config['hypervisor']['machine_id'], 'public_hostname':config['hostname'],
              'nginx_file':config['vhost_file'], 'auth_file':config['auth_file'], 'certificate':config['hostname']}
    if address:
        require(guest_address(record['mac'] + ' ipv4 ' + address + '/32', record['mac']) == address,
                'Retain only the verified private guest address.')
        result.update(ip=address, address=address, api_url='http://' + address + '/api_jsonrpc.php')
    if network is not None:
        require(isinstance(network, dict) and re.fullmatch(r'[A-Za-z0-9_.:-]{1,15}', network.get('bridge', '')),
                'Retain the actual verified libvirt bridge.')
        result['bridge'] = network['bridge']
    if machine_id is not None:
        require(address is not None and network is not None and isinstance(machine_id, str)
                and re.fullmatch(r'[0-9a-f]{32}', machine_id) and machine_id != config['hypervisor']['machine_id'],
                'Require the pinned SSH guest machine identity before marking ownership verified.')
        result.update(machine_id=machine_id, verified=True)
    return result


class FilterModule:
    def filters(self):
        return {'demo_zabbix_configuration':configuration, 'demo_zabbix_metadata':metadata,
                'demo_zabbix_domain_record':domain_record, 'demo_zabbix_guest_address':guest_address,
                'demo_zabbix_network_details':network_details, 'demo_zabbix_quarantine':quarantine,
                'demo_zabbix_event_stream':event_stream, 'demo_zabbix_recipient_medias':recipient_medias,
                'demo_zabbix_provenance':provenance}
