from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetPnl(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_pnl'
    expected_classes = ('GetPnlMixin',)
    method_name = 'get_pnl'
