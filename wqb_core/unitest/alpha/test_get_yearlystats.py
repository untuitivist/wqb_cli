from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetYearlystats(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_yearlystats'
    expected_classes = ('GetYearlystatsMixin',)
    method_name = 'get_yearlystats'
