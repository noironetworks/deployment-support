#!/bin/bash
DEBUG="ON"


# First figure out if we're debian or RPM
DISTRO=`lsb_release -a | grep Distributor | awk '/(.*):/ {print $3}'`
RHEL='RedHatEnterpriseServer'
UBUNTU='Ubuntu'

# N
NEWTON_VER="9"
OCATA_VER="10"
PIKE_VER="11"
QUEENS_VER="12"
NEUTRON_CONF="/etc/neutron/neutron.conf"

CMD_PREFIX=""

CREDENTIALS_FILE="my.cnf"

do_print () {
  if [ "${DEBUG}" != "" ]; then
      echo "${PRINT_STRING}"
  fi
}
# Assume not JuJu to start
DO_JUJU=""
JUJU_STATUS=""
if [ "${DISTRO}" = "${RHEL}" ]; then
    PRINT_STRING="Distro type: Red Hat"
    do_print
    MYSQL_USER="heat-admin@"
    NEUTRON_USER="heat-admin@"
    PACKAGE_TYPE="site-packages"

    MYSQL_HOSTNAME="overcloud-controller-0"
    NEUTRON_HOSTNAME="overcloud-controller-0"
    MYSQL_CONF=${NEUTRON_CONF}

    MYSQL_HOST=`. stackrc && nova list | grep ${MYSQL_HOSTNAME} | awk '{print $12}' | sed -nre 's/^[^0-9]*(([0-9]+\.)*[0-9]+).*/\1/p'`
    NEUTRON_HOST=${MYSQL_HOST}

    DB_USER_REGEX="| awk -F'/' '{print \$3}' | awk -F':' '{print \$1}'"
    DB_PASSWORD_REGEX="| awk -F':' '{print \$3}' | awk -F'@' '{print \$1}'"
    DB_USER_SEARCH="'^connection'"
    DB_PASSWORD_SEARCH="'^connection'"

    NEUTRON_VER=`ssh ${MYSQL_USER}${NEUTRON_HOST} "rpm -qa" |sed -ne 's/openstack-neutron-\(\([0-9]\.\)\{0,4\}[0-9][^.]\).*/\1/p'`
    if [ "${NEUTRON_VER}" = "${QUEENS_VER}" ]; then
        CMD_PREFIX="sudo docker exec -itu root "
        NEUTRON_CONF="/var/lib/config-data/puppet-generated/neutron/etc/neutron/neutron.conf"
    fi
elif [ "${DISTRO}" = "${UBUNTU}" ]; then
    PRINT_STRING="Distro type: Ubuntu"
    do_print
    DO_JUJU="juju"
    JUJU_STATUS="juju status "

    MYSQL_USER=""
    NEUTRON_USER=""
    PACKAGE_TYPE="dist-packages"

    MYSQL_HOSTNAME="mysql/0*"
    NEUTRON_HOSTNAME="neutron-api/0*"
    MYSQL_CONF="/etc/mysql/debian.cnf"

    MYSQL_HOST=`${JUJU_STATUS} | grep ${MYSQL_HOSTNAME}| awk '{print $4}'`
    PRINT_STRING="MySQL Host: ${MYSQL_HOST}"
    do_print
    NEUTRON_HOST=`${JUJU_STATUS} | grep ${NEUTRON_HOSTNAME} | awk '{print $4}'`
    PRINT_STRING="Neutron Host: ${NEUTRON_HOST}"
    do_print

    DB_USER_REGEX="| awk '/(.*)=/ {print \$3}'"
    DB_PASSWORD_REGEX="| awk '/(.*)=/ {print \$3}'"
    DB_USER_SEARCH="user"
    DB_PASSWORD_SEARCH="password"

fi


# Get the name of the neutron DB from the configuration
DB_NAME=`${DO_JUJU} ssh ${NEUTRON_USER}${NEUTRON_HOST} "sudo egrep '^connection' ${NEUTRON_CONF}" | awk -F'/' '{print $4}' | awk -F'?' '{print $1}' | sed 's/\r$//g'`
PRINT_STRING="DB Name: ${DB_NAME}"
do_print
DB_USER=`${DO_JUJU} ssh ${MYSQL_USER}${MYSQL_HOST} "sudo egrep -m 1 ${DB_USER_SEARCH} ${MYSQL_CONF}"  ${DB_USER_REGEX}`
PRINT_STRING="DB User: ${DB_USER}"
do_print
DB_PASSWORD=`${DO_JUJU} ssh ${MYSQL_USER}${MYSQL_HOST} "sudo egrep -m 1 ${DB_PASSWORD_SEARCH} ${MYSQL_CONF}"  ${DB_PASSWORD_REGEX}`
PRINT_STRING="DB Password: ${DB_PASSWORD}"
do_print

# Create a credentials file so we don't have to enter a password for mysql
PRINT_STRING="Creating /tmp/${CREDENTIALS_FILE}"
do_print
echo "[client]" > /tmp/${CREDENTIALS_FILE}
echo "user=${DB_USER}" >> /tmp/${CREDENTIALS_FILE}
echo "password=${DB_PASSWORD}" >> /tmp/${CREDENTIALS_FILE}

DUMMY=`${DO_JUJU} scp /tmp/${CREDENTIALS_FILE} ${MYSQL_USER}${MYSQL_HOST}:/tmp/${CREDENTIALS_FILE}`
PRINT_STRING="DB Name: ${DB_NAME}"
do_print
SSH_CMD="sudo mysql --defaults-file=/tmp/${CREDENTIALS_FILE} ${DB_NAME} -e 'select * from aim_alembic_version;' | grep [0-9]"
DB_HEAD=`${DO_JUJU} ssh ${MYSQL_USER}${MYSQL_HOST} "${SSH_CMD}"`
AIM_HEAD=`${DO_JUJU} ssh ${NEUTRON_USER}${NEUTRON_HOST} "sudo cat /usr/lib/python2.7/${PACKAGE_TYPE}/aim/db/migration/alembic_migrations/versions/HEAD"`
PRINT_STRING="AIM head: ${AIM_HEAD}"
do_print
PRINT_STRING="DB head: ${DB_HEAD}"
do_print

# Clean up after ourselves
DUMMY=`${DO_JUJU} ssh ${MYSQL_USER}${MYSQL_HOST} "rm -f /tmp/${CREDENTIALS_FILE}"`
rm -f /tmp/${CREDENTIALS_FILE}

if [ "${AIM_VER}" != "${HEAD}" ]; then
    echo "AIM DB migration was not completed Target HEAD: ${AIM_HEAD}, Current HEAD: ${DB_HEAD} -- please contact TAC for support"
else
    echo "AIM DB is valid"
fi
