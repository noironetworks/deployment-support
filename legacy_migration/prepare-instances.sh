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

# For all running instances....
RUNNING=$(virsh list | grep instance | awk '{print $2}')
echo "Running instances on $(hostname):"
echo "================================="
for INSTANCE in ${RUNNING}; do
    # Dump the XML for the instance to a file
    virsh dumpxml ${INSTANCE}  > ${DIR}/${INSTANCE}.xml
    VMNAME=$(grep nova:name ${DIR}/${INSTANCE}.xml | awk -F'[><]' '{print $3}')
    if [ "${VERBOSE}" = "True" ]; then
        echo "${VMNAME} (${INSTANCE})"
    fi
    # Extract the metadata for the instance, getting rid of the nova
    # namespace and URL and getting rid of the metadata hierarchy
    xmllint --xpath /domain/metadata ${DIR}/${INSTANCE}.xml  | sed -e's/nova://g' | grep -v metadata | sed -e's/instance xmlns.*>/instance>/g' > ${DIR}/metadata.xml

    # See if there are one or more EP files that have a matching vm-name
    # If we can't find one, it's either that the vm-name didn't make
    # it into an EP file, or the instance is lacking a network interface
    # Extract all the bridge interfaces
    IFACES=$(xmllint --xpath '/domain/devices/interface[@type="bridge"]' ${DIR}/${INSTANCE}.xml | grep 'target dev' | awk -F'"' '{print $2}')
    if [ "${IFACES}" != "" ]; then 
        for IFACE in ${IFACES}; do
            # Extract the port UUID and interface name from the EP file
            IFACE_NAME=$(echo ${IFACE} | sed -e's/tap/qvo/g')
            # Extract the external-ids for the port from OVSDB and save for later
            if [ "${VERBOSE}" = "True" ]; then
                echo "    Extracting ${IFACE_NAME} external-ids from OVSDB for ${INSTANCE}"
            fi
            ovs-vsctl get Interface ${IFACE_NAME} external-ids > ${DIR}/${IFACE_NAME}-external-ids.txt
            PORTID=$(cat ${DIR}/${IFACE_NAME}-external-ids.txt | awk -F'"' '{print $4}')
            # We can't update the libvirt XML without a PORTID
            if [ "${PORTID}" = "" ]; then
                # Let user know about this....
                echo "    TAP for ${IFACE_NAME} present in libvirt XML but not in OVSDB"
                continue
            fi

            # Check if there's an EP file for this PORTID
            IF_PRESENT=$(ls ${EPDIR}/${PORTID}*.ep)
            if [ "${IF_PRESENT}" = "" ]; then
                # Let user know about this....
                echo "    TAP for ${IFACE_NAME} present in libvirt XML but not in EP file"
            fi

            # We need to add dummy metadata for each neutron port
            # (which should have a corresponding interface in the XML file).
            if [ "${VERBOSE}" = "True" ]; then
                echo "    Creating extra metadata for port ${PORTID} on instance ${INSTANCE}"
            fi
            cat ${DIR}/metadata.xml | sed -e"3i<${add-PORTID}>$(echo -n x$___{1..200} | tr -d ' ')</${add-PORTID}>"  > ${DIR}/tmp.xml
            mv ${DIR}/tmp.xml ${DIR}/metadata.xml

        done
        # combine into a single compact string
        cat ${DIR}/metadata.xml | tr -d \\n | sed -e's/> *</></g' > ${DIR}/tmp.xml
        mv ${DIR}/tmp.xml ${DIR}/${INSTANCE}-metadata.xml
        # Update the metadata on a running instance
        if [ "${DRYRUN}" != "True" ]; then
            if [ "${VERBOSE}" = "True" ]; then
                echo "    Updating libvirt XML for instance ${INSTANCE}"
            fi
            virsh metadata ${INSTANCE} http://openstack.org/xmlns/libvirt/nova/1.0 --live --key nova --set "`cat ${DIR}/${INSTANCE}-metadata.xml`"
        fi
        # Clean up after ourselves
        rm -f ${DIR}/metadata.xml
    fi
done

# For all shutdown instances....
SHUTDOWN=$(virsh list --all --managed-save | grep 'shut off' | awk '{print $2}')
echo ""
echo "Shutdown instances on $(hostname):"
echo "=================================="
for INSTANCE in ${SHUTDOWN}; do
    virsh dumpxml ${INSTANCE}  > ${DIR}/${INSTANCE}.xml
    VMNAME=$(grep nova:name ${DIR}/${INSTANCE}.xml | awk -F'[><]' '{print $3}')
    if [ "${VERBOSE}" = "True" ]; then
        echo "${VMNAME} (${INSTANCE})"
    fi
    IFACES=$(xmllint --xpath '/domain/devices/interface[@type="bridge"]' ${DIR}/${INSTANCE}.xml | grep 'target dev' | awk -F'"' '{print $2}')
    if [ "${IFACES}" != "" ]; then 
        for IFACE in ${IFACES}; do
            # Extract the external-ids for the port from OVSDB and save for later
            IFACE_NAME=$(echo ${IFACE} | sed -e's/tap/qvo/g')
            if [ "${VERBOSE}" = "True" ]; then
                echo "    Extracting ${IFACE_NAME} external-ids from OVSDB for ${INSTANCE}"
            fi
            ovs-vsctl get Interface ${IFACE_NAME} external-ids > ${DIR}/${IFACE_NAME}-external-ids.txt
        done
    fi
done
