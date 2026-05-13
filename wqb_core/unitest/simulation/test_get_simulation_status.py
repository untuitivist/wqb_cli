from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetSimulationStatus(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.get_simulation_status'
    expected_classes = ('GetSimulationStatusMixin',)
    method_name = 'get_simulation_status'
