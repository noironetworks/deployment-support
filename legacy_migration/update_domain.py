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

import json
import paramiko
import subprocess
import time


CMD_TIME_WAIT = 15

# Where things usually live
RC_FILE='/root/keystonerc_admin'
DEFAULT_CFG_DIR = '/etc/opflex-agent-ovs/conf.d'
DEFAULT_OUTPUT_FILE = 'opflex_hosts.txt'
OPFLEX_DOMAIN_STRING = 'comp/prov-OpenStack/ctrlr-[%(dom)s]-%(dom)s/sw-InsiemeLSOid'


class SshMixin(object):
    """Simple wrapper class for SSH methods.

    Created to simplify SSH methods needed from paramiko
    """

    def __init__(self):
        self.ssh_clients = {}

    def get_ssh_client(self, host, username='root'):
        ssh_client = self.ssh_clients.get(host)
        if not ssh_client:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.load_system_host_keys()
            ssh_client.connect(host, username=username)
            self.ssh_clients[host] = ssh_client
        return ssh_client

    def remote_cmd(self, ssh_client, cmd, wait=CMD_TIME_WAIT):
        ssh_stdin, ssh_stdout, ssh_stderr = ssh_client.exec_command(cmd)
        if wait:
            endtime = time.time() + wait
            while not ssh_stdout.channel.eof_received:
                time.sleep(1)
                if time.time() > endtime:
                    ssh_stdout.channel.close()
                    return []
        return ssh_stdout.read(), ssh_stderr.read()


