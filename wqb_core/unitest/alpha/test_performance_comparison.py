from wqb_core.unitest._helpers import ModuleContractTestCase


class TestPerformanceComparison(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.performance_comparison'
    expected_classes = ('PerformanceComparisonMixin',)
    method_name = 'performance_comparison'
