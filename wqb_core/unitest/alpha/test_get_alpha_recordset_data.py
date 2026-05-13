from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetAlphaRecordsetData(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_alpha_recordset_data'
    expected_classes = ('GetAlphaRecordsetDataMixin',)
    method_name = 'get_alpha_recordset_data'
