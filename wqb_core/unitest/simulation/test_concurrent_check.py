from wqb_core.unitest._helpers import ModuleContractTestCase


class TestConcurrentCheck(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.concurrent_check'
    expected_classes = ('ConcurrentCheckMixin',)