class OpflexAgentManager(SshMixin):
    """Configuration File Manager for hosts running OpFlex Agents.

    This has methods to get host <=> VMM Domain mappings for OpFlex
    agents in an OpenStack installation. Hosts are determined by
    querying neutron for all active OpFlex agents. The mapping file
    can be retrieved from an active system, then updated/edited
    manually, and then used to update the agent configuration file
    on all the hosts. This must be run from a host that has CLI access
    to the OpenStack controller and ssh access to all hosts running 
    OpFlex agents.
    """

    def __init__(self, rcfile, config_dir, host_vmm_file):
        if not config_dir:
            config_dir = DEFAULT_CFG_DIR
        if not host_vmm_file:
            host_vmm_file = DEFAULT_OUTPUT_FILE
        if not rcfile:
            rcfile = RC_FILE
        self._hosts = []
        self._host_configs = {}
        self.host_vmm_mappings = {}
        self.rcfile = rcfile
        self.host_vmm_file = host_vmm_file
        self.config_dir = config_dir
        self.KEY = 'source ' + self.rcfile + ' && '
        super(OpflexAgentManager, self).__init__()

    @property
    def hosts(self):
        if not self._hosts:
            self._hosts = self.get_active_opflex_hosts()
        return self._hosts

    @property
    def host_configs(self):
        if not self._host_configs:
            self._host_configs = self.get_opflex_host_config()
        return self._host_configs

    def get_active_opflex_hosts(self):
        """Return all the hosts in the deployment with live OpFlex agents."""
        cmd1 = "neutron agent-list | grep OpFlex | grep ':-)'"
        cmd2 = " | awk -F'|' '{print $4}'"
        cmd = self.KEY + cmd1 + cmd2
        hosts = subprocess.check_output(['bash','-c', cmd])
        all_hosts = [host.strip() for host in hosts.split("\n") if host]
        return all_hosts

    def get_opflex_host_config(self):
        """Get list of per-host OpFlex configuration files.

        OpFlex agents can have more than one configuration file. Create
        a dict that maps hostnames to lists of tuples, where each tuple
        contains the full path of the OpFlex configuration file and the
        object that holds the file's contents.
        """
        host_configs = {}
        for host in self.hosts:
            ssh_client = self.get_ssh_client(host)
            cmd = 'ls ' + self.config_dir
            cfg_files, _ = self.remote_cmd(ssh_client, cmd) 
            # make sure we have a list of config files
            cfg_file_list = " ".join(cfg_files.split()).split()
            for cfg_file in cfg_file_list:
                cmd = 'cat ' + self.config_dir + '/' + cfg_file
                cfg_data, _ = self.remote_cmd(ssh_client, cmd) 
                host_configs.setdefault(host, []).append(
                    (cfg_file, OpflexConfig(cfg_data)))
        return host_configs

    def update_opflex_host_config(self):
        """Update OpFlex config on the hosts running OpFlex agents.

        This updates the configuration files on each active OpFlex host.
        This should be run after the host <=> VMM domain mappings have
        been updated.
        """
        host_configs = {}
        for host, vmm in self.host_vmm_mappings.iteritems():
            if host not in self.hosts:
                print "Skipping host %s, which wasn't seen" % host
                continue
            ssh_client = self.get_ssh_client(host)
            for cfg_file, cfg_obj in self.host_configs[host]:
                cmd1 = "echo '" + json.dumps(cfg_obj.json_config,
                                               indent=4, sort_keys=True)
                cmd2 = "' > " + self.config_dir + '/' + cfg_file
                cmd = cmd1 + cmd2
                self.remote_cmd(ssh_client, cmd) 
        return host_configs
                    
    def extract_host_vmm_mappings(self):
        """Retrieve host to VMM domain mappings from agents.

        Extract the VMM domains configuration from each host
        running an OpFlex agent, and return the mapping as a dict.
        """
        vmm_mappings = {}
        for host in self.hosts:
            for cfg_file, cfg_obj in self.host_configs[host]:
                if cfg_obj.json_config.get('opflex') and (
                        cfg_obj.json_config['opflex'].get('domain')):
                    domain = cfg_obj.json_config['opflex']['domain']
                    vmm = domain[domain.index('[')+1:domain.index(']')]
                    vmm_mappings[host] = vmm
                    break
        self.host_vmm_mappings = vmm_mappings
        return vmm_mappings

    def update_host_vmm_mappings(self):
        """Update agent configuration file objects with the new mappings.

        THe configuration files will need to be written back to the hosts,
        but the files must first be updated with the new mapping information.
        """
        for host, vmm in self.host_vmm_mappings.iteritems():
            if host not in self.hosts:
                print "Skipping host %s, which wasn't seen" % host
                continue
            for cfg_file, cfg_obj in self.host_configs[host]:
                if cfg_obj.json_config.get('opflex') and (
                        cfg_obj.json_config['opflex'].get('domain')):
                    domain = OPFLEX_DOMAIN_STRING % {'dom': vmm}
                    cfg_obj.json_config['opflex']['domain'] = domain

    def write_host_mappings(self):
        """Store current mappings to a file"""
        with open(self.host_vmm_file, 'w+') as fd:
            json.dump(self.host_vmm_mappings, fd, indent=4, sort_keys=True)

    def read_host_mappings(self):
        """Retrieve new mappings from a file"""
        with open(self.host_vmm_file, 'r') as fd:
            self.host_vmm_mappings = json.load(fd)


class OpflexConfig(object):
    """Update the VMM domain in the opflex configuration file

    The opflex-agent configuration file is mostly JSON, but it
    allows C++ style commenting.
    """

    def __init__(self, raw_cfg_data):
        self._raw_cfg_data = raw_cfg_data
        self._preprocessed_config = []
        self._json_config = {}

    @property
    def preprocessed_config(self):
        """Remove invalid JSON characters.

        The opflex-agent configuration file supports C++ style
        commenting. Strip out these characters so that the data
        can be loaded as JSON if needed.
        """
        if not self._preprocessed_config:
            preprocessed_data = []
            for line in self._raw_cfg_data.splitlines():
                lastidx = line.find('//')
                if lastidx == -1:
                    lastidx = len(line)
                preprocessed_data.append(line[0:lastidx])
            self._preprocessed_config = "".join(preprocessed_data)
        return self._preprocessed_config
        
    @property
    def json_config(self):
        """Convert raw data to JSON.

        We convert the OpFlex agent configuration file data to
        JSON in order to make it easier to search, modify, and
        write out any configuration changes.
        """
        if not self._json_config:
            self._json_config = json.loads(self.preprocessed_config)
        return self._json_config

