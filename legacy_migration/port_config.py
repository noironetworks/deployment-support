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

# This module contains a bunch of helper classes
# that are used to facilitate and somewhat automate
# migration from the legacy plugins to the merged plugin

# Where things usually live
NEUTRON_CONF = '/etc/neutron/neutron.conf'
PLUGIN_CONF = '/etc/neutron/plugin.ini'
AIM_CFG_FILE_NAME = '/etc/aim/aim.conf'
AIMCTL_CFG_FILE_NAME = '/etc/aim/aimctl.conf'


# Default values for configuration. Note that
# we use this as a way to define all the possible
# keys/configuration for a given section -- if you
# want a sepcific configuration to be migrated, it
# must be represented here
AIM_DEFAULT_CFG = {'DEFAULT': 
                       {'debug': 'False\n',
                        'rpc_backend': 'rabbit\n',
                        'control_exchange': 'neutron\n',
                        'default_log_levels': 'neutron.context=ERROR\n'},
                   'oslo_messaging_rabbit':
                       {'rabbit_host': None,
                        'rabbit_hosts': None,
                        'rabbit_userid': None,
                        'rabbit_password': None,
                        'rabbit_ha_queues': 'False\n',
                        'rabbit_use_ssl': None},
                   'database':
                       {'connection': None},
                   'aim':
                       {'agent_down_time': '75\n',
                        'poll_config': 'False\n',
                        'aim_system_id': None},
                   'apic':
                       {'apic_hosts': None,
                        'apic_username': 'admin\n',
                        'apic_password': 'noir0123\n',
                        'apic_use_ssl': 'True\n',
                        'verify_ssl_certificate': 'False\n',
                        'scope_names': 'True\n'}
                  }

AIMCTL_DEFAULT_CFG = {'DEFAULT': 
                          {'apic_system_id': None},
                      'apic':
                          {'scope_infra': 'False\n',
                           'apic_provision_infra': 'False\n',
                           'apic_provision_hostlinks': 'False\n',
                           'apic_vmm_type': None,
                           'apic_vlan_ns_name': None,
                           'apic_node_profile': None,
                           'apic_entity_profile': None,
                           'apic_function_profile': None,
                           'apic_vpc_pairs': None}
                     }

class AimConfig(object):
    """Update aim.conf and aimctl.conf files.

    Migration from the legacy plugin to AIM requires
    extracting configuraiton paramters from the existing
    neutron configuration and generating new configuration
    files for AIM.
    """

    def __init__(self):
        self.aim_filename = AIM_CFG_FILE_NAME
        self.aimctl_filename = AIMCTL_CFG_FILE_NAME
        self.aim_default_cfg = AIM_DEFAULT_CFG
        self.aimctl_default_cfg = AIMCTL_DEFAULT_CFG
        self.neutron_config = None
        self.plugin_config = None

    def get_legacy_config(self):
        self.neutron_config = ConfigInfo(NEUTRON_CONF)
        self.plugin_config = ConfigInfo(PLUGIN_CONF)

    def _update_section(self, new_section, old_section, params):
        # Some of the parameters live in a section with a
        # different name.
        cfg = self.neutron_config.get_section_config(old_section)
        if not cfg:
            # may live in the plugin.ini
            cfg = self.plugin_config.get_section_config(old_section)
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

    def _write_configuration(self, params, filename):
        fd = open(filename, 'w+')
        for section in params.keys():
            fd.write('[' + section + ']\n')
            for cfg_key in params[section].keys():
                if not params[section][cfg_key]:
                    write_string = '#' + cfg_key + '=\n'
                else:
                    write_string = cfg_key + '=' + params[section][cfg_key]
                fd.write(write_string)
        fd.close()
        
    def _get_physical_config(self):
        phys_config = {}
        for config in [self.neutron_config, self.plugin_config]:
            for section in config.sections_dict.keys():
                if section.startswith('apic_switch'):
                    phys_config.setdefault(section, {})
                    cfg = config.get_section_config(section)
                    for k in cfg.keys():
                        phys_config[section][k] = cfg[k]
        return phys_config

    def create_aim_config(self):
        new_section = 'apic'
        old_section = 'ml2_cisco_apic'

        params = self.aim_default_cfg
        self._update_parameters(params, [self.neutron_config,
                                         self.plugin_config])
        self._update_section(new_section, old_section, params)

        # THe system ID needs to be migrated to AIM
        apic_system_id = self.neutron_config.get_section_config(
            'DEFAULT').get('apic_system_id')
        params['aim']['aim_system_id'] = apic_system_id

        # Create aim.conf
        self._write_configuration(params, self.aim_filename)

        params = self.aimctl_default_cfg
        self._update_parameters(params, [self.neutron_config,
                                         self.plugin_config])
        self._update_section(new_section, old_section, params)
 
        # For aimctl.conf, there are some sections that have
        # unique names that need to be added from the legacy
        # configuration
        phys_config = self._get_physical_config()
        for section in phys_config.keys():
            params[section] = phys_config[section]

        # We have to migrate the VMM domains. For now, we
        # just worry about the one in apic_domain_name
        apic_section = (self.neutron_config.get_section_config(old_section) or
                        self.plugin_config.get_section_config(old_section))
        if apic_section.get('apic_domain_name'):
            vmm_dom_name = 'apic_vmdom:' + apic_section['apic_domain_name']
            vmm_dom_name = vmm_dom_name.translate(None, '\n')
            # TODO: add vlan_ranges? Are these only in APIC?
            params[vmm_dom_name] = {}

        # TODO: how to get physdoms?

        # Create aimtcl.conf
        self._write_configuration(params, self.aimctl_filename)
            


