from wqb_core.unitest._helpers import ModuleContractTestCase


class TestFilterAlphas(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.filter_alphas'
    expected_classes = ('FilterAlphasMixin',)
    method_name = 'filter_alphas'
