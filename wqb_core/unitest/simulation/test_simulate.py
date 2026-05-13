from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSimulate(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.simulate'
    expected_classes = ('SimulateMixin',)
    method_name = 'simulate'
