#!/usr/bin/python

DOCUMENTATION = """
---

module: comware_stp
short_description: Manage stp global BPDU enable, working mode and tc-bpdu attack protection function.
description:
    - 
version_added: 1.0
category: Feature (RW)
author:hanyangyang
notes:

options:
    bpdu:
        description:
            - Turn on the global BPDU protection function.
        required: false
        default: null
        choices: ['true','false']
        aliases: []
    mode:
        description:
            - Configure the working mode of the spanning tree.
        required: false
        default: null
        choices: [MSTP', 'PVST', 'RSTP','STP']
        aliases: []
    tc:
        description:
            - Enable anti tc-bpdu attack protection function.
        required: false
        default: null
        choices: ['true', 'false']
        aliases: []
    state:
        description:
            - Desired state for the interface configuration
        required: false
        default: present
        choices: ['present', 'absent', 'default']
        aliases: []
    hostname:
        description:
            - IP Address or hostname of the Comware v7 device that has
              NETCONF enabled
        required: true
        default: null
        choices: []
        aliases: []
    username:
        description:
            - Username used to login to the switch
        required: true
        default: null
        choices: []
        aliases: []
    password:
        description:
            - Password used to login to the switch
        required: true
        default: null
        choices: []
        aliases: []
    port:
        description:
            - The Comware port used to connect to the switch
        required: false
        default: 830
        choices: []
        aliases: []
    look_for_keys:
        description:
            - Whether searching for discoverable private key files in ~/.ssh/
        required: false
        default: False
        choices: []
        aliases: []
"""
EXAMPLE = """

# Basic stp config
- comware_stp: bpdu=true mode=MSTP tc=true username={{ username }} password={{ password }} hostname={{ inventory_hostname }}
# delete Basic stp config
- comware_stp: bpdu=true mode=MSTP tc=true state=absent username={{ username }} password={{ password }} hostname={{ inventory_hostname }}
"""

import socket

try:
    HAS_PYCW7 = True
    from pycw7.comware import COM7
    from pycw7.features.stp import Stp
    from pycw7.features.errors import InterfaceError
    from pycw7.errors import *
except ImportError as ie:
    HAS_PYCW7 = False


def safe_fail(module, device=None, **kwargs):
    if device:
        device.close()
    module.fail_json(**kwargs)

def safe_exit(module, device=None, **kwargs):
    if device:
        device.close()
    module.exit_json(**kwargs)

def main():
    module = AnsibleModule(
        argument_spec=dict(
            bpdu=dict(required=False,choices=['true', 'false',]),
            mode=dict(required=False,choices=['MSTP', 'PVST', 'RSTP','STP']),
            tc=dict(required=False,choices=['true', 'false',]),
            state=dict(choices=['present', 'absent', 'default'],
                       default='present'),
            hostname=dict(required=True),
            username=dict(required=True),
            password=dict(required=False, default=None),
            port=dict(type='int', default=830),
            look_for_keys=dict(default=False, type='bool'),
        ),
        supports_check_mode=True
    )

    if not HAS_PYCW7:
        safe_fail(module, msg='There was a problem loading from the pycw7 '
                  + 'module.', error=str(ie))

    filtered_keys = ('state', 'hostname', 'username', 'password',
                     'port', 'CHECKMODE', 'name', 'look_for_keys')

    hostname = socket.gethostbyname(module.params['hostname'])
    username = module.params['username']
    password = module.params['password']
    port = module.params['port']
    device = COM7(host=hostname, username=username,
                    password=password, port=port)
    state = module.params['state']
    changed = False
    proposed = dict((k, v) for k, v in module.params.items()
                    if v is not None and k not in filtered_keys)

    try:
        look_for_keys = module.params['look_for_keys']
        device.open(look_for_keys=look_for_keys)
    except ConnectionError as e:
        safe_fail(module, device, msg=str(e),
                  descr='Error opening connection to device.')

    try:
        stp = Stp(device,)
    except PYCW7Error as e:
        safe_fail(module,device,descr='there is problem in setting stp config',
                  msg=str(e))

    try:
        existing = stp.get_config()
    except PYCW7Error as e:
        safe_fail(module, device, msg=str(e),
                  descr='Error getting existing config.')

    if state == 'present':
        delta = dict(set(proposed.items()).difference(
            existing.items()))
        if delta:
            stp.build(stage=True, **delta)

    elif state == 'default' or 'absent':
        defaults = stp.get_default_config()
        delta = dict(set(existing.items()).difference(
            defaults.items()))
        if delta:
            stp.default(stage=True)

    commands = None
    end_state = existing

    if device.staged:
        commands = device.staged_to_string()
        if module.check_mode:
            safe_exit(module, device, changed=True,
                      commands=commands)
        else:
            try:
                device.execute_staged()
                end_state = stp.get_config()
            except PYCW7Error as e:
                safe_fail(module, device, msg=str(e),
                          descr='Error on device execution.')
            changed = True

    results = {}
    results['proposed'] = proposed
    results['existing'] = existing
    results['state'] = state
    results['commands'] = commands
    results['changed'] = changed
    # results['end_state'] = end_state

    safe_exit(module, device, **results)

from ansible.module_utils.basic import *
main()
