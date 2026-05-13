from wqb_core.unitest._helpers import ModuleContractTestCase


class TestConcurrentSimulate(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.concurrent_simulate'
    expected_classes = ('ConcurrentSimulateMixin',)
