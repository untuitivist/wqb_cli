from wqb_core.unitest._helpers import ModuleContractTestCase


class TestLocateAlpha(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.locate_alpha'
    expected_classes = ('LocateAlphaMixin',)
    method_name = 'locate_alpha'
