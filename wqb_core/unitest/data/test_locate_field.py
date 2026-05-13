from wqb_core.unitest._helpers import ModuleContractTestCase


class TestLocateField(ModuleContractTestCase):
    module_name = 'wqb_core.data.locate_field'
    expected_classes = ('LocateFieldMixin',)
    method_name = 'locate_field'
