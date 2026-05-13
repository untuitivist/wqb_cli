from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetTutorials(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_tutorials'
    expected_classes = ('GetTutorialsMixin',)
    method_name = 'get_tutorials'
