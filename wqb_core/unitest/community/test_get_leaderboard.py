from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetLeaderboard(ModuleContractTestCase):
    module_name = 'wqb_core.community.get_leaderboard'
    expected_classes = ('GetLeaderboardMixin',)
    method_name = 'get_leaderboard'
