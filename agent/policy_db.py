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

import policy_config


@click.group()
def policy_db():
    """Commands for Opflex policy collection and introspection"""
    pass

@policy_db.command(name="ep-info")
@click.option('--policy-file',required=True,
              help='Policy file name (JSON)')
@click.option('--endpoint', required=True,
              help='ID of endpoint (L2 MAC or L3 IP)')
def ep_info(policy_file, endpoint):
    policy_conf = policy_config.PolicyConfigManager(policy_file)
    policy_conf.get_policy_for_ep(endpoint)


@policy_db.command(name="list-l2-eps")
@click.option('--policy-file',required=True,
              help='Policy file name (JSON)')
def list_l2_eps(policy_file):
    policy_conf = policy_config.PolicyConfigManager(policy_file)
    policy_conf.list_l2_eps()


@policy_db.command(name="list-l3-eps")
@click.option('--policy-file',required=True,
              help='Policy file name (JSON)')
def list_l3_eps(policy_file):
    policy_conf = policy_config.PolicyConfigManager(policy_file)
    policy_conf.list_l3_eps()


@policy_db.command(name="list-vms")
@click.option('--policy-file',required=True,
              help='Policy file name (JSON)')
def list_vms(policy_file):
    policy_conf = policy_config.PolicyConfigManager(policy_file)
    policy_conf.list_vms()


@policy_db.command(name="find-policy")
@click.option('--policy-file',required=True,
              help='Policy file name (JSON)')
@click.option('--policy-name',required=True,
              help='Name of the type of policy objects to find')
def find_policy(policy_file, policy_name):
    policy_conf = policy_config.PolicyConfigManager(policy_file)
    policy_conf.list_objects_by_type(policy_name)


def run():
    policy_db(auto_envvar_prefix='POLICYDB')


if __name__ == '__main__':
    run()
