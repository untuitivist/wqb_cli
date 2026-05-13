import importlib
import inspect
import os
import unitest
from collections.abc import Generator
from pathlib import Path

from wqb_core import WQBSession


ROOT_DIR = Path(__file__).resolve().parents[1]
_SHARED_SESSION: WQBSession | None = None


def _default_community_export_file() -> str | None:
    candidates = []
    for base in (
        Path.home() / 'Downloads',
        Path(r'U:\Project\MainCode\3.Work\WQB\WebDataScope-0.9.3'),
    ):
        if not base.exists():
            continue
        candidates.extend(base.glob('WQPCommunityState_*.json'))
        candidates.extend(base.glob('WQPCommunityState_*.wqcs'))
    candidates = [p for p in candidates if p.is_file()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0])

READONLY_METHOD_ARGS = {
    'get_authentication': (),
    'head_authentication': (),
    'get_user_profile': ('self',),
    'get_user_alphas': (),
    'get_events': (),
    'get_leaderboard': (),
    'get_tutorials': (),
    'get_messages_summary': (),
    'get_messages': (),
    'get_pyramid_multipliers': (),
    'get_pyramid_alphas': (),
    'get_user_competitions': (),
    'get_instrument_options': (),
    'get_platform_setting_options': (),
    'get_datasets': (),
    'get_datafields': (),
    'get_operators': (),
    'search_operators': (),
    'filter_alphas_limited': (),
    'filter_alphas': (),
    'search_datasets_limited': ('USA', 1, 'TOP3000'),
    'search_datasets': ('USA', 1, 'TOP3000'),
    'search_fields_limited': ('USA', 1, 'TOP3000'),
    'search_fields': ('USA', 1, 'TOP3000'),
    'export_community_storage': (),
    'search_community_storage': ('alpha',),
}

READONLY_METHOD_KWARGS = {
    'get_messages_summary': {'limit': 3},
    'get_messages': {'limit': 3},
    'get_pyramid_alphas': {'scope': 'quarter'},
    'filter_alphas_limited': {'limit': 3},
    'filter_alphas': {'limit': 3},
    'search_datasets_limited': {'limit': 3},
    'search_datasets': {'limit': 3},
    'search_fields_limited': {'limit': 3},
    'search_fields': {'limit': 3},
    'export_community_storage': {'source_path': _default_community_export_file()},
    'search_community_storage': {'limit': 3},
}

ID_ENV_MAP = {
    'alpha_id': 'WQB_TEST_ALPHA_ID',
    'competition_id': 'WQB_TEST_COMPETITION_ID',
    'recordset_name': 'WQB_TEST_RECORDSET_NAME',
    'dataset_id': 'WQB_TEST_DATASET_ID',
    'field_id': 'WQB_TEST_FIELD_ID',
    'simulation_url': 'WQB_TEST_SIMULATION_URL',
    'user_id': 'WQB_TEST_USER_ID',
}

WRITE_METHODS = {
    'delete_authentication',
    'post_authentication',
    'patch_properties',
    'set_alpha_properties',
    'simulate',
    'submit',
    'run_selection',
    'check',
    'concurrent_check',
    'concurrent_simulate',
    'wait_for_simulation',
}

AUTO_RESOLVERS = {
    'alpha_id': '_resolve_alpha_id',
    'competition_id': '_resolve_competition_id',
    'dataset_id': '_resolve_dataset_id',
    'field_id': '_resolve_field_id',
    'page_id': '_resolve_tutorial_page_id',
    'recordset_name': '_resolve_recordset_name',
}


def _clear_proxies() -> None:
    for key in (
        'HTTP_PROXY',
        'HTTPS_PROXY',
        'ALL_PROXY',
        'http_proxy',
        'https_proxy',
        'all_proxy',
    ):
        os.environ.pop(key, None)


