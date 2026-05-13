from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetEvents(ModuleContractTestCase):
    module_name = 'wqb_core.community.get_events'
    expected_classes = ('GetEventsMixin',)
    method_name = 'get_events'
