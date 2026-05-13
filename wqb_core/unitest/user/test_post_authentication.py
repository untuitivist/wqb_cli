from wqb_core.unitest._helpers import ModuleContractTestCase


class TestPostAuthentication(ModuleContractTestCase):
    module_name = 'wqb_core.user.post_authentication'
    expected_classes = ('PostAuthenticationMixin',)
    method_name = 'post_authentication'
