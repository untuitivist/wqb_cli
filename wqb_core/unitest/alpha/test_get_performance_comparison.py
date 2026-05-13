from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetPerformanceComparison(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_performance_comparison'
    expected_classes = ('GetPerformanceComparisonMixin',)
    method_name = 'get_performance_comparison'
