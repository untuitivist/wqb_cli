from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetPlatformSettingOptions(ModuleContractTestCase):
    module_name = 'wqb_core.data.get_platform_setting_options'
    expected_classes = ('GetPlatformSettingOptionsMixin',)
    method_name = 'get_platform_setting_options'
