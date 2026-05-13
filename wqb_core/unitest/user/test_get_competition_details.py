from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetCompetitionDetails(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_competition_details'
    expected_classes = ('GetCompetitionDetailsMixin',)
    method_name = 'get_competition_details'
