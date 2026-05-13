from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetCorrelationPowerpool(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_correlation_powerpool'
    expected_classes = ('GetCorrelationPowerpoolMixin',)
    method_name = 'get_correlation_powerpool'
