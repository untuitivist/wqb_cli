from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetUserCompetitions(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_user_competitions'
    expected_classes = ('GetUserCompetitionsMixin',)
    method_name = 'get_user_competitions'
