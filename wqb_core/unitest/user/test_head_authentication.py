from wqb_core.unitest._helpers import ModuleContractTestCase


class TestHeadAuthentication(ModuleContractTestCase):
    module_name = 'wqb_core.user.head_authentication'
    expected_classes = ('HeadAuthenticationMixin',)
    method_name = 'head_authentication'
