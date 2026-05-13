from wqb_core.unitest._helpers import ModuleContractTestCase


class TestDeleteAuthentication(ModuleContractTestCase):
    module_name = 'wqb_core.user.delete_authentication'
    expected_classes = ('DeleteAuthenticationMixin',)
    method_name = 'delete_authentication'
