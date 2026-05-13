from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetOperators(ModuleContractTestCase):
    module_name = 'wqb_core.data.get_operators'
    expected_classes = ('GetOperatorsMixin',)
    method_name = 'get_operators'
