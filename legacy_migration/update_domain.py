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

# Where things usually live
OPFLEX_CONF = '/etc/opflex-agent-ovs/conf.d/opflex-agent-ovs.conf'
OPFLEX_DEFAULT_CFG = {'opflex': 
    {'domain': 'comp/prov-OpenStack/ctrlr-[%(dom)s]-%(dom)s/sw-InsiemeLSOid'}
}


class OpflexConfig(object):
    """Update the VMM domain in the opflex configuration file

    """

    def __init__(self, config_file_name):
        self.opflex_filename = OPFLEX_CONF
        if config_file_name:
            self.opflex_filename = config_file_name
        self.opflex_default_cfg = OPFLEX_DEFAULT_CFG
        self.cfg_objs = {}

    def get_legacy_config(self):
        self.cfg_objs[filename] = config_info.ConfigInfo(self.opflex_filename)

    def _update_section(self, new_section, old_section, params):
        # Some of the parameters live in a section with a
        # different name.
        for cfg_file in self.cfg_objs.keys():
            cfg_obj = self.cfg_objs[cfg_file]
            cfg = cfg_obj.get_section_config(old_section)
            if cfg:
                break
        if not cfg:
            print "No section named %(section)s" % {'section': old_section}
            return
        for k in cfg.keys():
            if k in params[new_section].keys():
                params[new_section][k] = cfg[k]

    def _update_parameters(self, parameters, configurations):
        for section in parameters.keys():
            for configuration in configurations:
                cfg = configuration.get_section_config(section)
                for k in cfg.keys():
                    if k in parameters[section]:
                        parameters[section][k] = cfg[k]

    def _get_vmm_dom_config(self):
        vmdom_config = {}
        for config in self.cfg_objs.values():
            for section in config.sections_dict.keys():
                if section.startswith('domain'):
                    vmdom_config.setdefault(section, {})
                    cfg = config.get_section_config(section)
                    for k in cfg.keys():
                        vmdom_config[section][k] = cfg[k]
        return vmdom_config

    def _find_config_item(self, config_name):
        for config in self.cfg_objs.values():
            for section in config.sections_dict.keys():
                if config.sections_dict[section].get(config_name):
                    return config.sections_dict[section][config_name]
        return None
                
    def create_aim_config(self):
        new_section = 'apic'
        old_section = 'ml2_cisco_apic'

        params = self.aim_default_cfg
        self._update_parameters(params, self.cfg_objs.values())
        self._update_section(new_section, old_section, params)

        # THe system ID needs to be migrated to AIM
        apic_system_id = self._find_config_item('apic_system_id')
        params['aim']['aim_system_id'] = apic_system_id

        # Create aim.conf
        aim_cfg = config_info.ConfigInfo(self.aim_filename,
                                         config_dict = params)
        aim_cfg.write_configuration()

        params = self.aimctl_default_cfg
        self._update_parameters(params, self.cfg_objs.values())
        self._update_section(new_section, old_section, params)
 
        # We have to migrate the VMM domains. For now, we
        # just worry about the one in apic_domain_name
        apic_domain_name = self._find_config_item('apic_domain_name')
        if apic_domain_name:
            vmm_dom_name = 'apic_vmdom:' + apic_domain_name
            vmm_dom_name = vmm_dom_name.translate(None, '\n')
            # TODO: add vlan_ranges? Are these only in APIC?
            params[vmm_dom_name] = {}

        # TODO: how to get physdoms?

        # Create aimtcl.conf
        aimctl_cfg = config_info.ConfigInfo(self.aimctl_filename,
                                            config_dict = params)
        aimctl_cfg.write_configuration()
