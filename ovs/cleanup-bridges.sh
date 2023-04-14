#!/bin/sh
for bridge in $(ovs-vsctl show | awk '/Bridge/ {print $2}'  | grep 'int\|fabric'); do
   for interface in $(ovs-ofctl show $bridge | grep addr | awk -F"(" '{print $2}' | awk -F")" '{print $1}'); do
       if [[ "$interface" != "$bridge" ]]; then
           echo "ovs-vsctl del-port $bridge $interface"
       fi
   done;
done
