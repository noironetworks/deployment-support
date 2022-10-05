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


class PolicyObject(object):
    """Opflex Policy Object

    Opflex JSON policy objects take the form:
    {
        "subject": <object type>,
        "uri": <uri string>,
        "properties": [ <list of properties> ]
        "children": [ <list of child objects> ]]
        "parent_subject": <parent object type>
        "parent_uri": <uri of parent>
        "parent_relation": <same as subject above>
    }
    """

    def __init__(self, jsondict):
        if not jsondict.get('subject'):
            print("Warning: object with no subject")
            return None
         
        if not jsondict.get('uri'):
            print("Warning: object with no uri")
            return None

        self.uri = jsondict['uri']
        self.subject = jsondict['subject']
        self.properties = jsondict.get('properties', [])
        self.children = jsondict.get('children', [])
        if jsondict.get('parent_uri'):
            self.parent_uri = jsondict.get('parent_uri')
        if jsondict.get('parent_subject'):
            self.parent_subject = jsondict.get('parent_subject')
        if jsondict.get('parent_relation'):
            self.parent_relation = jsondict.get('parent_relation')
        # Keep the original dict so we can display it
        self.visited = False
        self.jsondict = jsondict

    def _get_property(self, property_name):
        for prop in self.properties:
            if prop.get('name') == property_name:
                return prop

    def do_print(self):
        print(json.dumps(self.jsondict, indent=4, sort_keys=True))



class PolicyConfigManager(object):
    """Policy configuration Manager

    This class provides a set of APIs to introspect policy data.
    """

    def __init__(self, policy_filename):
        self.filename = policy_filename
        self.objects_by_uri = {}
        self.objects_by_type = {}
        self.parsed_policy = []
        self._get_policy_json()
        self._json_to_objects()

    def _json_to_objects(self):
        for item in self.parsed_policy:
            obj = PolicyObject(item)
            self.objects_by_type.setdefault(obj.subject, []).append(obj)
            self.objects_by_uri[obj.uri] = obj

    def _get_policy_json(self):
        with open(self.filename, 'r') as fd:
            self.parsed_policy = json.load(fd)

    def list_l3_eps(self):
        """List all of the Layer 3 policy objects

        Find all of the objects of type EpdrLocalL3Ep
        """
        self.list_objects_by_type('EpdrLocalL3Ep')

    def list_l2_eps(self):
        """List all of the Layer 3 policy objects

        Find all of the objects of type EpdrLocalL2Ep
        """
        self.list_objects_by_type('EpdrLocalL2Ep')

    def list_objects_by_type(self, object_type):
        """List all of the policy objects that have the same subject"""
        for opflex_obj in self.objects_by_type.get(object_type, []):
            opflex_obj.do_print()

    def list_vms(self):
        """List all the VM policy objects

        Find all the objects of type GbpeVMEp
        """
        self.list_objects_by_type('GbpeVMEp')

    def find_related_objects(self, node):
        related_objects = node.children[:]
        for prop in node.properties:
            if (prop.get('name') == 'target' and
                    prop.get('data',{}).get('reference_uri')):
                uri = prop['data']['reference_uri']
                if not self.objects_by_uri.get(uri):
                    print('####### URI for %s, but not found in dump ######' % uri)
                elif not self.objects_by_uri[uri].visited:
                    related_objects.append(prop['data']['reference_uri'])
                    self.objects_by_uri[uri].visited = True
        for uri in related_objects:
            child_obj = self.objects_by_uri.get(uri)
            if child_obj:
                child_obj.do_print()
                self.find_related_objects(child_obj)
            else:
                print('####### URI for %s, but not found in dump ######' % uri)
        

    def get_policy_for_ep(self, endpoint):
        """Get all the policy for a given EP

        Start by finding the Endpoint in the L2 or L3
        EP subtrees:
        /EpdrL2Discovered/EpdrLocalL2Ep
        /EpdrL3Discovered/EpdrLocalL3Ep

        If an L3 EP is requested, there should also be an
        associated L2 EP. The search for policy continues from the
        L2 EP, as that object will have children URis.
        """
        def _find_matching_ep(endpoint, ep_type, eps):
            for ep in eps:
                prop = ep._get_property(ep_type)
                if prop and endpoint in prop.get('data'):
                    return ep
            return None
     
        # Devine the EP type, if possible
        l2_ep_obj = None
        l3_ep_obj = None
        if netaddr.valid_ipv4(endpoint) or netaddr.valid_ipv6(endpoint):
            #ep_obj = netaddr.IPAddress(endpoint)
            eps = self.objects_by_type.get('EpdrLocalL3Ep')
            l3_ep_obj = _find_matching_ep(endpoint, 'ip', eps)
            if l3_ep_obj:
                l3_ep_obj.do_print()
            if not l3_ep_obj or not l3_ep_obj._get_property('mac'):
                return
            endpoint = l3_ep_obj._get_property('mac')['data']

        if netaddr.valid_mac(endpoint):
            eps = self.objects_by_type.get('EpdrLocalL2Ep')
            l2_ep_obj = _find_matching_ep(endpoint, 'mac', eps)
            if l2_ep_obj:
                l2_ep_obj.do_print()
            if not l2_ep_obj or not l2_ep_obj.children:
                return
        # Now do depth-first search for each child
        self.find_related_objects(l2_ep_obj)

    def find_unresolved_policy(self):
        """Find all unresolved policy

        Find all the MOs that have a "target" element in their
        "properties' section, then verify that the target MO also
        exists in the policy.
        """
        for opflex_obj in list(self.objects_by_uri.values()):
            target = opflex_obj._get_property('target')
            if target:
                target_uri = target['data']['reference_uri']
                if not self.objects_by_uri.get(target_uri):
                    print('####### URI for %s, but not found in dump ######' % target_uri)


###################################################################
# These currently aren't used -- we'll probably just use the dicts
class PropertiesObject(object):
    """Opflex Property Object

    Opflex property objects are elements in a list of
    propertiy objects kept by the polciy object. Items in
    the list take on the form of:
    {
        "name": <string for the name>,
        "data": <scalar or dict>
    }
    """

    def __init__(self, jsondict):
        if jsondict.get('name'):
            self.name = jsondict['name']

        if jsondict.get('data'):
            if self.name == 'target':
                if not isinstance(jsondict['data'], dict):
                    print("Data is target, but not a dict")
                    return None
            self.data = jsondict['data']


class DataObject(object):
    """Opflex Property Data Object

    Opflex property data can be either scalar elements, or
    if the property name was "target", dictionaries with the form:
    {
        "subject": <type of object referenced>,
        "reference_uri": <URI of the referenced object>
    }
    """

    def __init__(self, jsondict):
        if not jsondict.get('subject'):
            print("No subject in Data")
            return None
        if jsondict.get('reference_uri'):
            print("No reference_uri in Data")
            return None
        self.subject = jsondict['subject']
        self.reference_uri = jsondict['reference_uri']

