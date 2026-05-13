from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSearchFields(ModuleContractTestCase):
    module_name = 'wqb_core.data.search_fields'
    expected_classes = ('SearchFieldsMixin',)
    method_name = 'search_fields'
