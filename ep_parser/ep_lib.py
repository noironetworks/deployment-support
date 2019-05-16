# Copyright (c) 2019 Cisco Systems
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import json
import netaddr

class EPManager(object):
    """Endpont(ep) Manager

    This class provides a set of APIs to introspect policy data.
    """

    def __init__(self, ep_filename):
        self.filename = ep_filename
        self.parsed_json = {}
        self.my_objects = {}
        self._get_ep_json()
        self._json_to_objects()

    def _json_to_objects(self):
	self.my_objects["uuid"] = self.parsed_json["uuid"]
        if self.parsed_json["neutron-metadata-optimization"] == True:
            self.my_objects["metadata_opt"] = True
        self.my_objects["os_domain"] = self.parsed_json["dhcp4"]["domain"]
        self.my_objects["static_routes"] = self.parsed_json["dhcp4"]["static-routes"]
        self.my_objects["ip_addr"] = self.parsed_json["dhcp4"]["ip"]
        self.my_objects["gateway"] = self.parsed_json["dhcp4"]["routers"]
        self.my_objects["access_interface"] = self.parsed_json["access-interface"]
        self.my_objects["uplink_interface"] = self.parsed_json["access-uplink-interface"]
        self.my_objects["mac_addr"] = self.parsed_json["mac"]
        self.my_objects["vrf"] = self.parsed_json["domain-name"]
        self.my_objects["epg"] = self.parsed_json["endpoint-group-name"]
        self.my_objects["tenant"] = self.parsed_json["policy-space-name"]
        self.my_objects["net_uuid"] = self.parsed_json["neutron-network"]
        self.my_objects["sec_groups"] = self.parsed_json["security-group"]
        self.my_objects["attributes"] = self.parsed_json["attributes"]

    def _get_ep_json(self):
        with open(self.filename, 'r') as fd:
            self.parsed_json = json.load(fd)

    def ep_dump(self):
            print "uuid is " + self.my_objects["uuid"].split("|")[0]
            print "metadata_opt is " + str(self.my_objects["metadata_opt"])
            print "domain is " + self.my_objects["os_domain"]
            print "IP address is " + self.my_objects["ip_addr"]
            print "MAC address is " + self.my_objects["mac_addr"]
            print "IP gateway is " + self.my_objects["gateway"][0]
            print "routes are " + str(self.my_objects["static_routes"])
            print "access interface is " + self.my_objects["access_interface"]
            print "uplink interface is " + self.my_objects["uplink_interface"]
            print "VRF is " + self.my_objects["vrf"]
            print "EPG is " + self.my_objects["epg"].split("|")[1]
            print "Tenant is " + self.my_objects["tenant"]
            print "Network is " + self.my_objects["net_uuid"]
            print "Security Groups are" + str(self.my_objects["sec_groups"])
            print "Attributes are" + str(self.my_objects["attributes"])

    def get_param(self,param):
            print "parameter is " + str(self.my_objects[param])
