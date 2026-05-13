from wqb_core.unitest._helpers import ModuleContractTestCase


class TestExportCommunityStorage(ModuleContractTestCase):
    module_name = 'wqb_core.dataset.export_community_storage'
    expected_classes = ('ExportCommunityStorageMixin',)
    method_name = 'export_community_storage'

