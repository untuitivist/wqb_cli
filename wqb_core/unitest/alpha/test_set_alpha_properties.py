from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSetAlphaProperties(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.set_alpha_properties'
    expected_classes = ('SetAlphaPropertiesMixin',)
    method_name = 'set_alpha_properties'
