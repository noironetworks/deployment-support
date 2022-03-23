This directory contains tooling that is helpful if a customer's data plane
needs to be reconstructed. 

There are two compoents to the tooling:
1) python script to create shell script for creating the same
   network ports/interfaces that are connected to OVS and namespaces
2) shell script to convert ovs-ofctl flow dumps into commands to
   create flow-mods.

The python script is used as follows:

[root@overcloud-novacompute-0 OOpenFlow13]# python
Python 3.6.8 (default, Aug  3 2021, 06:54:29)
[GCC 8.3.1 20191121 (Red Hat 8.3.1-5)] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import bridge_ifs
>>> mgr = bridge_ifs.OVSInterfaceParser()
>>> mgr.parse_ports('OOpenFlow-int-brfabric')
>>> mgr.parse_ports('OOpenFlow-int-brint')
>>> mgr.create_script_file()

This creates a "config-bridges.sh" script, which can be run to create
the relevant tap ports, patch ports, etc.

A simpler way to recreate the bridges and ports is to obtain the OVSDB
database, and simply import that. However, that component may not always
be available, but the output of the "ovs-ofctl show <bridge name>" usually is.

The shell script is run as follows:
    sh ./create-flowmods.sh <file containing ovs-ofctl dump for a bridge> <name of bridge> > <output-file>

As an example:
    # sh ./create-flowmods.sh flowmod-dump.txt br-fabric > create-br-fabric-flows.sh
