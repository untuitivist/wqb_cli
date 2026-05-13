"""
功能概述
`wqb_core.data.get_platform_setting_options` 模块。

这个文件提供与当前文件名对应的具体实现。

主推荐入口
- `get_platform_setting_options(...)`

适用场景
- 作为库模块被导入使用。

注意事项
- 本文件中的中文说明已按 UTF-8 重写。
- 具体参数、返回值和示例以函数签名与方法 docstring 为准。
"""

if __name__ == "__main__" and (__package__ is None or __package__ == ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    __package__ = "wqb_core.data"

from ..foundation.urls import URL_SIMULATIONS


class GetPlatformSettingOptionsMixin:
    def get_platform_setting_options(
        self,
        *args,
        log: str | None = '',
        **kwargs,
    ) -> dict:
        """
        获取当前账号可用的 market settings。
        
        该方法通过 `WQBSession.get_platform_setting_options(...)` 暴露。
        """
        url = URL_SIMULATIONS
        resp = self.options(url, *args, **kwargs)
        resp.raise_for_status()
        settings_data = resp.json()
        settings_options = settings_data['actions']['POST']['settings']['children']
        instrument_type_data = {}
        region_data = {}
        universe_data = {}
        delay_data = {}
        neutralization_data = {}
        for _, setting in settings_options.items():
            if setting['type'] != 'choice':
                continue
            if setting['label'] == 'Instrument type':
                instrument_type_data = setting['choices']
            elif setting['label'] == 'Region':
                region_data = setting['choices']['instrumentType']
            elif setting['label'] == 'Universe':
                universe_data = setting['choices']['instrumentType']
            elif setting['label'] == 'Delay':
                delay_data = setting['choices']['instrumentType']
            elif setting['label'] == 'Neutralization':
                neutralization_data = setting['choices']['instrumentType']
        data_list = []
        for instrument_type in instrument_type_data:
            instrument_value = instrument_type['value']
            for region in region_data[instrument_value]:
                region_value = region['value']
                for delay in delay_data[instrument_value]['region'][region_value]:
                    data_list.append(
                        {
                            'InstrumentType': instrument_value,
                            'Region': region_value,
                            'Delay': delay['value'],
                            'Universe': [
                                item['value']
                                for item in universe_data[instrument_value]['region'][region_value]
                            ],
                            'Neutralization': [
                                item['value']
                                for item in neutralization_data[instrument_value]['region'][region_value]
                            ],
                        }
                    )
        if log is not None:
            self.logger.info(
                '\n'.join(
                    (
                        f"{self}.get_platform_setting_options(...) [",
                        f"    {url}",
                        f"]: {log}",
                    )
                )
            )
        return {
            'instrument_options': data_list,
            'total_combinations': len(data_list),
            'instrument_types': [item['value'] for item in instrument_type_data],
            'regions_by_type': {
                item['value']: [r['value'] for r in region_data[item['value']]]
                for item in instrument_type_data
            },
        }

if __name__ == "__main__":
    import argparse
    import asyncio
    import inspect
    import json

    from wqb_core import WQBSession
    from requests import Response

    def _cli_parse_value(text: str):
        lowered = text.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if lowered in {"null", "none"}:
            return None
        if text.startswith("@json:"):
            return json.loads(text[6:])
        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        try:
            return int(text)
        except ValueError:
            pass
        try:
            return float(text)
        except ValueError:
            pass
        return text

    def _cli_collect_unknown(tokens: list[str]) -> dict[str, object]:
        data: dict[str, object] = {}
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if not token.startswith("--"):
                raise SystemExit(f"Unsupported positional argument: {token!r}")
            if "=" in token:
                key_text, value_text = token.split("=", 1)
                key = key_text[2:].replace("-", "_")
                value = _cli_parse_value(value_text)
                if key in data:
                    current = data[key]
                    if isinstance(current, list):
                        current.append(value)
                    else:
                        data[key] = [current, value]
                else:
                    data[key] = value
                i += 1
                continue
            key = token[2:].replace("-", "_")
            if i + 1 >= len(tokens) or tokens[i + 1].startswith("--"):
                value = True
                i += 1
            else:
                value = _cli_parse_value(tokens[i + 1])
                i += 2
            if key in data:
                current = data[key]
                if isinstance(current, list):
                    current.append(value)
                else:
                    data[key] = [current, value]
            else:
                data[key] = value
        return data

    def _cli_serialize(value):
        if isinstance(value, Response):
            payload = {
                "status_code": value.status_code,
                "reason": value.reason,
                "url": value.url,
                "headers": dict(value.headers),
            }
            try:
                payload["json"] = value.json()
            except ValueError:
                payload["text"] = value.text
            return payload
        if isinstance(value, dict):
            return {str(k): _cli_serialize(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [_cli_serialize(v) for v in value]
        if inspect.isgenerator(value):
            return [_cli_serialize(v) for v in list(value)]
        return value

    parser = argparse.ArgumentParser(description=inspect.getdoc(GetPlatformSettingOptionsMixin.get_platform_setting_options) or "")
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--prefer-dotenv")
    parser.add_argument("--dotenv-path")
    args, unknown = parser.parse_known_args()

    session_kwargs = {}
    if args.prefer_dotenv is not None:
        session_kwargs["prefer_dotenv"] = _cli_parse_value(args.prefer_dotenv)
    if args.dotenv_path is not None:
        session_kwargs["dotenv_path"] = args.dotenv_path
    if args.username is not None or args.password is not None:
        if args.username is None or args.password is None:
            raise SystemExit("--username and --password must be provided together")
        session_kwargs["wqb_auth"] = (args.username, args.password)

    session = WQBSession(**session_kwargs)

    target = getattr(session, "get_platform_setting_options")
    kwargs = _cli_collect_unknown(unknown)
    result = target(**kwargs)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    print(json.dumps(_cli_serialize(result), ensure_ascii=False, indent=2, default=str))
