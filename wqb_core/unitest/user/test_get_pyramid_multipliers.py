from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetPyramidMultipliers(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_pyramid_multipliers'
    expected_classes = ('GetPyramidMultipliersMixin',)
    method_name = 'get_pyramid_multipliers'
