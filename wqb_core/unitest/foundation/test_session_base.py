from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSessionBase(ModuleContractTestCase):
    module_name = 'wqb_core.foundation.session_base'
    expected_classes = ('WQBSessionBase',)
