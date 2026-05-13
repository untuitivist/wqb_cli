from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetCompetitionAgreement(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_competition_agreement'
    expected_classes = ('GetCompetitionAgreementMixin',)
    method_name = 'get_competition_agreement'
