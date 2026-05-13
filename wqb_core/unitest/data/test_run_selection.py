from wqb_core.unitest._helpers import ModuleContractTestCase


class TestRunSelection(ModuleContractTestCase):
    module_name = 'wqb_core.data.run_selection'
    expected_classes = ('RunSelectionMixin',)
    method_name = 'run_selection'
