from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetDatasets(ModuleContractTestCase):
    module_name = 'wqb_core.data.get_datasets'
    expected_classes = ('GetDatasetsMixin',)
    method_name = 'get_datasets'
