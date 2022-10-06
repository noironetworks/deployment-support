#!/bin/sh
egrep -v OFPST_FLOW $1 | sed -e "s/^.*, table=/ovs-ofctl add-flow $2 -OOpenFlow13 \"table=/g" | sed -e 's/, n_packets=.*priority=/,priority=/g' | sed -e 's/ actions=/,actions=/g' | sed -e 's/$/"/g'
