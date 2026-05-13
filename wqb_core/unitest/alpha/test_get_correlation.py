from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetCorrelation(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_correlation'
    expected_classes = ('GetCorrelationMixin',)
    method_name = 'get_correlation'
