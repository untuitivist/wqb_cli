from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSearchOperators(ModuleContractTestCase):
    module_name = 'wqb_core.data.search_operators'
    expected_classes = ('SearchOperatorsMixin',)
    method_name = 'search_operators'
