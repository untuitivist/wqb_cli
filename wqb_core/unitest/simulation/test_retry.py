from wqb_core.unitest._helpers import ModuleContractTestCase


class TestRetry(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.retry'
    expected_classes = ('RetryMixin',)
