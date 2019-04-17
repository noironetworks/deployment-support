support-tools
=============

Scripts and documents for support.

This repo contains tools and scripts that can be used
to support noironetworks OpenStack deployments. Although
many of the scripts will run out of the box, they are meant
to be used as references, and may need to be modified and/or
adapted, depending on the installation.

Here is a list of the included scripts:

db_check.sh
-----------

The db_check.sh script checks to see if there are any issues
with AIM database migrations. It queries the current head
in the AIM alembic migrations table, and checks that against
the expected head, which is defined in the installed AIM
source code. It lets the user know whether or not all of
DB migrations have been run. This script should be run
from the undercloud VM (either JuJu or OpenStack Director).


support_tool
------------

This tool contains commands that are helpful for users
that are migrating from the legacy ML2 plugin to the
unified plugin. The tool contains several sub-commands:

* aim-config
This sub-command inspects existing neutron configuration
files for configuration needed in the AIM configuration files,
and uses that information to construct the aim.conf and aimctl.conf
configuration files. These files are installed under /etc/aim.
This command should be run on each neutron controller.
::
    options:
     --config-file: specify a configuration file that contains
                    state needed for AIM configuration. This
                    option can be specified multiple times, one
                    for each configuration file needed.

    example:
    support_tool aim-config --config-file /etc/neutron/neutron.conf \
             --config-file /etc/neutron/plugins/ml2/ml2_conf.ini

* get-domains
This subcommand must be run from a neutron controller. It uses
a credentials file to execute neutron client commands and find
hosts running neutron-opflex-agents, then looks up the
IP addresses of those hosts and ssh's into them and extracts
the VMM domains and puts them into a json file:
::
    {
        "f2-compute-1.noiro.lab": "ostack",
        "f2-compute-2.noiro.lab": "ostack"
    }

    options:
    --credentials-file OpenStack admin RC/credentials file
                       (default is /root/keystonerc_admin)
    --config-directory Directory on computes containing OpFlex agent
                       config (default is /etc/opflex-agent-ovs/conf.d)
    --output-file      File to place host/VMM Domain mappings (JSON)
                       (default is opflex_hosts.txt)

    example:
    support_tool get-domains --credentials-file /home/admin/adiminrc \
                              --config-directory /etc/opflexaagent-ovs \
                              --output-file vmm-doms.txt

* update-domains
This subcommand must be run from a neutron controller. It uses
a credentials file so that it can execute neutron client commands
to find hosts running neutron-opflex-agents, then looks up the
IP addresses of those hosts and ssh's into them and updates the
VMM domains using mapping information contained in a json file.
::
    options:
    --input-file TEXT        File containing host/VMM Domain mappings (JSON)
    --credentials-file TEXT  OpenStack RC/credentials file
    --config-directory TEXT  Directory on computes containing OpFlex agent
                             config.

    example:
    support_tool update-domains --input-file vmm-doms.txt \
                                --credentials-file /home/admin/adiminrc \
                                --config-directory /etc/opflexaagent-ovs

* toggle-config
This toggles the neutron configuration between the legacy ML2 driver 
and the unified mechanism driver.
::
    options:
    --config-file TEXT  Configuration file name
    --toggle TEXT       Configuration to use. Use 'new' for merged, 'old' for
                        legacy

    example:
    support_tool toggle-config --config-file /etc/neutron/neutron.conf \
             --config-file /etc/neutron/plugins/ml2/ml2_conf.ini \
             --toggle new
