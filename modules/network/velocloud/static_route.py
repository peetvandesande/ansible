from ansible.module_utils.basic import AnsibleModule
import urllib3
 
import veclient
from veclient import *

def get_edge(client, module):
    params = {"with": []}
    edges = client.call_api('/enterprise/getEnterpriseEdges', params)

    for edge in edges:
        if edge['name'] == module.params['edge']:
            return edge
            break
    module.fail_json(msg="Can't find edge")

def get_device_module(client, module, edge_id):
    params = {"edgeId": edge_id}
    modules = client.call_api('/edge/getEdgeConfigurationStack', params)

    for module in modules[0]['modules']:
        if module['name'] == 'deviceSettings':
            return module
            break
    module.fail_json(msg="Can't find device settings module")

def add_static_route(client, module, dev):
    segment = 0 # Assume global segment
    route = {
            "destination"        : module.params['destination'],
            "netmask"            : module.params['netmask'],
            "sourceIp"           : None,
            "gateway"            : module.params['gateway'],
            "cost"               : module.params['cost'],
            "preferred"          : module.params['preferred'],
            "description"        : module.params['description'],
            "cidrPrefix"         : module.params['prefix'],
            "wanInterface"       : module.params['interface'],
            "subinterfaceId"     : -1,
            "icmpProbeLogicalId" : None,
            "vlanId"             : None,
            "advertise"          : module.params['advertise']
    }

    # Check if route is already here
    existing_routes = dev['data']['segments'][segment]['routes']['static']
    index = 0
    for existing_route in existing_routes:
        if existing_route['destination'] == module.params['destination']:
            if module.params['state'] == 'present':
                # Check if route needs to be changed
                if existing_route != route:
                    dev['data']['segments'][segment]['routes']['static'][index] = route
                    params = {'id': dev['id'], '_update': dev['data']}
                    update = client.call_api('/configuration/updateConfigurationModule', params)

                    module.exit_json(changed=True, argument_spec=module.params, meta=existing_route)
                else:
                    module.exit_json(changed=False, argument_spec=module.params, meta=existing_route)
                break
        index = index + 1

    if module.params['state'] == 'present':
        dev['data']['segments'][segment]['routes']['static'].append(route)
    else:
        dev['data']['segments'][segment]['routes']['static'].remove(route)

    params = {'id': dev['id'], '_update': dev['data']}
    update = client.call_api('/configuration/updateConfigurationModule', params)

    return update

def main():
    urllib3.disable_warnings()
    module = AnsibleModule(
        argument_spec    = dict(
            orchestrator = dict(required  = True),
            token        = dict(required  = True),
            edge         = dict(required  = True),
            state        = dict(default   = 'present', choices = ['present', 'absent']),
            destination  = dict(required  = True),
            netmask      = dict(required  = True),
            prefix       = dict(required  = True),
            gateway      = dict(required  = True),
            interface    = dict(required  = True),
            cost         = dict(default   = 0, type            = 'int'),
            advertise    = dict(default   = True, type         = 'bool'),
            preferred    = dict(default   = True, type         = 'bool'),
            description  = dict(required  = False)
        )
    )

    try:
        client = VcoRequestManager(hostname=module.params['orchestrator'], verify_ssl=False, token=module.params['token'])
    except ApiException as e:
        module.fail_json(msg=e)

    edge = get_edge(client, module)
    dev = get_device_module(client, module, edge['id'])
    route = add_static_route(client, module, dev)

    module.exit_json(changed=True, argument_spec=module.params, meta=route)
 
if __name__ == '__main__':
    main()

