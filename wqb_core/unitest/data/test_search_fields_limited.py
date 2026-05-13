from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSearchFieldsLimited(ModuleContractTestCase):
    module_name = 'wqb_core.data.search_fields_limited'
    expected_classes = ('SearchFieldsLimitedMixin',)
    method_name = 'search_fields_limited'
