from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetTutorialPage(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_tutorial_page'
    expected_classes = ('GetTutorialPageMixin',)
    method_name = 'get_tutorial_page'
