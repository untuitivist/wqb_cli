import unitest

from wqb_core.user.get_pyramid_alphas import GetPyramidAlphasMixin
from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetPyramidAlphas(unitest.TestCase):
    def test_quarter_date_range(self):
        start, end = GetPyramidAlphasMixin._quarter_date_range(2026, 2)
        self.assertEqual(start, '2026-04-01')
        self.assertEqual(end, '2026-06-30')


class TestGetPyramidAlphasLive(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_pyramid_alphas'
    expected_classes = ('GetPyramidAlphasMixin',)
    method_name = 'get_pyramid_alphas'


if __name__ == '__main__':
    unitest.main()
