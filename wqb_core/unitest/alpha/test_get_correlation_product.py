from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetCorrelationProduct(ModuleContractTestCase):
    module_name = 'wqb_core.alpha.get_correlation_product'
    expected_classes = ('GetCorrelationProductMixin',)
    method_name = 'get_correlation_product'
