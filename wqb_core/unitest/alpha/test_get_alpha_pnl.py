from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetAlphaPnl(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_alpha_pnl'
    expected_classes = ('GetAlphaPnlMixin',)
    method_name = 'get_alpha_pnl'
