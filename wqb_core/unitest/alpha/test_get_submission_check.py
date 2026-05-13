from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetSubmissionCheck(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_submission_check'
    expected_classes = ('GetSubmissionCheckMixin',)
    method_name = 'get_submission_check'
