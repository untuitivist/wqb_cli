"""
功能概述
`wqb_core.foundation.defines` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- 以本模块中定义的公开类、函数和常量为准。

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

from typing import Any

__all__ = [
    '__version__',
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'HEAD',
    'OPTIONS',
    'LOCATION',
    'RETRY_AFTER',
    'EQUITY',
    'Alpha',
    'MultiAlpha',
    'Region',
    'Delay',
    'Universe',
    'InstrumentType',
    'DataCategory',
    'FieldType',
    'DatasetsOrder',
    'FieldsOrder',
    'Status',
    'AlphaType',
    'AlphaCategory',
    'Language',
    'Color',
    'Neutralization',
    'UnitHandling',
    'NanHandling',
    'Pasteurization',
    'AlphasOrder',
    'Null',
    'NULL',
]

__version__ = '0.2.5'

GET = 'GET'
POST = 'POST'
PUT = 'PUT'
PATCH = 'PATCH'
DELETE = 'DELETE'
HEAD = 'HEAD'
OPTIONS = 'OPTIONS'

LOCATION = 'Location'
RETRY_AFTER = 'Retry-After'

EQUITY = 'EQUITY'

Alpha = Any
MultiAlpha = Any
Region = Any
Delay = Any
Universe = Any
InstrumentType = Any
DataCategory = Any
FieldType = Any
DatasetsOrder = Any
FieldsOrder = Any
Status = Any
AlphaType = Any
AlphaCategory = Any
Language = Any
Color = Any
Neutralization = Any
UnitHandling = Any
NanHandling = Any
Pasteurization = Any
AlphasOrder = Any


class Null:
    pass


NULL = Null()

# Alpha lifecycle status values commonly accepted by the platform filter APIs.
# Keep this note in sync with filter_alphas/filter_alphas_limited docstrings.
# Confirmed common values:
# - ACTIVE
# - UNSUBMITTED
# - DECOMMISSIONED
