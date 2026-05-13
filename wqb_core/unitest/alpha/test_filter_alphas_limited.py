from wqb_core.unitest._helpers import ModuleContractTestCase


class TestFilterAlphasLimited(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.filter_alphas_limited'
    expected_classes = ('FilterAlphasLimitedMixin',)
    method_name = 'filter_alphas_limited'
