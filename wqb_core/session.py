"""
功能概述
`wqb_core.session` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- 以本模块中定义的公开类、函数和常量为准。

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

from .alpha import (
    FilterAlphasLimitedMixin,
    FilterAlphasMixin,
    GetAlphaDetailsMixin,
    GetAlphaPnlMixin,
    GetAlphaRecordsetDataMixin,
    GetAlphaRecordsetsMixin,
    GetCorrelationMixin,
    GetCorrelationPowerpoolMixin,
    GetCorrelationProductMixin,
    GetCorrelationSelfMixin,
    GetPerformanceComparisonMixin,
    GetPnlMixin,
    GetSubmissionCheckMixin,
    GetYearlystatsMixin,
    LocateAlphaMixin,
    PerformanceComparisonMixin,
    PatchPropertiesMixin,
    SetAlphaPropertiesMixin,
)
from .community import GetEventsMixin, GetLeaderboardMixin
from .data import (
    GetDatafieldsMixin,
    GetDatasetsMixin,
    GetOperatorsMixin,
    GetPlatformSettingOptionsMixin,
    LocateDatasetMixin,
    LocateFieldMixin,
    RunSelectionMixin,
    SearchDatasetsLimitedMixin,
    SearchDatasetsMixin,
    SearchFieldsLimitedMixin,
    SearchFieldsMixin,
    SearchOperatorsMixin,
)
from .dataset import ExportCommunityStorageMixin, SearchCommunityStorageMixin
from .foundation.session_base import WQBSessionBase
from .simulation import (
    CheckMixin,
    ConcurrentCheckMixin,
    ConcurrentSimulateMixin,
    GetSimulationStatusMixin,
    RetryMixin,
    SimulateMixin,
    SubmitMixin,
    WaitForSimulationMixin,
)
from .user import (
    DeleteAuthenticationMixin,
    GetAuthenticationMixin,
    GetCompetitionAgreementMixin,
    GetCompetitionDetailsMixin,
    GetInstrumentOptionsMixin,
    GetMessagesMixin,
    GetMessagesSummaryMixin,
    GetPyramidAlphasMixin,
    GetPyramidMultipliersMixin,
    GetTutorialPageMixin,
    GetTutorialsMixin,
    GetUserActivitiesMixin,
    GetUserAlphasMixin,
    GetUserCompetitionsMixin,
    GetUserProfileMixin,
    HeadAuthenticationMixin,
    PostAuthenticationMixin,
)

__all__ = ['WQBSession']


class WQBSession(
    GetAuthenticationMixin,
    PostAuthenticationMixin,
    DeleteAuthenticationMixin,
    HeadAuthenticationMixin,
    GetUserProfileMixin,
    GetTutorialsMixin,
    GetTutorialPageMixin,
    GetMessagesMixin,
    GetMessagesSummaryMixin,
    GetUserActivitiesMixin,
    GetPyramidMultipliersMixin,
    GetPyramidAlphasMixin,
    GetUserCompetitionsMixin,
    GetCompetitionDetailsMixin,
    GetCompetitionAgreementMixin,
    GetInstrumentOptionsMixin,
    GetEventsMixin,
    GetLeaderboardMixin,
    ExportCommunityStorageMixin,
    SearchCommunityStorageMixin,
    GetOperatorsMixin,
    SearchOperatorsMixin,
    RunSelectionMixin,
    GetDatasetsMixin,
    GetDatafieldsMixin,
    GetPlatformSettingOptionsMixin,
    LocateDatasetMixin,
    SearchDatasetsLimitedMixin,
    SearchDatasetsMixin,
    LocateFieldMixin,
    SearchFieldsLimitedMixin,
    SearchFieldsMixin,
    GetAlphaDetailsMixin,
    LocateAlphaMixin,
    GetUserAlphasMixin,
    FilterAlphasLimitedMixin,
    FilterAlphasMixin,
    PatchPropertiesMixin,
    SetAlphaPropertiesMixin,
    GetAlphaRecordsetsMixin,
    GetAlphaRecordsetDataMixin,
    GetCorrelationProductMixin,
    GetCorrelationSelfMixin,
    GetCorrelationPowerpoolMixin,
    GetCorrelationMixin,
    GetAlphaPnlMixin,
    GetPnlMixin,
    GetYearlystatsMixin,
    GetPerformanceComparisonMixin,
    PerformanceComparisonMixin,
    GetSubmissionCheckMixin,
    RetryMixin,
    SimulateMixin,
    ConcurrentSimulateMixin,
    GetSimulationStatusMixin,
    WaitForSimulationMixin,
    CheckMixin,
    ConcurrentCheckMixin,
    SubmitMixin,
    WQBSessionBase,
):
    """
    A class that implements common APIs of WorldQuant BRAIN platform.
    """

    pass
