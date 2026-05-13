from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSubmit(ModuleContractTestCase):
    module_name = 'wqb_core.simulation.submit'
    expected_classes = ('SubmitMixin',)
    method_name = 'submit'
