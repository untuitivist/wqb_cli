"""
功能概述
`wqb_core.foundation.credentials` 模块。

这个文件负责从显式参数、环境变量和 `.env` 文件中解析 WQB 认证信息。

主推荐入口
- `find_dotenv(...)`
- `load_dotenv_values(...)`
- `resolve_wqb_auth(...)`

适用场景
- 在不同工作目录下自动查找 `.env`
- 读取 `.env` 中的 `EMAIL/PASSWORD`
- 将认证输入统一解析成 `HTTPBasicAuth`

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- `resolve_wqb_auth` 会在找不到认证信息时显式报错，而不是静默返回空值。
"""

import os
from pathlib import Path

from requests.auth import HTTPBasicAuth

__all__ = ['find_dotenv', 'load_dotenv_values', 'resolve_wqb_auth']


def find_dotenv(dotenv_path: str | os.PathLike[str] | None = None) -> Path | None:
    """
    查找 `.env` 文件路径。
    """
    candidates: list[Path] = []
    if dotenv_path is not None:
        candidates.append(Path(dotenv_path))
    else:
        candidates.append(Path.cwd() / '.env')
        current = Path(__file__).resolve().parent
        candidates.extend(parent / '.env' for parent in (current, *current.parents))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_dotenv_values(
    dotenv_path: str | os.PathLike[str] | None = None,
) -> dict[str, str]:
    """
    读取 `.env` 文件中的键值对。
    """
    env_file = find_dotenv(dotenv_path)
    if env_file is None:
        return {}
    values: dict[str, str] = {}
    for raw_line in env_file.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def resolve_wqb_auth(
    wqb_auth: tuple[str, str] | HTTPBasicAuth | None = None,
    *,
    prefer_dotenv: bool = True,
    dotenv_path: str | os.PathLike[str] | None = None,
) -> HTTPBasicAuth:
    """
    综合显式参数与 `.env` 文件解析 WQB 认证信息。
    """
    dotenv_values = load_dotenv_values(dotenv_path)
    dotenv_email = dotenv_values.get('EMAIL') or dotenv_values.get('WQB_EMAIL')
    dotenv_password = dotenv_values.get('PASSWORD') or dotenv_values.get('WQB_PASSWORD')
    dotenv_auth = (
        HTTPBasicAuth(dotenv_email, dotenv_password)
        if dotenv_email is not None and dotenv_password is not None
        else None
    )
    explicit_auth = wqb_auth
    if explicit_auth is not None and not isinstance(explicit_auth, HTTPBasicAuth):
        explicit_auth = HTTPBasicAuth(*explicit_auth)
    resolved = dotenv_auth or explicit_auth if prefer_dotenv else explicit_auth or dotenv_auth
    if resolved is None:
        raise ValueError(
            "WQB credentials not found. Provide `wqb_auth=(email, password)` "
            "or create a `.env` with `EMAIL=...` and `PASSWORD=...`."
        )
    return resolved
