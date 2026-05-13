from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetAuthentication(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_authentication'
    expected_classes = ('GetAuthenticationMixin',)
    method_name = 'get_authentication'
