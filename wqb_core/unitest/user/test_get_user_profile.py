from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetUserProfile(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_user_profile'
    expected_classes = ('GetUserProfileMixin',)
    method_name = 'get_user_profile'
