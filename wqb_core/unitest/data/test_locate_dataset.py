from wqb_core.unitest._helpers import ModuleContractTestCase


class TestLocateDataset(ModuleContractTestCase):
    module_name = 'wqb_core.data.locate_dataset'
    expected_classes = ('LocateDatasetMixin',)
    method_name = 'locate_dataset'
