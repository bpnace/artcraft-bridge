"""Synthetic protocol and lifecycle regression tests. No installed apps required."""
import io
import json
import os
from pathlib import Path
import plistlib
import socket
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, Mock

from artcraft_bridge import bridge as b


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_paths = (b.BASE, b.RUNTIME, b.APPS_DIR)
        self.lock_patch = patch.object(b, 'LAUNCH_LOCK_DIR', self.root / 'global-locks', create=True)
        self.lock_patch.start()
        b.configure(self.root / 'workspace', self.root / 'runtime', self.root / 'apps')

    def tearDown(self):
        b.BASE, b.RUNTIME, b.APPS_DIR = self.old_paths
        self.lock_patch.stop()
        self.tmp.cleanup()

    def test_params_must_be_objects(self):
        for value in ([], False, 0, ''):
            with self.subTest(value=value), self.assertRaises(b.BridgeError):
                b.call('designcraft', 'ui.inspect', value)

    def test_timeout_limits(self):
        for value in (0, -1, 56, float('nan')):
            with self.subTest(value=value), self.assertRaises(b.BridgeError):
                b.call('designcraft', 'ui.inspect', timeout=value)

    def test_reply_id_matching(self):
        data = b'{"id":"other","result":1}\n{"id":"mine","result":2}\n'
        self.assertEqual(b.read_reply(io.BytesIO(data), 'mine'), 2)

    def test_rejected_reply(self):
        with self.assertRaises(b.BridgeError):
            b.read_reply(io.BytesIO(b'{"id":"x","error":"rejected"}\n'), 'x')

    def test_reply_requires_result(self):
        with self.assertRaises(b.BridgeError):
            b.read_reply(io.BytesIO(b'{"id":"x"}\n'), 'x')

    def test_incomplete_reply(self):
        with self.assertRaises(b.BridgeError):
            b.read_reply(io.BytesIO(b'{"id":"x","result":0}'), 'x')

    def test_reply_size_bound(self):
        with patch.object(b, 'MAX_REPLY', 10), self.assertRaises(b.BridgeError):
            b.read_reply(io.BytesIO(b'x' * 12 + b'\n'), 'x')

    def test_request_limit(self):
        with self.assertRaises(b.BridgeError):
            b.send(io.BytesIO(), {'text': 'x' * b.MAX_REQUEST}, 'x')

    def test_process_identity(self):
        identity = 'today ' + b.executable('designcraft')
        with patch.object(b, 'process_identity', return_value=identity):
            self.assertFalse(b.process_matches('designcraft', 123, identity='old identity'))
            self.assertTrue(b.process_matches('designcraft', 123, identity=identity))
            self.assertFalse(b.process_matches('designcraft', -1, identity=identity))

    def test_missing_state_is_actionable(self):
        with self.assertRaisesRegex(b.BridgeError, 'use its existing GUI if already running'):
            b.load_state('designcraft')

    def test_stale_state_rejected(self):
        b.atomic_json(b.state_path('designcraft'), {'app': 'designcraft', 'port': 1234, 'pid': 123})
        with patch.object(b, 'process_matches', return_value=False), self.assertRaises(b.BridgeError):
            b.load_state('designcraft')

    def test_atomic_state_is_private(self):
        path = b.state_path('designcraft')
        b.atomic_json(path, {'app': 'designcraft'})
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(json.loads(path.read_text())['app'], 'designcraft')
        self.assertFalse(path.with_suffix('.tmp').exists())

    def test_inventory_uses_configured_app_directory(self):
        binary = Path(b.executable('designcraft'))
        binary.parent.mkdir(parents=True)
        binary.touch()
        with (binary.parents[1] / 'Info.plist').open('wb') as stream:
            plistlib.dump({'CFBundleShortVersionString': '9.9.9'}, stream)
        row = next(row for row in b.inventory() if row['app'] == 'designcraft')
        self.assertTrue(row['installed'])
        self.assertEqual(row['version'], '9.9.9')

    def test_wall_clock_deadline(self):
        client, peer = socket.socketpair()
        def trickle():
            try:
                for _ in range(20):
                    peer.send(b' ')
                    time.sleep(.03)
            except OSError:
                pass
            finally:
                peer.close()
        worker = threading.Thread(target=trickle, daemon=True)
        worker.start()
        started = time.monotonic()
        with client, self.assertRaises((TimeoutError, socket.timeout)):
            b.DeadlineStream(client, started + .12).readline(1000)
        self.assertLess(time.monotonic() - started, .5)
        worker.join(.5)

    def test_no_mutation_retry(self):
        client, peer = socket.socketpair()
        received = []
        def serve():
            with peer:
                received.append(peer.recv(10000))
                peer.shutdown(socket.SHUT_RDWR)
        worker = threading.Thread(target=serve)
        worker.start()
        with patch.object(b.socket, 'create_connection', return_value=client) as connection:
            with self.assertRaises(b.BridgeError):
                b.call('designcraft', 'engine.execute', {'command': 'frame.create'}, state={'port': 1234}, timeout=1)
            self.assertEqual(connection.call_count, 1)
        worker.join()
        self.assertEqual(len(received), 1)
        self.assertEqual(json.loads(received[0])['method'], 'engine.execute')

    def test_authenticated_protocols(self):
        for app in ('photocraft', 'pdfcraft'):
            with self.subTest(app=app):
                token_file = self.root / 'synthetic-token'
                token_file.write_text(json.dumps({'token': 'synthetic'}) if app == 'pdfcraft' else 'synthetic')
                client, peer = socket.socketpair()
                requests = []
                def serve():
                    with peer, peer.makefile('rwb') as stream:
                        for _ in range(2):
                            req = json.loads(stream.readline())
                            requests.append(req)
                            reply = {'id': req['id'], 'result': {'accepted': True}}
                            if app == 'pdfcraft':
                                reply['jsonrpc'] = '2.0'
                            else:
                                reply['ok'] = True
                            stream.write((json.dumps(reply) + '\n').encode())
                            stream.flush()
                worker = threading.Thread(target=serve)
                worker.start()
                with patch.object(b.socket, 'create_connection', return_value=client):
                    result = b.call(app, 'ui.state', state={'port': 1234, 'token_file': str(token_file)}, timeout=1)
                worker.join(2)
                self.assertEqual(result, {'accepted': True})
                self.assertEqual([r['method'] for r in requests], ['auth', 'ui.state'])
                self.assertEqual(requests[0]['params'], {'token': 'synthetic'})
                self.assertEqual(requests[1].get('jsonrpc'), '2.0' if app == 'pdfcraft' else None)

    def test_public_calls_take_lifecycle_lock(self):
        state = {'port': 1234}
        with patch.object(b, 'load_state', return_value=state), patch.object(b.fcntl, 'flock') as lock, patch.object(b.socket, 'create_connection', side_effect=ConnectionRefusedError):
            with self.assertRaises(b.BridgeError):
                b.call('designcraft', 'ui.inspect')
            lock.assert_called_once()

    def test_stop_uses_captured_state(self):
        state = {'pid': 123, 'executable': 'x', 'process_identity': 'y'}
        with patch.object(b, 'load_state', return_value=state), patch.object(b, 'call', return_value={}) as call, patch.object(b, 'process_matches', return_value=False):
            self.assertTrue(b.stop_locked('designcraft')['stopped'])
            self.assertIs(call.call_args.kwargs['state'], state)

    def test_pdf_start_requires_copy_opt_in(self):
        with patch.object(b.platform, 'system', return_value='Darwin'), self.assertRaisesRegex(b.BridgeError, '--portable-copy'):
            b.start('pdfcraft')

    def test_pdf_stop_requires_signal_opt_in(self):
        with patch.object(b, 'load_state', return_value={}), patch.object(b.os, 'kill') as kill, self.assertRaisesRegex(b.BridgeError, '--allow-empty-pdf-termination'):
            b.stop_locked('pdfcraft')
        kill.assert_not_called()

    def test_pdf_with_documents_never_signalled(self):
        with patch.object(b, 'load_state', return_value={}), patch.object(b, 'call', return_value={'documents': [{'dirty': True}]}), patch.object(b.os, 'kill') as kill, self.assertRaisesRegex(b.BridgeError, 'open documents'):
            b.stop_locked('pdfcraft', True)
        kill.assert_not_called()

    def test_session_rejects_different_configuration(self):
        state = {'app': 'designcraft', 'port': 1234, 'pid': 123,
                 'workspace': str(b.BASE), 'apps_dir': str(b.APPS_DIR)}
        b.atomic_json(b.state_path('designcraft'), state)
        for key in ('workspace', 'apps_dir'):
            with self.subTest(key=key):
                changed = dict(state)
                changed[key] += '-different'
                b.atomic_json(b.state_path('designcraft'), changed)
                with self.assertRaises(b.SessionConflict):
                    b.load_state('designcraft')

    def test_start_does_not_replace_conflicting_session(self):
        with patch.object(b.platform, 'system', return_value='Darwin'), patch.object(b.Path, 'is_file', return_value=True), patch.object(b, 'load_state', side_effect=b.SessionConflict('different workspace')), patch.object(b.subprocess, 'Popen') as launch:
            with self.assertRaises(b.SessionConflict):
                b.start('designcraft')
            launch.assert_not_called()

    def test_process_scan_matches_executable_not_arguments(self):
        name = b.executable('designcraft')
        copied = '/private/test/DesignCraft.app/Contents/MacOS/DesignCraft'
        output = f' 101 {name}\n 102 {copied}\n 103 /usr/bin/python3\n 0 {name}\n -2 {name}\n 104 /tmp/DesignCraftHelper\n'
        with patch.object(b.subprocess, 'run', return_value=Mock(returncode=0, stdout=output)) as scan:
            self.assertEqual(b.running_instances('designcraft'), [101, 102])
        self.assertEqual(scan.call_args.args[0], ['ps', '-axo', 'pid=,comm='])

    def test_process_scan_failure_blocks_launch(self):
        with patch.object(b.subprocess, 'run', return_value=Mock(returncode=1, stdout='')), self.assertRaises(b.BridgeError):
            b.running_instances('designcraft')

    def test_start_refuses_external_or_cross_state_instance(self):
        for binary in (b.executable('designcraft'), '/other/state/DesignCraft.app/Contents/MacOS/DesignCraft'):
            with self.subTest(binary=binary), patch.object(b.platform, 'system', return_value='Darwin'), patch.object(b.Path, 'is_file', return_value=True), patch.object(b, 'load_state', side_effect=b.BridgeError('no state')), patch.object(b.subprocess, 'run', return_value=Mock(returncode=0, stdout=f' 987 {binary}\n')), patch.object(b.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(b.SessionConflict, '--allow-multiple'):
                    b.start('designcraft')
                launch.assert_not_called()

    def test_start_reuses_healthy_session_before_process_scan(self):
        state = {'pid': 123, 'port': 456}
        with patch.object(b.platform, 'system', return_value='Darwin'), patch.object(b.Path, 'is_file', return_value=True), patch.object(b, 'load_state', return_value=state), patch.object(b, 'call', return_value={}), patch.object(b, 'running_instances') as scan, patch.object(b.subprocess, 'Popen') as launch:
            self.assertTrue(b.start('designcraft')['reused'])
            scan.assert_not_called()
            launch.assert_not_called()

    def test_multiple_instances_require_explicit_opt_in(self):
        with patch.object(b.platform, 'system', return_value='Darwin'), patch.object(b.Path, 'is_file', return_value=True), patch.object(b, 'load_state', side_effect=b.BridgeError('no state')), patch.object(b, 'running_instances', return_value=[987]) as scan, patch.object(b.socket, 'socket'), patch.object(b.subprocess, 'Popen', side_effect=RuntimeError('launch reached')) as launch:
            with self.assertRaisesRegex(RuntimeError, 'launch reached'):
                b.start('designcraft', allow_multiple=True)
            scan.assert_not_called()
            launch.assert_called_once()

    def test_launch_lock_shared_across_state_directories(self):
        state = {'pid': 123, 'port': 456}
        with patch.object(b.platform, 'system', return_value='Darwin'), patch.object(b.Path, 'is_file', return_value=True), patch.object(b, 'load_state', return_value=state), patch.object(b, 'call', return_value={}):
            for directory in ('runtime-one', 'runtime-two'):
                b.configure(state_dir=self.root / directory)
                b.start('designcraft')
        lock = b.LAUNCH_LOCK_DIR / 'designcraft.lock'
        self.assertTrue(lock.is_file())
        self.assertEqual(lock.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(list(b.LAUNCH_LOCK_DIR.iterdir())), 1)

    def test_global_launch_lock_serializes_concurrent_starts(self):
        acquired = threading.Event()
        def competing_start():
            with b.launch_lock('designcraft'):
                acquired.set()
        with b.launch_lock('designcraft'):
            worker = threading.Thread(target=competing_start)
            worker.start()
            self.assertFalse(acquired.wait(.05))
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertTrue(acquired.is_set())

    def test_cli_multiple_instances_opt_in(self):
        with patch('sys.argv', ['artcraft-bridge', 'start', 'designcraft', '--allow-multiple']), patch.object(b, 'start', return_value={}) as start, patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(b.main(), 0)
        start.assert_called_once_with('designcraft', False, True)

    def test_non_macos_launch_rejected(self):
        with patch.object(b.platform, 'system', return_value='Linux'), self.assertRaisesRegex(b.BridgeError, 'macOS'):
            b.start('designcraft')

    def test_cli_params_file(self):
        path = self.root / 'params.json'
        path.write_text('{"page": 1}')
        with patch('sys.argv', ['artcraft-bridge', 'call', 'designcraft', 'ui.inspect', '--params-file', str(path)]), patch.object(b, 'call', return_value={}) as call, patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(b.main(), 0)
        self.assertEqual(call.call_args.args[2], {'page': 1})

    def test_cli_null_params_rejected(self):
        with patch('sys.argv', ['artcraft-bridge', 'call', 'designcraft', 'ui.inspect', 'null']), patch('sys.stderr', new_callable=io.StringIO):
            self.assertEqual(b.main(), 1)

    def test_cli_conflicting_params_rejected(self):
        with patch('sys.argv', ['artcraft-bridge', 'call', 'designcraft', 'ui.inspect', '{}', '--params-file', 'params.json']), patch('sys.stderr', new_callable=io.StringIO):
            self.assertEqual(b.main(), 1)


if __name__ == '__main__':
    unittest.main()
