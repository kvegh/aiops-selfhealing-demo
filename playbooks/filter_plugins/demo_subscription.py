"""Bind RHSM registration and retirement to one authenticated TRA owner."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import re

from ansible.errors import AnsibleFilterError

spec = spec_from_file_location('subscription_mcp_owner', Path(__file__).with_name('demo_mcp.py'))
mcp = module_from_spec(spec)
spec.loader.exec_module(mcp)


def require(condition, message):
    if not condition:
        raise AnsibleFilterError(message)


def configuration(deployment):
    config = mcp.website.website_configuration(deployment)
    config['tra'] = mcp.guest(config, deployment.get('tra'), 'tra')
    return config


def identity(result, config):
    require(isinstance(result, dict) and isinstance(result.get('rc'), int) and not isinstance(result.get('rc'), bool) and result['rc'] in (0, 1)
            and isinstance(result.get('stdout', ''), str) and isinstance(result.get('stderr', ''), str),
            'Read exact native subscription identity before registration or retirement.')
    text = result.get('stdout', '') + '\n' + result.get('stderr', '')
    if result['rc'] == 1:
        require('This system is not yet registered.' in text and not re.search(r'^system identity:', text, re.M),
                'A failed identity request is not proof of native registration absence.')
        return {'registered': False, 'consumer_uuid': None, 'consumer_name': None}
    consumers = re.findall(r'^system identity:\s*([0-9a-f-]+)\s*$', text, re.M)
    names = re.findall(r'^name:\s*(\S+)\s*$', text, re.M)
    require(len(consumers) == 1 and bool(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', consumers[0]))
            and consumers[0] != '00000000-0000-0000-0000-000000000000'
            and len(names) == 1 and names[0] in {config['tra']['vm_name'], config.get('registration_name', config['tra']['vm_name'])},
            'A current RHSM consumer must name the exact selected TRA; copied consumers are not ours to change.')
    return {'registered': True, 'consumer_uuid': consumers[0], 'consumer_name': names[0]}


def owner(config, consumer_uuid, retired=False, consumer_name=None):
    require(isinstance(consumer_uuid, str) and bool(re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', consumer_uuid))
            and consumer_uuid != '00000000-0000-0000-0000-000000000000' and type(retired) is bool,
            'Record only a real native consumer identity and explicit state.')
    consumer_name = consumer_name or config['tra']['vm_name']
    require(consumer_name in {config['tra']['vm_name'], config.get('registration_name', config['tra']['vm_name'])},
            'Bind only the selected TRA native short or verified fully qualified hostname.')
    return {'schema_version': 1, 'instance_name': config['instance_name'], 'guest_name': config['tra']['vm_name'],
            'guest_uuid': config['tra']['uuid'], 'machine_id': config['tra']['machine_id'],
            'consumer_uuid': consumer_uuid, 'consumer_name': consumer_name, 'retired': retired}


def validate_owner(value, config):
    require(isinstance(value, dict) and set(value) == {
        'schema_version', 'instance_name', 'guest_name', 'guest_uuid', 'machine_id', 'consumer_uuid', 'consumer_name', 'retired'}
        and isinstance(value['schema_version'], int) and not isinstance(value['schema_version'], bool) and value['schema_version'] == 1
        and type(value['retired']) is bool and value == owner(config, value['consumer_uuid'], value['retired'], value['consumer_name']),
        'Existing subscription ownership belongs to another guest or is incomplete; preserve it for review.')
    return value


def before_registration(observed, saved, config):
    if saved is not None:
        validate_owner(saved, config)
    if observed['registered']:
        require(saved is not None and saved['retired'] is False and saved['consumer_uuid'] == observed['consumer_uuid']
                and saved['consumer_name'] == observed['consumer_name'],
                'Do not claim an existing registered consumer without this exact TRA ownership receipt.')
    else:
        require(saved is None, 'A previous consumer receipt survives without registration; finish its verified retirement first.')
    return True


def before_retirement(observed, saved, config):
    if saved is not None:
        validate_owner(saved, config)
    if observed['registered']:
        require(saved is not None and saved['retired'] is False and saved['consumer_uuid'] == observed['consumer_uuid']
                and saved['consumer_name'] == observed['consumer_name'],
                'Retire only this exact TRA\'s recorded current consumer; never unregister a copied or foreign consumer.')
    elif saved is not None:
        require(saved['retired'] is True,
                'Registration disappeared before successful unregister was recorded. Retain ownership and recover the original native job evidence.')
    return True


class FilterModule:
    def filters(self):
        return {'demo_subscription_configuration': configuration, 'demo_subscription_identity': identity,
                'demo_subscription_owner': owner, 'demo_subscription_validate_owner': validate_owner,
                'demo_subscription_before_registration': before_registration,
                'demo_subscription_before_retirement': before_retirement}
