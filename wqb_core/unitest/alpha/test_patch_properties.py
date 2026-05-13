from wqb_core.unitest._helpers import ModuleContractTestCase


class TestPatchProperties(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.patch_properties'
    expected_classes = ('PatchPropertiesMixin',)
    method_name = 'patch_properties'
