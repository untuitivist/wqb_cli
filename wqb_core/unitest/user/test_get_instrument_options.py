from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetInstrumentOptions(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_instrument_options'
    expected_classes = ('GetInstrumentOptionsMixin',)
    method_name = 'get_instrument_options'
