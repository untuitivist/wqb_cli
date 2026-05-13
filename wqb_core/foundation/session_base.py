"""
功能概述
`wqb_core.foundation.session_base` 模块。

这个文件提供 `WQBSessionBase`，用于把认证解析、自动登录与基础会话行为整合成
`WQBSession` 可继承的底座。

主推荐入口
- `WQBSessionBase`

适用场景
- 构造带自动认证能力的底层 session
- 统一管理 `wqb_auth`、认证 endpoint 和 `Location` 判定逻辑

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 上层通常不直接实例化 `WQBSessionBase`，而是使用 `WQBSession`。
"""

import json
import logging
from pathlib import Path

from requests.auth import HTTPBasicAuth
from requests.utils import cookiejar_from_dict, dict_from_cookiejar

from .auto_auth_session import AutoAuthSession
from .credentials import resolve_wqb_auth
from .defines import LOCATION, POST
from .urls import URL_AUTHENTICATION

__all__ = ['WQBSessionBase']


class WQBSessionBase(AutoAuthSession):
    """
    `WQBSession` 的基础会话类。

    负责解析认证信息，并把自动认证流程配置到 requests session 行为中。
    """

    def __init__(
        self,
        wqb_auth: tuple[str, str] | HTTPBasicAuth | None = None,
        *,
        logger: logging.Logger = logging.root,
        prefer_dotenv: bool = True,
        dotenv_path: str | None = None,
        shared_auth: bool = True,
        auth_cache_path: str | None = None,
        **kwargs,
    ) -> None:
        wqb_auth = resolve_wqb_auth(
            wqb_auth,
            prefer_dotenv=prefer_dotenv,
            dotenv_path=dotenv_path,
        )
        kwargs['auth'] = wqb_auth
        super().__init__(
            POST,
            URL_AUTHENTICATION,
            auth_expected=lambda resp: 201 == resp.status_code,
            expected=lambda resp: resp.status_code not in (204, 401, 429),
            logger=logger,
            **kwargs,
        )
        self.shared_auth = shared_auth
        self.auth_cache_path = self._resolve_auth_cache_path(auth_cache_path)
        self.expected_location = (
            lambda resp: self.expected(resp) and LOCATION in resp.headers
        )
        if self.shared_auth:
            self._load_auth_cache()

    def __repr__(self) -> str:
        return "<WQBSession>"

    @staticmethod
    def _resolve_auth_cache_path(auth_cache_path: str | None) -> Path:
        if auth_cache_path is not None:
            return Path(auth_cache_path)
        root = Path(__file__).resolve().parents[2]
        return root / '.wqb_cli_auth' / 'cookies.json'

    def _load_auth_cache(self) -> None:
        """
        从本地缓存恢复 cookie，避免每个 CLI 脚本都重新登录。
        """
        try:
            if not self.auth_cache_path.is_file():
                return
            payload = json.loads(self.auth_cache_path.read_text(encoding='utf-8'))
            cookies = payload.get('cookies')
            if not isinstance(cookies, dict) or not cookies:
                return
            self.cookies = cookiejar_from_dict(cookies, cookiejar=self.cookies)
        except Exception as exc:
            self.logger.warning(f"{self} failed to load auth cache: {exc}")

    def _save_auth_cache(self) -> None:
        """
        将当前 session cookie 写入本地缓存，供其他 CLI 脚本复用。
        """
        try:
            self.auth_cache_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                'cookies': dict_from_cookiejar(self.cookies),
            }
            self.auth_cache_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
        except Exception as exc:
            self.logger.warning(f"{self} failed to save auth cache: {exc}")

    def auth_request(self, *args, **kwargs):
        """
        执行认证请求，并在成功后持久化最新 cookie。
        """
        resp = super().auth_request(*args, **kwargs)
        if self.shared_auth and self.auth_expected(resp):
            self._save_auth_cache()
        return resp

    def request(self, method: str, url: str, *args, **kwargs):
        """
        执行业务请求；若当前 cookie 仍然有效，也会顺手刷新本地缓存。
        """
        resp = super().request(method, url, *args, **kwargs)
        if self.shared_auth and self.expected(resp):
            self._save_auth_cache()
        return resp

    @property
    def wqb_auth(self) -> HTTPBasicAuth:
        """
        返回当前 session 持有的认证对象。
        """
        return self.kwargs['auth']

    @wqb_auth.setter
    def wqb_auth(self, wqb_auth: tuple[str, str] | HTTPBasicAuth) -> None:
        """
        更新当前 session 的认证对象。
        """
        self.kwargs['auth'] = resolve_wqb_auth(wqb_auth, prefer_dotenv=False)
