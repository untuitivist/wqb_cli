from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetAlphaRecordsets(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_alpha_recordsets'
    expected_classes = ('GetAlphaRecordsetsMixin',)
    method_name = 'get_alpha_recordsets'
