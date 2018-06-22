# Copyright 2017-present Open Networking Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import unittest
from mock import patch, Mock


import os, sys

test_path=os.path.abspath(os.path.dirname(os.path.realpath(__file__)))
service_dir=os.path.join(test_path, "../../../..")
xos_dir=os.path.join(test_path, "../../..")
if not os.path.exists(os.path.join(test_path, "new_base")):
    xos_dir=os.path.join(test_path, "../../../../../../orchestration/xos/xos")
    services_dir=os.path.join(xos_dir, "../../xos_services")

# While transitioning from static to dynamic load, the path to find neighboring xproto files has changed. So check
# both possible locations...
def get_models_fn(service_name, xproto_name):
    name = os.path.join(service_name, "xos", xproto_name)
    if os.path.exists(os.path.join(services_dir, name)):
        return name
    else:
        name = os.path.join(service_name, "xos", "synchronizer", "models", xproto_name)
        if os.path.exists(os.path.join(services_dir, name)):
            return name
    raise Exception("Unable to find service=%s xproto=%s" % (service_name, xproto_name))

class TestModelPolicyRCORDSubscriber(unittest.TestCase):
    def setUp(self):

        self.sys_path_save = sys.path
        sys.path.append(xos_dir)
        sys.path.append(os.path.join(xos_dir, 'synchronizers', 'new_base'))

        config = os.path.join(test_path, "../test_config.yaml")
        from xosconfig import Config
        Config.clear()
        Config.init(config, 'synchronizer-config-schema.yaml')

        from synchronizers.new_base.mock_modelaccessor_build import build_mock_modelaccessor
        build_mock_modelaccessor(xos_dir, services_dir, [
            get_models_fn("../profiles/rcord", "rcord.xproto"),
            get_models_fn("olt-service", "volt.xproto") # in test create we spy on VOLTServiceInstance
        ])

        import synchronizers.new_base.modelaccessor
        from model_policy_rcordsubscriber import RCORDSubscriberPolicy, model_accessor

        from mock_modelaccessor import MockObjectList

        # import all class names to globals
        for (k, v) in model_accessor.all_model_classes.items():
            globals()[k] = v

        # Some of the functions we call have side-effects. For example, creating a VSGServiceInstance may lead to creation of
        # tags. Ideally, this wouldn't happen, but it does. So make sure we reset the world.
        model_accessor.reset_all_object_stores()

        self.policy = RCORDSubscriberPolicy()
        self.si = Mock(name="myTestSubscriber")

    def tearDown(self):
        sys.path = self.sys_path_save

    def test_update_pre_provisione(self):
        si = self.si
        si.status = "pre-provisioned"
        self.policy.handle_create(si)

        with patch.object(VOLTServiceInstance, "save", autospec=True) as save_volt, \
             patch.object(ServiceInstanceLink, "save", autospec=True) as save_link:

            self.policy.handle_create(si)
            self.assertEqual(save_link.call_count, 0)
            self.assertEqual(save_volt.call_count, 0)

    def test_update_and_do_nothing(self):
        si = self.si
        si.is_new = False
        si.subscribed_links.all.return_value = ["already", "have", "a", "chain"]
        
        with patch.object(VOLTServiceInstance, "save", autospec=True) as save_volt, \
             patch.object(ServiceInstanceLink, "save", autospec=True) as save_link:

            self.policy.handle_create(si)
            self.assertEqual(save_link.call_count, 0)
            self.assertEqual(save_volt.call_count, 0)

    def test_create(self):
        volt = Mock()
        volt.get_service_instance_class_name.return_value = "VOLTServiceInstance"

        service_dependency = Mock()
        service_dependency.provider_service = volt

        si = self.si
        si.is_new = True
        si.subscribed_links.all.return_value = []
        si.owner.subscribed_dependencies.all.return_value = [service_dependency]

        with patch.object(VOLTServiceInstance, "save", autospec=True) as save_volt, \
             patch.object(ServiceInstanceLink, "save", autospec=True) as save_link:

            self.policy.handle_create(si)
            self.assertEqual(save_link.call_count, 1)
            self.assertEqual(save_volt.call_count, 1)


if __name__ == '__main__':
    unittest.main()
