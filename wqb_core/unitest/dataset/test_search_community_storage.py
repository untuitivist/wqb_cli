from wqb_core.unitest._helpers import ModuleContractTestCase


class TestSearchCommunityStorage(ModuleContractTestCase):
    module_name = 'wqb_core.dataset.search_community_storage'
    expected_classes = ('SearchCommunityStorageMixin',)
    method_name = 'search_community_storage'
