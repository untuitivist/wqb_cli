from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetMessages(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_messages'
    expected_classes = ('GetMessagesMixin',)
    method_name = 'get_messages'
