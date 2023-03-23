This directory contains ansible playbooks to update the opflex-agent binaries
in a container, when using Red Hat OpenStack Platform (OSP) Director. There
are three playbooks, two of which are always run:
* update-opflex-agent-binaries.yaml (required)

  This playbook stops the existing container, restarts it without running
  the opflex agent. The tarball with the new binaries are copied into the
  container, and a script is run to un-install the old binaries and install
  the new ones.

* update-opflex-agent-config.yaml (optional)

  This playbook is used to update any configuration file changes needed. The
  playbook provided in this repo has some example tasks, which you can use
  as a reference to tailor this playbook however needed to update any config
  for the agent.

* run-new-opflex-agent.yaml (required)

  This playbook restores the opflex-agent program in the container, and
  restarts the container to run the new opflex agent.

The playbooks should be copied to and run from the undercloud.

# Pre-Upgrade process
Before running the upgrade, you need to prepare a tarball of the new opflex-agent
binaries. The relevant binaries are:
* opflex-agent
* opflex-agent-lib
* opflex-agent-renderer-openvswitch
* noiro-openvswitch-lib
* noiro-openvswitch-otherlib
* prometheus-cpp-lib
* libmodelgbp
* libopflex
* libuv

The RPMs for these files should be tar'd into a file called opflex-agent-tarball.tar, and then
the file should be compressed using gzip, creating the opflex-agent-tarball.tar.gz tarball. That
tarball needs to be copied to the undercloud VM so that the playbooks can be used to install it.

# Upgrade process
1. Obtain the cloud inventory for ansible. Run this from the /home/stack directory:

<pre><code>$ source stackrc
$ tripleo-ansible-inventory --ansible_ssh_user heat-admin --static-yaml-inventory ~/inventory.yaml
</code></pre>

2. ssh into each of the overcloud nodes, to add them to the undercloud's known_hosts file.

<pre><code>$ for server in $(openstack server list -c Networks -f value | awk \
-F"=" '{print $2}'); do ssh heat-admin@$server "ls"; done
</code></pre>

3. Run the playbooks to update the opflex agent on the nodes. You can limit which nodes
   are upgraded using the -l argument:

<pre><code>$ ansible-playbook -i inventory.txt update-opflex-agent-binaries.yaml -l overcloud-novacompute-0
$ ansible-playbook -i inventory.txt update-opflex-agent-config.yaml -l overcloud-novacompute-0
$ ansible-playbook -i inventory.txt run-new-opflex-agent.yaml -l overcloud-novacompute-0
</code></pre>
