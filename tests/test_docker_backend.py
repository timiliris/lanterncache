"""Docker backend contract tests. No daemon, network, credentials or game download."""
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import docker_backend as backend


class BackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.host_data = self.base / 'docker-host-data'
        self.patches = [patch.object(backend, 'BASE', self.base),
                        patch.object(backend, 'HOST_DATA', str(self.host_data))]
        for item in self.patches:
            item.start()
        self.engine = backend.Backend()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.temp.cleanup()

    def job(self, **options):
        directory = self.base / 'jobs' / 'test-job'
        directory.mkdir(parents=True)
        marker = {'directory': 'jobs/test-job', 'finished': False,
                  'status': 'running', 'night': False, 'check': False}
        marker.update(options)
        backend.atomic_json(self.engine.marker, marker)
        return directory

    def test_failed_job_preserves_completed_depots_and_removes_credentials(self):
        directory = self.job()
        (directory / 'account.config').write_text('private-test-token')
        backend.atomic_json(directory / 'successfullyDownloadedDepots.json', {'new': 42})
        main = self.base / 'prefill/successfullyDownloadedDepots.json'
        backend.atomic_json(main, {'existing': 7})
        with patch.object(backend, 'log_text', return_value='Unable to download manifests!'):
            self.engine._finish({'State': {'Running': False, 'ExitCode': 0}})
        self.assertEqual(json.loads(main.read_text()), {'existing': 7, 'new': 42})
        self.assertEqual(json.loads(self.engine.marker.read_text())['status'], 'failed')
        self.assertFalse(directory.exists())
        self.assertNotIn('private-test-token', (self.base / 'last-job.log').read_text())

    def test_manifest_phase_continues_as_download_inside_window(self):
        directory = self.job(night=True, check=True)
        with patch.object(backend, 'log_text', return_value='Prefill complete!'), \
             patch.object(self.engine, 'in_window', return_value=True), \
             patch.object(self.engine, '_container') as create:
            self.engine._finish({'State': {'Running': False, 'ExitCode': 0}})
        create.assert_called_once_with(directory, False)
        marker = json.loads(self.engine.marker.read_text())
        self.assertFalse(marker['check'])
        self.assertFalse(marker['finished'])
        self.assertTrue(directory.exists())

    def test_manifest_phase_does_not_download_outside_window(self):
        directory = self.job(night=True, check=True)
        with patch.object(backend, 'log_text', return_value='Prefill complete!'), \
             patch.object(self.engine, 'in_window', return_value=False), \
             patch.object(self.engine, '_container') as create:
            self.engine._finish({'State': {'Running': False, 'ExitCode': 0}})
        create.assert_not_called()
        self.assertTrue(json.loads(self.engine.marker.read_text())['finished'])
        self.assertFalse(directory.exists())

    def test_stop_disables_nightly_phase_before_finishing(self):
        self.job(night=True, check=True)
        running = {'State': {'Running': True},'Config':{'Labels':{'io.lanterncache.managed':'true'}}}
        stopped = {'State': {'Running': False, 'ExitCode': 0}}
        with patch.object(backend, 'inspect', side_effect=[running, stopped]), \
             patch.object(backend, 'api') as api, \
             patch.object(self.engine, '_finish') as finish:
            self.engine.stop()
        self.assertFalse(json.loads(self.engine.marker.read_text())['night'])
        api.assert_called_once_with('POST', f'/containers/{backend.JOB_CONTAINER}/stop?t=10')
        finish.assert_called_once_with(stopped)

    def test_snapshot_reports_running_download_after_manifest_transition(self):
        self.job(night=True, check=True)
        backend.atomic_json(self.engine.settings, {'nightEnabled': False})
        running = {'State': {'Running': True}, 'Config': {'Labels': {'io.lanterncache.managed': 'true'}}}
        stopped = {'State': {'Running': False, 'ExitCode': 0}}
        transitioned = False

        def inspect(name):
            if name == backend.JOB_CONTAINER:
                return running if transitioned else stopped
            return running

        def finish(container):
            nonlocal transitioned
            transitioned = True
            marker = json.loads(self.engine.marker.read_text())
            marker['check'] = False
            backend.atomic_json(self.engine.marker, marker)

        with patch.object(backend, 'inspect', side_effect=inspect), \
             patch.object(backend, 'log_text', return_value='Downloading'), \
             patch.object(self.engine, '_finish', side_effect=finish):
            state = self.engine.snapshot(backend.dt.datetime(2026, 10, 7, 2))
        self.assertEqual(state['active'], [backend.JOB_CONTAINER])
        self.assertEqual(state['jobMode'], 'download')

    def test_job_path_cannot_escape_private_jobs_directory(self):
        backend.atomic_json(self.engine.marker, {'directory': '../outside', 'finished': False})
        with patch.object(backend, 'log_text') as logs:
            with self.assertRaisesRegex(ValueError, 'Invalid job path'):
                self.engine._finish({'State': {'Running': False, 'ExitCode': 0}})
        logs.assert_not_called()

    def test_manual_download_isolates_only_requested_game(self):
        (self.base / 'prefill/account.config').write_text('private-test-token')
        backend.atomic_json(self.base / 'prefill/selectedAppsToPrefill.json', [714010, 526870])
        with patch.object(backend, 'inspect', return_value=None), \
             patch.object(self.engine, '_container') as create:
            self.engine.start(526870)
        directory, check = create.call_args.args
        self.assertFalse(check)
        self.assertEqual(json.loads((directory / 'selectedAppsToPrefill.json').read_text()), [526870])
        self.assertEqual(json.loads((self.base / 'prefill/selectedAppsToPrefill.json').read_text()), [714010, 526870])

    def test_manifest_container_cannot_download_chunks(self):
        directory = self.job()
        with patch.object(backend, 'inspect', return_value=None), \
             patch.object(backend, 'api', side_effect=[{'Id': 'new-job'}, {}]) as api:
            self.engine._container(directory, True)
        create = api.call_args_list[0]
        body = create.args[2]
        self.assertIn('--no-download', body['Cmd'])
        self.assertEqual(body['HostConfig']['RestartPolicy'], {'Name': 'no'})
        self.assertEqual(body['HostConfig']['NetworkMode'], 'container:' + backend.CACHE_CONTAINER)
        self.assertTrue(all(binding.startswith(str(self.host_data)) for binding in body['HostConfig']['Binds']))

    def test_log_protocol_preserves_stdout_and_stderr_frames(self):
        def frame(stream, text):
            encoded = text.encode()
            return struct.pack('>BBBBI', stream, 0, 0, 0, len(encoded)) + encoded
        with patch.object(backend, 'api', return_value=frame(1, 'Downloading\n') + frame(2, 'Retrying\n')):
            self.assertEqual(backend.log_text('test'), 'Downloading\nRetrying\n')

    def test_current_game_survives_progress_pushing_header_out_of_tail(self):
        name = 'context-test'
        backend._LOG_START.pop(name, None)
        with patch.object(backend, 'api', side_effect=[b'Starting Valheim\nDownloading\n', b'Progress\n' * 1100]) as api:
            backend.log_text(name)
            logs = backend.log_text(name)
        self.assertIn('Starting Valheim', logs)
        self.assertIn('tail=all', api.call_args_list[0].args[1])
        self.assertIn('tail=1000', api.call_args_list[1].args[1])
        self.assertLessEqual(len(logs.splitlines()), 101)
        backend._LOG_START.pop(name, None)

    def test_finish_reads_full_log_to_detect_earlier_skipped_games(self):
        self.job()
        logs = 'Starting Valheim\nUnable to download manifests! Skipping app...\n' + 'Progress\n' * 1100
        with patch.object(backend, 'log_text', return_value=logs) as read:
            self.engine._finish({'State': {'Running': False, 'ExitCode': 0}})
        read.assert_called_once_with(backend.JOB_CONTAINER, full=True)
        self.assertEqual(json.loads(self.engine.marker.read_text())['status'], 'failed')
        self.assertIn('Skipping app', (self.base / 'last-job.log').read_text())

    def test_unmanaged_container_collision_is_not_removed(self):
        directory = self.job()
        existing = {'State': {'Running': False}, 'Config': {'Labels': {'other.app': 'true'}}}
        with patch.object(backend, 'inspect', return_value=existing), \
             patch.object(backend, 'api') as api:
            with self.assertRaisesRegex(backend.DockerError, 'another application'):
                self.engine._container(directory, False)
        api.assert_not_called()

    def test_unmanaged_container_is_not_stopped_or_marker_changed(self):
        self.job(night=True)
        original = self.engine.marker.read_bytes()
        existing = {'State': {'Running': True}, 'Config': {'Labels': {}}}
        with patch.object(backend, 'inspect', return_value=existing), \
             patch.object(backend, 'api') as api:
            with self.assertRaisesRegex(backend.DockerError, 'not managed'):
                self.engine.stop()
        api.assert_not_called()
        self.assertEqual(self.engine.marker.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
