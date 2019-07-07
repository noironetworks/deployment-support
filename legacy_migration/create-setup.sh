#!/bin/sh
PRJ=$1
echo "Creating resources for project ${PRJ}"
if [ "${PRJ}" != "admin" ]; then
    openstack project create ${PRJ}
    openstack role add --project ${PRJ} --user admin admin
fi

neutron --os-project-name ${PRJ} security-group-create ${PRJ}-sg
neutron --os-project-name ${PRJ} security-group-rule-create --direction ingress --remote-ip-prefix 0.0.0.0/0 ${PRJ}-sg

neutron --os-project-name ${PRJ} net-create ${PRJ}-net1
neutron --os-project-name ${PRJ} subnet-create ${PRJ}-net1 40.40.40.0/24 --name ${PRJ}-subnet1
neutron --os-project-name ${PRJ} net-create ${PRJ}-net2
neutron --os-project-name ${PRJ} subnet-create ${PRJ}-net2 50.50.50.0/24 --name ${PRJ}-subnet2
neutron --os-project-name ${PRJ} router-create ${PRJ}-router
neutron --os-project-name ${PRJ} router-interface-add ${PRJ}-router ${PRJ}-subnet1
neutron --os-project-name ${PRJ} router-interface-add ${PRJ}-router ${PRJ}-subnet2
neutron --os-project-name ${PRJ} router-gateway-set ${PRJ}-router l3out-2
NET1_ID=$(neutron --os-project-name ${PRJ} net-show ${PRJ}-net1 -c id -f value)
NET2_ID=$(neutron --os-project-name ${PRJ} net-show ${PRJ}-net2 -c id -f value)
EXT_NET_ID=$(neutron --os-project-name ${PRJ} net-show l3out-2 -c id -f value)
for count in `seq 5`; do
    nova --os-project-name ${PRJ} boot --flavor m1.tiny --image cirros.new --nic net-id=${NET1_ID} --security-group ${PRJ}-sg net1_vm$count
done
for count in `seq 5`; do
    nova --os-project-name ${PRJ} boot --flavor m1.tiny --image cirros.new --nic net-id=${NET2_ID} --security-group ${PRJ}-sg net2_vm$count
done
sleep 5
nova --os-project-name ${PRJ} interface-attach --net-id ${EXT_NET_ID} net1_vm5
nova --os-project-name ${PRJ} interface-attach --net-id ${EXT_NET_ID} net2_vm5
nova --os-project-name ${PRJ} interface-attach --net-id ${NET2_ID} net1_vm2
nova --os-project-name ${PRJ} interface-attach --net-id ${NET1_ID} net2_vm2
FIP1=$(neutron --os-project-name ${PRJ} floatingip-create l3out-2 -c id -f value)
FIP2=$(neutron --os-project-name ${PRJ} floatingip-create l3out-2 -c id -f value)
IP1=$(openstack --os-project-name ${PRJ} server show net1_vm3 -c addresses -f value | awk -F"=" '{print $2}')
SUB1_ID=$(neutron --os-project-name ${PRJ} subnet-show ${PRJ}-subnet1 -c id -f value)
SUB2_ID=$(neutron --os-project-name ${PRJ} subnet-show ${PRJ}-subnet2 -c id -f value)
PORT1_ID=$(neutron --os-project-name ${PRJ} port-list | grep ${SUB1_ID} | grep ${IP1} | awk '{print $2}')
IP2=$(openstack --os-project-name ${PRJ} server show net2_vm3 -c addresses -f value | awk -F"=" '{print $2}')
PORT2_ID=$(neutron --os-project-name ${PRJ} port-list | grep ${SUB2_ID} | grep ${IP2} | awk '{print $2}')
neutron --os-project-name ${PRJ} floatingip-associate ${FIP1} ${PORT1_ID}
neutron --os-project-name ${PRJ} floatingip-associate ${FIP2} ${PORT2_ID}
