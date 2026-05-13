from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetAlphaDetails(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_alpha_details'
    expected_classes = ('GetAlphaDetailsMixin',)
    method_name = 'get_alpha_details'
