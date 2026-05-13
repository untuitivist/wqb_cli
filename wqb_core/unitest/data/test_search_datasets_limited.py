from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSearchDatasetsLimited(ModuleContractTestCase):
    module_name = 'wqb_core.data.search_datasets_limited'
    expected_classes = ('SearchDatasetsLimitedMixin',)
    method_name = 'search_datasets_limited'
