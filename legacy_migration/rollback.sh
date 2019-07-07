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
    # Get the managedsave XML state
    virsh managedsave-dumpxml ${INSTANCE} > ${DIR}/${INSTANCE}-saved.xml
    VMNAME=$(grep nova:name ${DIR}/${INSTANCE}.xml | awk -F'[><]' '{print $3}')
    if [ "${VERBOSE}" = "True" ]; then
        echo "${VMNAME} (${INSTANCE})"
    fi
    # Extract all the bridge interfaces
    IFACES=$(xmllint --xpath '/domain/devices/interface[@type="bridge"]' ${DIR}/${INSTANCE}-saved.xml | grep 'target dev' | awk -F'"' '{print $2}')

    # Sanity-check: make sure we have the same number of
    # interfaces as before
    ROLLBACK_IFS=$(xmllint --xpath '/domain/devices/interface[@type="bridge"]' ${DIR}/${INSTANCE}-rollback.xml | grep 'target dev' | awk -F'"' '{print $2}')
    if [ "${IFACES}" != "${ROLLBACK_IFS}" ]; then
        echo "    Inconsistent interfaces for Instance ${VMNAME} (${INSTANCE}): saved: ${IFACES} rollback: ${ROLLBACK_IFS}"
        continue
    fi
    if [ "${IFACES}" != "" ]; then 
        for IFACE in ${IFACES}; do
            BRNAME=$(echo ${IFACE} | sed -e's/tap/qbr/g')
            IFACE_NAME=$(echo ${IFACE} | sed -e's/tap/qvo/g')
            # Clear the external-ids for the old qvo port in OVSDB
            if [ "${DRYRUN}" != "True" ]; then
                if [ "${VERBOSE}" = "True" ]; then
                    echo "    Restoring external-ids data for ${IFACE_NAME} in OVSDB"
                fi
                ovs-vsctl set Interface ${IFACE_NAME} external-ids="$(cat ${DIR}/${IFACE_NAME}-external-ids.txt)"
            fi
        done
        # Update the suspended instance’s XML
        if [ "${DRYRUN}" != "True" ]; then
            if [ "${VERBOSE}" = "True" ]; then
                echo "    Updating managed save XML for ${INSTANCE}"
            fi
            grep -v ${add-PORTID} ${DIR}/${INSTANCE}-rollback.xml > ${DIR}/tmp.xml
            virsh managedsave-define ${INSTANCE} ${DIR}/tmp.xml
        fi
        rm -f ${DIR}/tmp.xml
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
            # Restore the external-ids for the old qvo ports in OVSDB
            IFACE_NAME=$(echo ${IFACE} | sed -e's/tap/qvo/g')
            if [ "${DRYRUN}" != "True" ]; then
                if [ "${VERBOSE}" = "True" ]; then
                    echo "    Restoring external-ids data for ${IFACE_NAME} in OVSDB"
                fi
                ovs-vsctl set Interface ${IFACE_NAME} external-ids="$(cat ${DIR}/${IFACE_NAME}-external-ids.txt)"
            fi
        done
    fi
    # Clean up after ourselves
    rm -f ${DIR}/shutdown.xml
done
