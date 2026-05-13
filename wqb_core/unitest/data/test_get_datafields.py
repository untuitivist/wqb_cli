from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetDatafields(ModuleContractTestCase):
    module_name = 'wqb_core.data.get_datafields'
    expected_classes = ('GetDatafieldsMixin',)
    method_name = 'get_datafields'
