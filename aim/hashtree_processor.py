import argparse
import json
import sys
import traceback

from oslo_log import log as logging

from apicapi import apic_client

from aim import aim_manager
from aim.agent.aid.universes.aci import converter
from aim.api import resource as aim_resource
from aim.api import status as aim_status
from aim.common.hashtree import structured_tree
from aim.common import utils
from aim import config as aim_cfg
from aim import context
from aim.db import api
from aim import tree_manager



CREATE = 'create'
DELETE = 'delete'

LOG = logging.getLogger(__name__)


class HashtreeProcessor(object):

    def __init__(self, filename, annotation_key=None):
        self.filename = filename

        aim_cfg.init(["--config-file", "/etc/aim/aim.conf"])
        self.aim_ctx = context.AimContext(store=api.get_store())
        self.manager = aim_manager.AimManager()
        self.annotation_key = annotation_key
        self.conf_manager = aim_cfg.ConfigManager(self.aim_ctx, 'dummy_host')
        self.object_backlog = []

    @staticmethod
    def establish_aci_session(apic_config):
        return apic_client.RestClient(
            logging, '',
            apic_config.get_option('apic_hosts', group='apic'),
            apic_config.get_option('apic_username', group='apic'),
            apic_config.get_option('apic_password', group='apic'),
            apic_config.get_option('apic_use_ssl', group='apic'),
            scope_names=False, scope_infra=False, renew_names=False,
            verify=apic_config.get_option('verify_ssl_certificate',
                                          group='apic'),
            request_timeout=apic_config.get_option('apic_request_timeout',
                                                   group='apic'),
            cert_name=apic_config.get_option('certificate_name',
                                             group='apic'),
            private_key_file=apic_config.get_option('private_key_file',
                                                    group='apic'),
            sign_algo=apic_config.get_option(
                'signature_verification_algorithm', group='apic'),
            sign_hash=apic_config.get_option(
                'signature_hash_type', group='apic'))

    def get_hashtree_data(self):
        fd = open(self.filename, 'r')
        # get rid of first line, which is a header
        tenant_line = fd.readline()
        self.tenant = tenant_line.strip().split()[-1][3:-1]
        alldata = fd.read()
        self.json_data = json.loads(alldata)
        self.hashtree = structured_tree.StructuredHashTree.from_string(
            alldata, root_key=self.tenant)
        self._converter = converter.AciToAimModelConverter()
        self._converter_aim_to_aci = converter.AimToAciModelConverter()

    def get_differences(self):
        self.differences = {CREATE: [], DELETE: []}
        difference = self.hashtree.diff(
            structured_tree.StructuredHashTree())
        self.differences[CREATE].extend(difference['add'])
        self.differences[DELETE].extend(difference['remove'])

    def get_relevant_state_for_read(self):
        return [{'tn-' + self.tenant: self.hashtree}]

    def _fill_node(self, current_key, desired_state):
        root = tree_manager.AimHashTreeMaker._extract_root_rn(current_key)
        for state in desired_state:
            try:
                current_node = state[root].find(current_key)
            except (IndexError, KeyError):
                continue
            if current_node and not current_node.dummy:
                return current_node.metadata.to_dict()

    def _fill_related_nodes(self, resource_keys, current_key, desired_state):
        root = tree_manager.AimHashTreeMaker._extract_root_rn(current_key)
        for state in desired_state:
            try:
                current_node = state[root].find(current_key)
                if not current_node:
                    continue
            except (IndexError, KeyError):
                continue
            for child in current_node.get_children():
                if child.metadata.get('related') and not child.dummy:
                    resource_keys.append(child.key)

    def _fill_parent_node(self, resource_keys, current_key, desired_state):
        root = tree_manager.AimHashTreeMaker._extract_root_rn(current_key)
        for state in desired_state:
            try:
                parent_node = state[root].find(current_key[:-1])
                if not parent_node:
                    continue
            except (IndexError, KeyError):
                continue
            if not parent_node.dummy:
                resource_keys.append(parent_node.key)

    def get_resources(self, resource_keys, desired_state=None):
        #if resource_keys:
        #    LOG.debug("Requesting resource keys in %s: %s",
        #              self.name, resource_keys)
        # NOTE(ivar): state is a copy at the current iteration that was created
        # through the observe() method.
        desired_state = desired_state or self.get_relevant_state_for_read()
        result = []
        id_set = set()
        monitored_set = set()
        for key in resource_keys:
            if key not in id_set:
                attr = self._fill_node(key, desired_state)
                if not attr:
                    continue
                monitored = attr.pop('monitored', None)
                related = attr.pop('related', False)
                attr = attr.get('attributes', {})
                aci_object = self._keys_to_bare_aci_objects([key])[0]
                list(aci_object.values())[0]['attributes'].update(attr)
                dn = list(aci_object.values())[0]['attributes']['dn']
                # Capture related objects
                if desired_state:
                    self._fill_related_nodes(resource_keys, key,
                                             desired_state)
                    if related:
                        self._fill_parent_node(resource_keys, key,
                                               desired_state)
                result.append(aci_object)
                if monitored:
                    if related:
                        try:
                            monitored_set.add(
                                converter.AciToAimModelConverter().convert(
                                    [aci_object])[0].dn)
                        except IndexError:
                            pass
                    else:
                        monitored_set.add(dn)
                id_set.add(key)
        if resource_keys:
            result = self._convert_get_resources_result(result, monitored_set)
            #LOG.debug("Result for keys %s\n in %s:\n %s" %
            #          (resource_keys, self.name, result))
        return result

    def _convert_get_resources_result(self, result, monitored_set):
        result = converter.AciToAimModelConverter().convert(result)
        for item in result:
            if item.dn in monitored_set:
                item.monitored = True
        return result

    def get_resources_for_delete(self, resource_keys):
        des_mon = structured_tree.StructuredHashTree()
        #des_mon = self.multiverse[base.MONITOR_UNIVERSE]['desired'].state

        def action(result, aci_object, node):
            if not node or node.dummy:
                result.append(aci_object)
        return self._converter.convert(
            self._get_resources_for_delete(resource_keys, des_mon, action))

    def _get_resources_for_delete(self, resource_keys, mon_uni, action):
        #if resource_keys:
        #    LOG.debug("Requesting resource keys in %s for "
        #              "delete: %s" % (self.name, resource_keys))
        result = []
        for key in resource_keys:
            aci_object = self._keys_to_bare_aci_objects([key])[0]
            # If this object exists in the monitored tree it's transitioning
            root = tree_manager.AimHashTreeMaker._extract_root_rn(key)
            try:
                node = mon_uni[root].find(key)
            except KeyError:
                node = None
            action(result, aci_object, node)
        if resource_keys:
            LOG.debug("Result for keys %s\n in ACI Universe for delete:\n %s" %
                      (resource_keys, result))
        return result

    def _split_key(self, key):
        return [k.split('|', 2) for k in key]

    def _keys_to_bare_aci_objects(self, keys):
        # Transforms hashtree keys into minimal ACI objects
        aci_objects = []
        for key in keys:
            fault_code = None
            key_parts = self._split_key(key)
            mo_type = key_parts[-1][0]
            aci_object = {mo_type: {'attributes': {}}}
            if mo_type == 'faultInst':
                fault_code = key_parts[-1][1]
                key_parts = key_parts[:-1]
            dn = apic_client.DNManager().build(key_parts)
            if fault_code:
                dn += '/fault-%s' % fault_code
                aci_object[mo_type]['attributes']['code'] = fault_code
            aci_object[mo_type]['attributes']['dn'] = dn
            aci_objects.append(aci_object)
        return aci_objects

    def _retrieve_tenant_rn(self, data):
        if isinstance(data, dict):
            data = self._aim_converter.convert([data])
            data = data[0] if data else None
        if isinstance(data, aim_resource.AciResourceBase):
            return tree_manager.AimHashTreeMaker().get_root_key(data)

    def aci_push_resources(self, context, resources):
        # Organize by tenant, and push into APIC
        by_tenant = {}
        for method, objects in resources.items():
            for data in objects:
                tenant_name = self._retrieve_tenant_rn(data)
                if tenant_name:
                    by_tenant.setdefault(tenant_name, {}).setdefault(
                        method, []).append(data)

        #self._filter_resources(context, by_tenant)
        for tenant, conf in by_tenant.items():
            self.push_aim_resources(conf)
        self.push_aci_mos()

    def push_aim_resources(self, resources):
        backlog = []
        if any(resources.values()):
            backlog.append(resources)
        self.object_backlog = backlog

    def push_aci_mos(self):
        dn_mgr = apic_client.DNManager()
        decompose = dn_mgr.aci_decompose_dn_guess
        for request in self.object_backlog:
            for method, aim_objects in request.items():
                # Method will be either "create" or "delete"
                # sort the aim_objects based on DN first for DELETE method
                sorted_aim_objs = aim_objects
                if method == DELETE:
                    sorted_aim_objs = sorted(
                        aim_objects,
                        key=lambda x: list(
                            x.values())[0]['attributes']['dn'])
                potential_parent_dn = ' '
                for aim_object in sorted_aim_objs:
                    # get MO from ACI client, identify it via its DN parts
                    # and push the new body
                    if method == DELETE:
                        # If a parent is also being deleted then we don't
                        # have to send those children requests to APIC
                        dn = list(aim_object.values())[
                            0]['attributes']['dn']
                        res_type = list(aim_object.keys())[0]
                        decomposed = decompose(dn, res_type)
                        parent_dn = dn_mgr.build(decomposed[1][:-1])
                        if parent_dn.startswith(potential_parent_dn):
                            continue
                        else:
                            potential_parent_dn = dn
                        to_push = [copy.deepcopy(aim_object)]
                    else:
                        if getattr(aim_object, 'monitored', False):
                            # When pushing to APIC, treat monitored
                            # objects as pre-existing
                            aim_object.monitored = False
                            #aim_object.pre_existing = True
                        to_push = self._converter_aim_to_aci.convert(
                            [aim_object])
                    LOG.debug('%s AIM object %s in APIC' % (
                              method, repr(aim_object)))
                    try:
                        if method == CREATE:
                            # Set ownership before pushing the request
                            to_push = self.set_ownership_key(
                                to_push)
                            LOG.debug("POSTING into APIC: %s" % to_push)
                            self._post_with_transaction(to_push)
                            #self.creation_succeeded(aim_object)
                        else:
                            to_delete, to_update = (
                                self.set_ownership_change(
                                    to_push))
                            LOG.debug("DELETING from APIC: %s" % to_delete)
                            for obj in to_delete:
                                attr = list(obj.values())[0]['attributes']
                                self.aci_session.DELETE(
                                    '/mo/%s.json' % attr.pop('dn'))
                            LOG.debug("UPDATING in APIC: %s" % to_update)
                            # Update object ownership
                            self._post_with_transaction(to_update,
                                                        modified=True)
                            #if to_update:
                            #    self.creation_succeeded(aim_object)
                    except Exception as e:
                        LOG.debug(traceback.format_exc())
                        LOG.error("An error has occurred during %s for "
                                  "object %s: %s" % (method, aim_object,
                                                     str(e)))
                        #if method == CREATE:
                        #    err_type = (
                        #        self.error_handler.analyze_exception(e))
                        #    # REVISIT(ivar): for now, treat UNKNOWN errors
                        #    # the same way as OPERATION_TRANSIENT.
                        #    # Investigate a way to understand when such
                        #    # errors might require agent restart.
                        #    self.creation_failed(aim_object, str(e),
                        #                         err_type)

    def set_ownership_key(self, to_push):
        result = to_push
        for obj in to_push:
            list(obj.values())[0]['attributes']['annotation'] = (
                self.annotation_key)
        return result

    def set_ownership_change(self, to_push):
        to_update = []
        return to_push, to_update

    def _post_with_transaction(self, to_push, modified=False):
        if not to_push:
            return
        dn_mgr = apic_client.DNManager()
        decompose = dn_mgr.aci_decompose_dn_guess
        with self.aci_session.transaction(
                top_send=True) as trs:
            for obj in to_push:
                attr = list(obj.values())[0]['attributes']
                if modified:
                    attr['status'] = converter.MODIFIED_STATUS
                mo, parents_rns = decompose(
                    attr.pop('dn'), list(obj.keys())[0])
                rns = dn_mgr.filter_rns(parents_rns)
                getattr(self.aci_session, mo).create(*rns, transaction=trs,
                                                     **attr)

    def aim_push_resources(self, context, resources, monitored=False):
        for method in resources:
            if method == DELETE:
                # Use ACI items directly
                items = resources[method]
            else:
                # Convert everything before creating
                items = self._converter.convert(resources[method])
            for resource in items:
                # Items are in the other universe's format unless deletion
                try:
                    self._push_resource(context, resource, method, monitored)
                except aim_exc.InvalidMonitoredStateUpdate as e:
                    msg = ("Failed to %s object %s in AIM: %s." %
                           (method, resource, str(e)))
                    LOG.warn(msg)
                except Exception as e:
                    LOG.error("Failed to %s object %s in AIM: %s." %
                              (method, resource, str(e)))
                    LOG.debug(traceback.format_exc())

    def _push_resource(self, context, resource, method, monitored):
        if isinstance(resource, aim_status.AciFault):
            # Retrieve fault's parent and set/unset the fault
            if method == CREATE:
                parents = utils.retrieve_fault_parent(
                    resource.external_identifier, converter.resource_map)
                for parent in parents:
                    if self.manager.get_status(context, parent):
                        LOG.debug("%s for object %s: %s",
                                  self.manager.set_fault.__name__, parent,
                                  resource)
                        self.manager.set_fault(context, resource=parent,
                                               fault=resource)
                        break
            else:
                self.manager.delete(context, resource)
        else:
            LOG.debug("%s object in AIM %s" %
                      (method, resource))
            if method == CREATE:
                if monitored:
                    # We need two more conversions to screen out
                    # unmanaged items
                    resource.monitored = monitored
                    resource = self._converter_aim_to_aci.convert(
                        [resource])
                    resource = self._converter.convert(resource)[0]
                    resource.monitored = monitored
                with context.store.begin(subtransactions=True):
                    if isinstance(resource, aim_resource.AciRoot):
                        # Roots should not be created by the
                        # AIM monitored universe.
                        # NOTE(ivar): there are contention cases
                        # where a user might delete a Root object
                        # right before the AIM Monitored Universe
                        # pushes an update on it. If we run a
                        # simple "create overwrite" this would
                        # re-create the object and AID would keep
                        # monitoring said root. by only updating
                        # roots and never creating them, we give
                        # full control over which trees to monitor
                        # to the user.
                        ext = context.store.extract_attributes
                        obj = self.manager.update(
                            context, resource, fix_ownership=monitored,
                            **ext(resource, "other"))
                        #if obj:
                        #    # Declare victory for the update
                        #    self.creation_succeeded(resource)
                    else:
                        self.manager.create(
                            context, resource, overwrite=True,
                            fix_ownership=monitored)
                        # Declare victory for the created object
                        #self.creation_succeeded(resource)
            else:
                if isinstance(resource, aim_resource.AciRoot) and monitored:
                    # Monitored Universe doesn't delete Tenant
                    # Resources
                    #LOG.info('%s skipping delete for object %s' %
                    #         (self.name, resource))
                    return
                if monitored:
                    # Only delete a resource if monitored
                    with context.store.begin(subtransactions=True):
                        existing = self.manager.get(context, resource)
                        if existing and existing.monitored:
                            self.manager.delete(context, resource)
                else:
                    self.manager.delete(context, resource)

    def create_aim_resources(self):
        result = {
            CREATE: self._converter_aim_to_aci.convert(self.get_resources(self.differences[CREATE])),
            DELETE: self._converter_aim_to_aci.convert(self.get_resources_for_delete(self.differences[DELETE]))
        }
        self.aim_push_resources(self.aim_ctx, result)

    def create_aci_resources(self):
        result = {
            CREATE: self.get_resources(self.differences[CREATE]),
            DELETE: self.get_resources_for_delete(self.differences[DELETE])
        }
        self.aci_session = self.establish_aci_session(self.conf_manager)
        self.aci_push_resources(self.aim_ctx, result)

def main():
    parser = argparse.ArgumentParser(description='Hashtree dump proecessor')

    parser.add_argument("-f", "--input_file", help="AIM Hashtree dump file",
                      dest="input_file")
    parser.add_argument("-d", "--db", help="Create AIM DB resources",
                      dest='do_aim_resources', action='store_true')
    parser.add_argument("-a", "--apic", help="Create AIM APIC resources",
                      dest='do_apic_resources', action='store_true')
    options = parser.parse_args()

    processor = HashtreeProcessor(options.input_file)
    print("Importing Hashtree")
    processor.get_hashtree_data()
    processor.get_differences()
    if options.do_aim_resources:
        processor.create_aim_resources()
    if options.do_apic_resources:
        processor.create_aci_resources()

if __name__ == "__main__":
    sys.exit(main())
