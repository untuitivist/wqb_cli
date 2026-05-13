from wqb_core.unitest._helpers import ModuleContractTestCase


class TestAutoAuthSession(ModuleContractTestCase):
    module_name = 'wqb_core.foundation.auto_auth_session'
    expected_classes = ('AutoAuthSession',)