class ConfigInfo(object):
    """Configuration File Interface.

    Helper class to get the information from
    an OpenStack configuration file, and look
    for configuration lines under sections. We
    could have just used oslo_config, but that
    requires knowing all of the modules needed
    and registering their configuration options.
    """
    def __init__(self, config_file_name):
        fd = open(config_file_name, 'r')
        self.all_lines = fd.readlines()
        self.sections_dict = {}
        self._parse_config_by_sections()

    def _get_valid_config(self, lines):
        clean_config = [cap for cap in lines
                        if not cap.startswith('#')
                        and not cap == '\n']
        cfg_dict = {}
        for cfg_item in clean_config:
            k, v = cfg_item.split('=', 1)
            cfg_dict[k] = v
        return cfg_dict

    def get_section_config(self, section_name):
        if self.sections_dict.get(section_name):
            return self.sections_dict[section_name]
        else:
            return {}

    def _parse_config_by_sections(self):
        capture_lines = []
        section_name = None
        for index in range(len(self.all_lines)):
            a_line = self.all_lines[index]
            if a_line.startswith('['):
                new_section = a_line.translate(None, '[]\n')
                if not section_name:
                    section_name = new_section
                    self.sections_dict.setdefault(section_name, {})
                else:
                    section_dict = self._get_valid_config(capture_lines)
                    self.sections_dict[section_name] = section_dict
                    section_name = new_section
                    capture_lines = []
            elif section_name:
                capture_lines.append(a_line)
        # Capture final section
        section_dict = self._get_valid_config(capture_lines)
        self.sections_dict[section_name] = section_dict
        return capture_lines


class NeutronConfig(object):
    """Update neutron configuration files.

    The neutron configuration files need updating for several
    steps in the legacy plugin migration process:
    1) Update the configuration with the needed changes
       in order to run the validation tool. This amounts
       to updating the service_plugins, mechanism_drivers,
       core_plugin, etc.
    2) Updating configuration state from the legacy ml2_cisco_apic
       section to the new ml2_apic_aim section
    """
    def __init__(self):
        self.aim_filename = AIM_CFG_FILE_NAME
        self.aimctl_filename = AIMCTL_CFG_FILE_NAME
        self.aim_default_cfg = AIM_DEFAULT_CFG
        self.aimctl_default_cfg = AIMCTL_DEFAULT_CFG
        self.neutron_config = None

    def get_legacy_config(self):
        self.neutron_config = ConfigInfo(NEUTRON_CONF)
        self.plugin_config = ConfigInfo(PLUGIN_CONF)

    # TODO: create APIs for the steps listed above
    #def migrate_md_config(self):
        

