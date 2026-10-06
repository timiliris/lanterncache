"""Exercise HTTP request boundaries without opening a socket or starting jobs."""
from email.message import Message
import importlib.util
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import docker_backend

# Importing the entrypoint must not initialize persistent Docker state in tests.
spec = importlib.util.spec_from_file_location('lanterncache_http_under_test', ROOT / 'server.py')
server = importlib.util.module_from_spec(spec)
with patch.object(docker_backend, 'Backend', return_value=Mock()):
    spec.loader.exec_module(server)


class HttpSecurityTests(unittest.TestCase):
    def setUp(self):
        self.backend = Mock()
        self.patches = [patch.object(server, 'BACKEND', self.backend),
                        patch.object(server, 'ALLOWED_HOSTS', {'lanterncache.local', '127.0.0.1'}),
                        patch.object(server, 'PUBLIC_ORIGINS', set()),
                        patch.object(server, 'TOKEN', 'test-csrf-token'),
                        patch.object(server, 'STATE', {'active': [], 'csrf': 'test-csrf-token'})]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()

    def request(self, path='/api/start', data=None, headers=None):
        handler = server.Handler.__new__(server.Handler)
        handler.path = path
        handler.headers = Message()
        payload = json.dumps({'id': 526870} if data is None else data).encode()
        defaults = {'Host': 'lanterncache.local:8088',
                    'Origin': 'http://lanterncache.local:8088',
                    'X-Cache-Token': 'test-csrf-token',
                    'Content-Length': str(len(payload))}
        defaults.update(headers or {})
        for key, value in defaults.items():
            if value is not None:
                handler.headers[key] = value
        handler.rfile = io.BytesIO(payload)
        handler.send = Mock()
        return handler

    def status(self, handler):
        return handler.send.call_args.args[0]

    def test_disallowed_host_cannot_read_state_even_with_token(self):
        handler = self.request('/api/state', headers={'Host': 'attacker.example:8088'})
        handler.do_GET()
        self.assertEqual(self.status(handler), 403)
        self.assertEqual(handler.send.call_args.args[1]['code'], 'host_forbidden')

    def test_dns_rebinding_host_cannot_start_download(self):
        handler = self.request(headers={'Host': 'attacker.example:8088', 'Origin': 'http://attacker.example:8088'})
        handler.do_POST()
        self.assertEqual(self.status(handler), 403)
        self.backend.start.assert_not_called()

    def test_allowed_host_includes_port_and_is_case_insensitive(self):
        handler = self.request('/api/state', headers={'Host': 'LANTERNCACHE.LOCAL:8088'})
        handler.do_GET()
        self.assertEqual(self.status(handler), 200)

    def test_missing_or_wrong_csrf_cannot_start_download(self):
        for token in [None, 'wrong-token']:
            with self.subTest(token=token):
                handler = self.request(headers={'X-Cache-Token': token})
                handler.do_POST()
                self.assertEqual(self.status(handler), 403)
        self.backend.start.assert_not_called()

    def test_cross_origin_request_is_rejected_with_correct_csrf(self):
        handler = self.request(headers={'Origin': 'https://attacker.example'})
        handler.do_POST()
        self.assertEqual(self.status(handler), 403)
        self.backend.start.assert_not_called()

    def test_origin_is_required_on_mutating_requests(self):
        handler = self.request('/api/stop', headers={'Origin': None})
        handler.do_POST()
        self.assertEqual(self.status(handler), 403)
        self.backend.stop.assert_not_called()

    def test_valid_request_starts_only_requested_known_game(self):
        handler = self.request()
        handler.do_POST()
        self.assertEqual(self.status(handler), 200)
        self.backend.start.assert_called_once_with(526870, check=False)

    def test_configured_https_origin_is_accepted(self):
        with patch.object(server, 'PUBLIC_ORIGINS', {'https://lanterncache.local'}):
            handler = self.request('/api/check', headers={'Origin': 'https://lanterncache.local'})
            handler.do_POST()
        self.assertEqual(self.status(handler), 200)
        self.backend.start.assert_called_once_with(526870, check=True)

    def test_unknown_game_is_rejected_before_backend(self):
        handler = self.request(data={'id': 999999})
        handler.do_POST()
        self.assertEqual(self.status(handler), 400)
        self.backend.start.assert_not_called()

    def test_oversized_payload_is_rejected_without_reading_body(self):
        handler = self.request(headers={'Content-Length': '4097'})
        handler.rfile = Mock()
        handler.do_POST()
        self.assertEqual(self.status(handler), 400)
        handler.rfile.read.assert_not_called()
        self.backend.start.assert_not_called()

    def test_schedule_rejects_numeric_boolean(self):
        handler = self.request('/api/schedule', data={'enabled': 1})
        handler.do_POST()
        self.assertEqual(self.status(handler), 400)
        self.backend.schedule.assert_not_called()

    def test_arbitrary_filesystem_paths_are_not_served(self):
        for path in ['/../server.py', '/locales/../../account.config', '/server.py']:
            with self.subTest(path=path):
                handler = self.request(path)
                handler.do_GET()
                self.assertEqual(self.status(handler), 404)


if __name__ == '__main__':
    unittest.main()
