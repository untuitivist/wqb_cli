from wqb_core.unitest._helpers import ModuleContractTestCase


class TestCheck(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.check'
    expected_classes = ('CheckMixin',)
    method_name = 'check'
