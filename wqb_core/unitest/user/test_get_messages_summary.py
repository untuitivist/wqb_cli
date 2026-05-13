from wqb_core.unitest._helpers import ModuleContractTestCase


class TestGetMessagesSummary(ModuleContractTestCase):
    module_name = 'wqb_core.user.get_messages_summary'
    expected_classes = ('GetMessagesSummaryMixin',)
    method_name = 'get_messages_summary'
