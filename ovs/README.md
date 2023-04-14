This directory contains tooling that is helpful if a customer's data plane
needs to be reconstructed. 

There are two compoents to the tooling:
1) python script to create shell script for creating the same
   network ports/interfaces that are connected to OVS and namespaces
2) shell script to convert ovs-ofctl flow dumps into commands to
   create flow-mods.

The python script is used as follows:

````
    # python3 --bridgefile ovs-ports --bridgefile ovs-ports-fabric --outfile config-bridges.sh

````

This creates a "config-bridges.sh" script, which can be run to create
the relevant tap ports, patch ports, etc. You can use the --outfile argument
to create a different destination file. Note that both the br-int and br-fabric
files are needed in order for the python program to work.

A simpler way to recreate the bridges and ports is to obtain the OVSDB
database, and simply import that. However, that component may not always
be available, but the output of the "ovs-ofctl show <bridge name>" usually is.

Before running that script, you can run the cleanup-bridges.sh script to remove
any ports from the br-int and br-fabric bridges from an existing setup:

````
    # sh ./cleanup-bridges.sh


The shell script is run as follows:
````
    sh ./create-flowmods.sh <file containing ovs-ofctl dump for a bridge> <name of bridge> > <output-file>
````

As an example:
````
    # sh ./create-flowmods.sh flowmod-dump.txt br-fabric > create-br-fabric-flows.sh
````
