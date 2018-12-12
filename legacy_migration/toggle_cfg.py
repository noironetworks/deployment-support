# Copyright (c) 2018 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import config_info

DEFAULT_NEUTRON_CONF = '/etc/neutron/neutron.conf'
DEFAULT_PLUGIN_CONF = '/etc/neutron/plugin.ini'
DRV = 'aim_extension,proxy_group,apic_allowed_vm_name,apic_segmentation_label'


class ToggleConfig(object):

    def __init__(self, config_file_names):
        self.cfg_objs = {}
        self.config_file_names = config_file_names
        self.config_changes = [{'item': 'core_plugin',
                                'old': 'ml2',
                                'new': 'ml2plus'},
                               {'item': 'service_plugins',
                                'old': 'cisco_apic_l3',
                                'new': 'apic_aim_l3,group_policy,ncp'},
                               {'item': 'policy_drivers',
                                'old': 'implicit_policy,apic',
                                'new': 'aim_mapping'},
                               {'item': 'mechanism_drivers ',
                                'old': 'cisco_apic_ml2',
                                'new': 'apic_aim'},
                               {'item': 'extension_drivers',
                                'section_name': 'ml2',
                                'old': None,
                                'new': 'apic_aim,port_security'},
                               {'item': 'extension_drivers',
                                'section_name': 'group_policy',
                                'old': None,
                                'new': DRV}
                              ]

    def _get_legacy_config(self):
        if not self.config_file_names:
            self.config_file_names = (DEFAULT_NEUTRON_CONF,
                                      DEFAULT_PLUGIN_CONF)
        for filename in self.config_file_names:
            self.cfg_objs[filename] = config_info.ConfigInfo(filename)

    def _set_config(self, config_type):
        self._get_legacy_config()
        for cfg_item in self.config_changes:
            for cfg_obj in self.cfg_objs.values():
                # Some cfg items need section scoping
                section_name = cfg_item.get('section_name')
                section_key, _ = cfg_obj.find_config_item(cfg_item['item'],
                    section_name=section_name)
                if section_key:
                    value = cfg_item[config_type]
                    cfg_obj.set_section_config(section_key,
                                               cfg_item['item'], value)
                    # Keep going, just in case it's in more than one file
                                  
    def old_config(self):
        self._set_config('old')
        for cfg_obj in self.cfg_objs.values():
            if 'neutron.conf' in cfg_obj.filename :
                cfg_obj.set_section_config('DEFAULT',
                                           'agent_down_time', '75')

    def new_config(self):
        self._set_config('new')
        for cfg_obj in self.cfg_objs.values():
            if 'neutron.conf' in cfg_obj.filename :
                cfg_obj.set_section_config('DEFAULT',
                                           'agent_down_time', '7200000')

    def write_config(self, neutron_out=None, plugin_out=None):
        for cfg_obj in self.cfg_objs.values():
            cfg_obj.write_configuration()


