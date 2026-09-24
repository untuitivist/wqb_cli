from __future__ import annotations

import json
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

import requests

from wqb_cli.core.community_client import CommunityClient, CommunityError
from wqb_cli.core.community_session import CommunitySessionStore, profile_key, restore_cookies, session_cookies


def page(identifier=20, status=200):
    reply = requests.Response()
    reply.status_code = status
    reply._content = json.dumps({'user': {'id': identifier, 'role': 'end-user'}}).encode('utf-8')
    return reply


class CommunitySessionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.path = self.root / 'sessions.sqlite3'
        self.jar = requests.cookies.RequestsCookieJar()
        self.jar.set('_help_center_session', 'fixture-private', domain='support.worldquantbrain.com',
                     path='/hc', secure=True, expires=int(time.time()) + 3600)

    def store(self, profile='fixture'):
        return CommunitySessionStore(self.path, profile)

    def payload(self):
        return {'version': 1, 'user_id': '20', 'saved_at': time.time(), 'cookies': session_cookies(self.jar)}

    def client(self, replies):
        brain = Mock()
        brain.session.cookies = requests.cookies.RequestsCookieJar()
        brain.call_once.return_value = {'ok': True, 'response': {'location': 'https://support.worldquantbrain.com/hc/en-us'}}
        session = Mock()
        session.cookies = self.jar.copy()
        session.get.side_effect = replies
        client = CommunityClient(brain_client=brain, session=session, session_store=self.store())
        return client, brain, session

    def seed(self):
        store = self.store()
        store.load()
        self.assertTrue(store.save(self.payload()))

    def test_cookie_scope_flags_expiry_are_preserved(self):
        records = session_cookies(self.jar)
        loaded = list(restore_cookies(records))[0]
        original = list(self.jar)[0]
        for attribute in ('domain', 'domain_specified', 'path', 'secure', 'expires', 'discard', 'value'):
            self.assertEqual(getattr(loaded, attribute), getattr(original, attribute))

    def test_expired_foreign_brain_and_challenge_cookies_are_not_cached(self):
        self.jar.set('token', 'private', domain='api.worldquantbrain.com')
        self.jar.set('_help_center_session', 'foreign', domain='example.com')
        self.jar.set('cf_clearance', 'not-an-auth-cookie', domain='support.worldquantbrain.com')
        self.jar.set('_zendesk_session', 'expired', domain='support.worldquantbrain.com', expires=1)
        self.assertEqual(len(session_cookies(self.jar)), 1)

    def test_next_process_reuses_valid_session_without_brain_login(self):
        self.seed()
        client, brain, session = self.client([page()])
        client.authenticate()
        self.assertTrue(client.authenticated)
        self.assertEqual(client.cache_status, 'reused')
        brain.call_once.assert_not_called()
        self.assertEqual(session.get.call_count, 1)

    def test_fresh_sso_session_is_saved(self):
        client, brain, session = self.client([page()])
        client.authenticate()
        self.assertEqual(client.cache_status, 'saved')
        self.assertEqual(self.store().load()['user_id'], '20')

    def test_expired_server_session_renews_once(self):
        self.seed()
        client, brain, session = self.client([page(status=401), page()])
        client.authenticate()
        self.assertTrue(client.authenticated)
        self.assertEqual(brain.call_once.call_count, 1)
        self.assertEqual(session.get.call_count, 2)

    def test_anonymous_200_is_not_authentication_success(self):
        client, brain, session = self.client([page(identifier=None)])
        with self.assertRaises(CommunityError) as raised:
            client.authenticate()
        self.assertEqual(raised.exception.code, 'community_session_unverified')
        self.assertIsNone(self.store().load())

    def test_cache_identity_mismatch_cannot_silently_switch_account(self):
        self.seed()
        client, brain, session = self.client([page(identifier=99), page()])
        client.authenticate()
        self.assertEqual(client.user_id, '20')
        self.assertEqual(brain.call_once.call_count, 1)

    def test_account_and_config_profiles_are_isolated(self):
        first = profile_key('a@example.com', self.root / 'a', self.root / 'cookies')
        second = profile_key('b@example.com', self.root / 'a', self.root / 'cookies')
        third = profile_key('a@example.com', self.root / 'b', self.root / 'cookies')
        self.assertEqual(len({first, second, third}), 3)
        store = self.store(first)
        store.load()
        store.save(self.payload())
        self.assertIsNone(self.store(second).load())

    def test_stale_process_cannot_overwrite_or_invalidate_newer_session(self):
        self.seed()
        first, second = self.store(), self.store()
        first.load()
        second.load()
        replacement = self.payload() | {'user_id': '21'}
        self.assertTrue(second.save(replacement))
        self.assertFalse(first.save(self.payload()))
        self.assertFalse(first.save(None))
        self.assertEqual(self.store().load()['user_id'], '21')

    def test_invalidated_session_cannot_be_resurrected_by_stale_process(self):
        self.seed()
        first, second = self.store(), self.store()
        first.load()
        second.load()
        self.assertTrue(second.save(None))
        self.assertFalse(first.save(self.payload()))
        self.assertIsNone(self.store().load())

    def test_old_or_corrupt_payload_falls_back_to_sso(self):
        store = self.store()
        store.load()
        store.save(self.payload() | {'saved_at': 0})
        self.assertIsNone(self.store().load())
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute("UPDATE sessions SET payload='broken'")
        self.assertIsNone(self.store().load())

    def test_challenge_is_not_saved_as_a_valid_session(self):
        challenged = page(status=403)
        challenged.headers['cf-mitigated'] = 'challenge'
        client, brain, session = self.client([challenged])
        with self.assertRaises(CommunityError) as raised:
            client.authenticate()
        self.assertEqual(raised.exception.code, 'browser_verification_required')
        self.assertIsNone(self.store().load())

    def test_unwritable_cache_does_not_prevent_successful_authentication(self):
        client, brain, session = self.client([page()])
        client.session_store = Mock()
        client.session_store.load.side_effect = OSError('private-path')
        client.authenticate()
        self.assertTrue(client.authenticated)
        self.assertEqual(client.cache_status, 'read_failed')

    def test_cache_validation_rate_limit_waits_without_new_login(self):
        self.seed()
        limited = page(status=429)
        limited.headers['Retry-After'] = '2'
        client, brain, session = self.client([limited, page()])
        client.sleeper = Mock()
        client.authenticate()
        client.sleeper.assert_called_once_with(2)
        brain.call_once.assert_not_called()
        self.assertEqual(client.cache_status, 'reused')

    def test_cache_validation_outage_preserves_persisted_session(self):
        self.seed()
        unavailable = page(status=503)
        unavailable.headers['Retry-After'] = '1000'
        client, brain, session = self.client([unavailable])
        with self.assertRaises(CommunityError):
            client.authenticate()
        self.assertIsNotNone(self.store().load())
        brain.call_once.assert_not_called()

    def test_rotated_cookie_is_saved_after_successful_api_read(self):
        client, brain, session = self.client([page()])
        client.authenticate()
        session.cookies.set('_help_center_session', 'rotated', domain='support.worldquantbrain.com', path='/hc')
        reply = page()
        reply._content = b'{"posts":[]}'
        session.request.return_value = reply
        self.assertTrue(client.call('GET', '/api/v2/community/posts.json')['ok'])
        loaded = restore_cookies(self.store().load()['cookies'])
        self.assertEqual(loaded.get('_help_center_session', domain='support.worldquantbrain.com', path='/hc'), 'rotated')


if __name__ == '__main__':
    unittest.main()
