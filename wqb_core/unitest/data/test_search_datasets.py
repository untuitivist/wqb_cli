from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSearchDatasets(ModuleContractTestCase):
    module_name = 'wqb_core.data.search_datasets'
    expected_classes = ('SearchDatasetsMixin',)
    method_name = 'search_datasets'