class ModuleContractTestCase(unitest.TestCase):
    __test__ = False
    module_name: str = ''
    expected_classes: tuple[str, ...] = ()
    expected_functions: tuple[str, ...] = ()
    method_name: str | None = None

    @classmethod
    def import_target(cls):
        if not cls.module_name:
            raise unitest.SkipTest('base contract class')
        return importlib.import_module(cls.module_name)

    @classmethod
    def setUpClass(cls):
        global _SHARED_SESSION
        _clear_proxies()
        if _SHARED_SESSION is None:
            _SHARED_SESSION = WQBSession()
            _SHARED_SESSION.trust_env = False
        cls.session = _SHARED_SESSION

    def test_import_module(self):
        module = self.import_target()
        self.assertIsNotNone(module)

    def test_expected_classes_exist(self):
        module = self.import_target()
        for name in self.expected_classes:
            with self.subTest(name=name):
                self.assertTrue(hasattr(module, name))
                self.assertTrue(inspect.isclass(getattr(module, name)))

    def test_expected_functions_exist(self):
        module = self.import_target()
        for name in self.expected_functions:
            with self.subTest(name=name):
                self.assertTrue(hasattr(module, name))
                self.assertTrue(callable(getattr(module, name)))

    @classmethod
    def _first_result(cls, payload):
        if isinstance(payload, dict):
            results = payload.get('results')
            if isinstance(results, list) and results:
                return results[0]
        if isinstance(payload, list) and payload:
            return payload[0]
        return None

    @classmethod
    def _resolve_alpha_id(cls):
        payload = cls.session.get_user_alphas(limit=1).json()
        first = cls._first_result(payload)
        if not first or 'id' not in first:
            raise unitest.SkipTest('unable to auto-resolve alpha_id from live get_user_alphas')
        return first['id']

    @classmethod
    def _resolve_competition_id(cls):
        payload = cls.session.get_user_competitions().json()
        first = cls._first_result(payload)
        if not first or 'id' not in first:
            raise unitest.SkipTest(
                'unable to auto-resolve competition_id from live get_user_competitions'
            )
        return first['id']

    @classmethod
    def _resolve_dataset_id(cls):
        payload = cls.session.get_datasets().json()
        first = cls._first_result(payload)
        if not first or 'id' not in first:
            raise unitest.SkipTest('unable to auto-resolve dataset_id from live get_datasets')
        return first['id']

    @classmethod
    def _resolve_field_id(cls):
        payload = cls.session.get_datafields(limit=1).json()
        first = cls._first_result(payload)
        if not first or 'id' not in first:
            raise unitest.SkipTest('unable to auto-resolve field_id from live get_datafields')
        return first['id']

    @classmethod
    def _resolve_tutorial_page_id(cls):
        payload = cls.session.get_tutorials().json()
        tutorial = cls._first_result(payload)
        pages = tutorial.get('pages') if isinstance(tutorial, dict) else None
        if not isinstance(pages, list) or not pages or 'id' not in pages[0]:
            raise unitest.SkipTest(
                'unable to auto-resolve page_id from live get_tutorials response'
            )
        return pages[0]['id']

    @classmethod
    def _resolve_recordset_name(cls):
        alpha_id = os.environ.get('WQB_TEST_ALPHA_ID') or cls._resolve_alpha_id()
        payload = cls.session.get_alpha_recordsets(alpha_id).json()
        first = cls._first_result(payload)
        if isinstance(first, dict):
            for key in ('name', 'id'):
                if first.get(key):
                    return first[key]
        raise unitest.SkipTest(
            'unable to auto-resolve recordset_name from live get_alpha_recordsets response'
        )

    def resolve_call(self):
        if not self.method_name:
            raise unitest.SkipTest('no live method configured')
        method = getattr(self.session, self.method_name)
        if self.method_name in WRITE_METHODS:
            raise unitest.SkipTest(f'{self.method_name} is gated due to side effects or environment limits')
        if self.method_name in READONLY_METHOD_ARGS:
            return method, READONLY_METHOD_ARGS[self.method_name], READONLY_METHOD_KWARGS.get(
                self.method_name, {}
            )
        sig = inspect.signature(method)
        args = []
        kwargs = {}
        for param in sig.parameters.values():
            if param.name == 'self':
                continue
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            if param.name == 'log':
                kwargs['log'] = None
                continue
            env_name = ID_ENV_MAP.get(param.name)
            if env_name and os.environ.get(env_name):
                value = os.environ[env_name]
                if param.annotation is int:
                    value = int(value)
                args.append(value)
                continue
            resolver_name = AUTO_RESOLVERS.get(param.name)
            if resolver_name:
                args.append(getattr(self, resolver_name)())
                continue
            if param.default is not inspect._empty:
                continue
            raise unitest.SkipTest(
                f'missing required environment variable for {self.method_name}: {param.name}'
            )
        return method, tuple(args), kwargs

    def test_live_integration(self):
        method, args, kwargs = self.resolve_call()
        try:
            result = method(*args, **kwargs)
        except PermissionError as exc:
            raise unitest.SkipTest(f'environment blocked subprocess/browser launch: {exc}')
        except Exception as exc:
            message = str(exc)
            if 'WinError 5' in message or '拒绝访问' in message:
                raise unitest.SkipTest(f'environment blocked subprocess/browser launch: {exc}')
            raise
        if inspect.isgenerator(result) or isinstance(result, Generator):
            try:
                result = next(result)
            except StopIteration:
                raise unitest.SkipTest(f'{self.method_name} returned no live pages')
        if hasattr(result, 'status_code'):
            self.assertLess(result.status_code, 500)
            return
        self.assertIsNotNone(result)
