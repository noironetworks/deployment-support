#!/bin/sh
PRJ=$1
echo ${PRJ}
for count in `seq 5`; do
    nova --os-project-name ${PRJ} delete net1_vm$count
done
for count in `seq 5`; do
    nova --os-project-name ${PRJ} delete net2_vm$count
done
neutron --os-project-name ${PRJ} router-gateway-clear ${PRJ}-router
neutron --os-project-name ${PRJ} router-interface-delete ${PRJ}-router ${PRJ}-subnet1
neutron --os-project-name ${PRJ} router-interface-delete ${PRJ}-router ${PRJ}-subnet2
neutron --os-project-name ${PRJ} router-delete ${PRJ}-router
neutron --os-project-name ${PRJ} net-delete ${PRJ}-net2
neutron --os-project-name ${PRJ} net-delete ${PRJ}-net1
for fip in $(neutron --os-project-name ${PRJ} floatingip-list -c id -f value); do
    neutron --os-project-name ${PRJ} floatingip-delete $fip;
done

neutron --os-project-name ${PRJ} security-group-delete ${PRJ}-sg
PRJID=$(openstack project show ${PRJ} -c id -f value)
DEF_SEC_ID=$(openstack security group list | grep ${PRJID} | awk '{print $2}')
neutron --os-project-name ${PRJ} security-group-delete ${DEF_SEC_ID}
if [ "${PRJ}" != "admin" ]; then
    openstack project delete ${PRJ}
fi
