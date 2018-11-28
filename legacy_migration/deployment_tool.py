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

import click
import config_info
from legacy_migration import cfg_mgmt_tool
from legacy_migration import toggle_cfg
from legacy_migration import update_domain


@click.group()
def deployment_tool():
    """Commands for ACI OpenStack deployments"""
    pass


@deployment_tool.command(name="toggle-config")
@click.option('--config-file', multiple=True,
              help='Configuration file name')
@click.option('--toggle', default='new',
              help="Configuration to use. Use 'new' for merged, 'old' for legacy")
def toggle(config_file, toggle):
    toggler = toggle_cfg.ToggleConfig(config_file)
    if toggle == 'new':
        toggler.new_config()
    elif toggle == 'old':
        toggler.old_config()
    toggler.write_config()


@deployment_tool.command(name="aim-config")
@click.option('--config-file', multiple=True,
              help='Configuration file name')
def make_aim_cfg(config_file):
    aim_cfg = cfg_mgmt_tool.AimConfig(config_file)
    aim_cfg.get_legacy_config()
    aim_cfg.create_aim_config()
    click.echo("Generated aim.conf and aimctl.conf.")


@deployment_tool.command(name="get-domains")
@click.option('--credentials-file',
              help='OpenStack admin RC/credentials file')
@click.option('--config-directory',
              help='Directory on computes containing OpFlex agent config.')
@click.option('--output-file',
              help='File to place host/VMM Domain mappings (JSON)')
def update_domains(credentials_file, config_directory, output_file):
    agent_manager = update_domain.OpflexAgentManager(credentials_file,
        config_directory, output_file)
    agent_manager.extract_host_vmm_mappings()
    agent_manager.write_host_mappings()
    click.echo("Wrote host/VMM Domain associations")


@deployment_tool.command(name="update-domains")
@click.option('--input-file',
              help='File containing host/VMM Domain mappings (JSON)')
@click.option('--credentials-file',
              help='OpenStack RC/credentials file')
@click.option('--config-directory',
              help='Directory on computes containing OpFlex agent config.')
def update_domains(credentials_file, config_directory, input_file):
    agent_manager = update_domain.OpflexAgentManager(credentials_file,
        config_directory, input_file)
    agent_manager.read_host_mappings()
    agent_manager.update_host_vmm_mappings()
    agent_manager.update_opflex_host_config()
    click.echo("Updated opflex-agent configuration")


def run():
    deployment_tool(auto_envvar_prefix='DEPLOYMENTTOOL')


if __name__ == '__main__':
    run()
