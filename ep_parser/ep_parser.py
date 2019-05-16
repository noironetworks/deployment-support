# Copyright (c) 2019 Cisco Systems
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

import ep_lib


@click.group()
def ep_parser():
    """Commands for Opflex policy collection and introspection"""
    pass

@ep_parser.command(name="dump")
@click.option('--ep-file',required=True,
              help='Endpoint file name (JSON)')
def ep_dump(ep_file):
    ep_conf = ep_lib.EPManager(ep_file)
    ep_conf.ep_dump()

@ep_parser.command(name="get-param")
@click.option('--ep-file',required=True,
              help='Endpoint file name (JSON)')
@click.option('--param',required=True,
              help='Get a parameter from ep file, parameter can be one of: uuid, metadata_opt, os_domain, ip_addr, mac_addr, gateway, static_routes, access_interface, uplink_interface, vrf, epg, tenant, net_uuid, sec_groups, attributes ')
def get_param(ep_file,param):
    ep_conf = ep_lib.EPManager(ep_file)
    ep_conf.get_param(param)


def run():
    ep_parser(auto_envvar_prefix='EPPARSER')


if __name__ == '__main__':
    run()
