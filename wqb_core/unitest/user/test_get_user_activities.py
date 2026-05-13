from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetUserActivities(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_user_activities'
    expected_classes = ('GetUserActivitiesMixin',)
    method_name = 'get_user_activities'
