from wqb_core.unitest._helpers import ModuleContractTestCase


class TestWaitForSimulation(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.wait_for_simulation'
    expected_classes = ('WaitForSimulationMixin',)
    method_name = 'wait_for_simulation'
