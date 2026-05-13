from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetCorrelationSelf(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_correlation_self'
    expected_classes = ('GetCorrelationSelfMixin',)
    method_name = 'get_correlation_self'
