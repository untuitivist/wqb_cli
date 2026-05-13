"""
功能概述
`wqb_core.__init__` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- 以本模块中定义的公开类、函数和常量为准。

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

from . import datetime_range
from . import filter_range
from . import foundation
from . import session
from .foundation import async_utils
from .foundation import auto_auth_session
from .foundation import credentials
from .foundation import defines
from .foundation import helpers
from .foundation import urls

__version__ = defines.__version__

__all__ = (
    defines.__all__
    + auto_auth_session.__all__
    + credentials.__all__
    + datetime_range.__all__
    + filter_range.__all__
    + helpers.__all__
    + async_utils.__all__
    + session.__all__
    + urls.__all__
)


from .foundation.defines import *  # noqa: F401,F403
from .foundation.auto_auth_session import *  # noqa: F401,F403
from .foundation.credentials import *  # noqa: F401,F403
from .datetime_range import *  # noqa: F401,F403
from .filter_range import *  # noqa: F401,F403
from .foundation.helpers import *  # noqa: F401,F403
from .foundation.async_utils import *  # noqa: F401,F403
from .session import *  # noqa: F401,F403
from .foundation.urls import *  # noqa: F401,F403
