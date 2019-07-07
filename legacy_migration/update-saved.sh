#!/bin/sh

# Change this to whatever dir you want to store the files
DIR="`pwd`/migration-data"
# Set to "False" to prevent any updates of libvirt
DRYRUN="False"
VERBOSE="True"
EPDIR="/var/lib/opflex-agent-ovs/endpoints"
if [ ! -d ${EPDIR} ]; then
    echo "${EPDIR} does not exist (neutron-opflex-agent host?)"
    exit
fi
if [ ! -d ${DIR} ]; then
    echo "${DIR} does not exist. Please create before running"
    exit
fi

# We don't have EP files or state in OVSDB for suspended instances, so
# we rely on files left behind by the prepare-instances.sh script

# For all suspended instances....
RUNNING=$(virsh list --all --managed-save | grep saved | awk '{print $2}')
echo "Running instances on $(hostname):"
echo "================================="
for INSTANCE in ${RUNNING}; do
    # Get the managedsave XML state, save a rollback file
    virsh managedsave-dumpxml ${INSTANCE} > ${DIR}/${INSTANCE}-rollback.xml
    VMNAME=$(grep nova:name ${DIR}/${INSTANCE}-rollback.xml | awk -F'[><]' '{print $3}')
    if [ "${VERBOSE}" = "True" ]; then
        echo "${VMNAME} (${INSTANCE})"
    fi
    cp ${DIR}/${INSTANCE}-rollback.xml ${DIR}/update.xml
    # Extract all the bridge interfaces
    IFACES=$(xmllint --xpath '/domain/devices/interface[@type="bridge"]' ${DIR}/${INSTANCE}-rollback.xml | grep 'target dev' | awk -F'"' '{print $2}')
    if [ "${IFACES}" != "" ]; then 
        for IFACE in ${IFACES}; do
            BRNAME=$(echo ${IFACE} | sed -e's/tap/qbr/g')
            IFACE_NAME=$(echo ${IFACE} | sed -e's/tap/qvo/g')
            # Get the neutron port UUID
            PORTID=$(cat ${DIR}/${IFACE_NAME}-external-ids.txt | awk -F'"' '{print $4}')
            # remove the dummy metadata tag and data,  move to br-int, and update the virtual interface to OVS
            if [ "${VERBOSE}" = "True" ]; then
                echo "    Converting ${IFACE_NAME} to OVS(${PORTID})"
            fi
            # This probably could be one step, but leaving it for someone cleverer than me to fix
            grep -v ${add-PORTID} ${DIR}/update.xml | sed -e"s/<source bridge='${BRNAME}'\/>/<source bridge='br-int'\/>\n\t<virtualport type='openvswitch'>\n\t\t<parameters interfaceid='${PORTID}'\/>\n\t<\/virtualport>/g" > ${DIR}/tmp.xml
            mv ${DIR}/tmp.xml ${DIR}/update.xml

            # Clear the external-ids for the old qvo port in OVSDB
            if [ "${DRYRUN}" != "True" ]; then
                if [ "${VERBOSE}" = "True" ]; then
                    echo "    Removing external-ids data from ${IFACE_NAME} in OVSDB"
                fi
                ovs-vsctl set Interface ${IFACE_NAME} external-ids={}
            fi
        done
        # Update the suspended instance’s XML
        if [ "${DRYRUN}" != "True" ]; then
            if [ "${VERBOSE}" = "True" ]; then
                echo "    Updating managed save XML for ${INSTANCE}"
            fi
            virsh managedsave-define ${INSTANCE} ${DIR}/update.xml
        fi
        # Clean up after ourselves
        rm -f ${DIR}/update.xml
    fi
done

# For all shutdown instances....
SHUTDOWN=$(virsh list --all --managed-save | grep 'shut off' | awk '{print $2}')
echo ""
echo "Shutdown instances on $(hostname):"
echo "=================================="
for INSTANCE in ${SHUTDOWN}; do
    virsh dumpxml ${INSTANCE} > ${DIR}/shutdown.xml
    VMNAME=$(grep nova:name ${DIR}/shutdown.xml | awk -F'[><]' '{print $3}')
    if [ "${VERBOSE}" = "True" ]; then
        echo "${VMNAME} (${INSTANCE})"
    fi
    IFACES=$(xmllint --xpath '/domain/devices/interface[@type="bridge"]' ${DIR}/shutdown.xml | grep 'target dev' | awk -F'"' '{print $2}')
    if [ "${IFACES}" != "" ]; then 
        for IFACE in ${IFACES}; do
            # Clear the external-ids for the old qvo port in OVSDB
            IFACE_NAME=$(echo ${IFACE} | sed -e's/tap/qvo/g')
            if [ "${DRYRUN}" != "True" ]; then
                if [ "${VERBOSE}" = "True" ]; then
                    echo "    Removing external-ids data from ${IFACE_NAME} in OVSDB"
                fi
                ovs-vsctl set Interface ${IFACE_NAME} external-ids={}
            fi
        done
    fi
    # Clean up after ourselves
    rm -f ${DIR}/shutdown.xml
done
