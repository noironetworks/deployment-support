#!/bin/sh
CHECK_ONLY=$1
REPLACE_LIBUV=0
CURR_OPFLEX_AGENT=$(rpm -qa opflex-agent)
CURR_OPFLEX_AGENT_LIB=$(rpm -qa opflex-agent-lib)
CURR_OPFLEX_AGENT_RENDERER_OPENVSWITCH=$(rpm -qa opflex-agent-renderer-openvswitch)
CURR_NOIRO_OPENVSWITCH_LIB=$(rpm -qa noiro-openvswitch-lib)
CURR_NOIRO_OPENVSWITCH_OTHERLIB=$(rpm -qa noiro-openvswitch-otherlib)
CURR_PROMETHEUS_CPP_LIB=$(rpm -qa prometheus-cpp-lib)
CURR_LIBMODELGBP=$(rpm -qa libmodelgbp)
CURR_LIBOPFLEX=$(rpm -qa libopflex)
CURR_LIBUV=$(rpm -qa libuv)

NEW_OPFLEX_AGENT=$(ls opflex-agent*.rpm | grep -v 'lib\|renderer')
NEW_OPFLEX_AGENT_LIB=$(ls opflex-agent-lib*.rpm)
NEW_OPFLEX_AGENT_RENDERER_OPENVSWITCH=$(ls opflex-agent-renderer-openvswitch*.rpm)
NEW_NOIRO_OPENVSWITCH_LIB=$(ls noiro-openvswitch-lib*.rpm)
NEW_NOIRO_OPENVSWITCH_OTHERLIB=$(ls noiro-openvswitch-otherlib*.rpm)
NEW_PROMETHEUS_CPP_LIB=$(ls prometheus-cpp-lib*.rpm)
NEW_LIBMODELGBP=$(ls libmodelgbp*.rpm)
NEW_LIBOPFLEX=$(ls libopflex*.rpm)
NEW_LIBUV=$(ls libuv*.rpm)

echo "Replacing ${CURR_OPFLEX_AGENT} with ${NEW_OPFLEX_AGENT}"
echo "Replacing ${CURR_OPFLEX_AGENT_LIB} with ${NEW_OPFLEX_AGENT_LIB}"
echo "Replacing ${CURR_OPFLEX_AGENT_RENDERER_OPENVSWITCH} with ${NEW_OPFLEX_AGENT_RENDERER_OPENVSWITCH}"
echo "Replacing ${CURR_NOIRO_OPENVSWITCH_LIB} with ${NEW_NOIRO_OPENVSWITCH_LIB}"
echo "Replacing ${CURR_NOIRO_OPENVSWITCH_OTHERLIB} with ${NEW_NOIRO_OPENVSWITCH_OTHERLIB}"
echo "Replacing ${CURR_PROMETHEUS_CPP_LIB} with ${NEW_PROMETHEUS_CPP_LIB}"
echo "Replacing ${CURR_LIBMODELGBP} with ${NEW_LIBMODELGBP}"
echo "Replacing ${CURR_LIBOPFLEX} with ${NEW_LIBOPFLEX}"
echo "Replacing ${CURR_LIBUV} with ${NEW_LIBUV}"

if [ "${CHECK_ONLY}" != '' ]; then
   echo "Removing old packages...."
   rpm -e ${CURR_OPFLEX_AGENT_RENDERER_OPENVSWITCH}
   # Have to force this one, since opflex-agent and opflex-agent-lib are circular dependencies
   rpm -e --nodeps ${CURR_OPFLEX_AGENT}
   rpm -e ${CURR_OPFLEX_AGENT_LIB}
   rpm -e ${CURR_LIBMODELGBP}
   rpm -e ${CURR_LIBOPFLEX}
   rpm -e ${CURR_NOIRO_OPENVSWITCH_LIB}
   rpm -e ${CURR_NOIRO_OPENVSWITCH_OTHERLIB}
   rpm -e ${CURR_PROMETHEUS_CPP_LIB}
   # For now, don't remove, since the one installed is more recent
   if [ "${REPLACE_LIBUV}" -ne 0 ]; then
       rpm -e ${CURR_LIBUV}
   fi

   echo "Installing new packages...."
   # For now, don't install, since the one installed is more recent
   if [ "${REPLACE_LIBUV}" -ne 0 ]; then
       rpm -i ${NEW_LIBUV}
   fi
   rpm -i ${NEW_PROMETHEUS_CPP_LIB}
   rpm -i ${NEW_NOIRO_OPENVSWITCH_OTHERLIB}
   rpm -i ${NEW_NOIRO_OPENVSWITCH_LIB}
   rpm -i ${NEW_LIBOPFLEX}
   rpm -i ${NEW_LIBMODELGBP}
   # Have to force this one, since opflex-agent and opflex-agent-lib are circular dependencies
   rpm -i --nodeps ${NEW_OPFLEX_AGENT_LIB}
   rpm -i ${NEW_OPFLEX_AGENT}
   rpm -i ${NEW_OPFLEX_AGENT_RENDERER_OPENVSWITCH}
fi
