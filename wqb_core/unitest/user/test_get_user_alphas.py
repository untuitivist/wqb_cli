from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetUserAlphas(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_user_alphas'
    expected_classes = ('GetUserAlphasMixin',)
    method_name = 'get_user_alphas'
