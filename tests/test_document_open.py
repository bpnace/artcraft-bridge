"""CADCraft document reuse regressions; no desktop apps are launched."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from artcraft_bridge import bridge as b


class DocumentOpenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.runtime_patch = patch.object(b, 'RUNTIME', self.root / 'runtime')
        self.runtime_patch.start()
        self.path = self.root / 'seat.dxf'
        self.path.write_text('saved document')
        self.state = {'port': 12345}

    def tearDown(self):
        self.runtime_patch.stop()
        self.temp.cleanup()

    def doc(self, index=0, dirty=False, active=False, path=None):
        return {'index': index, 'dirty': dirty, 'active': active,
                'path': str(self.path) if path is None else path}

    def open(self, path=None, reload=False):
        return b.call('cadcraft', 'app.open',
                      {'path': str(self.path) if path is None else str(path)},
                      state=self.state, reload_document=reload)

    def methods(self, request):
        return [(call.args[1], call.args[2]) for call in request.call_args_list]

    def test_repeated_and_canonical_paths_open_once(self):
        link = self.root / 'alias.dxf'
        link.symlink_to(self.path)
        documents = []

        def respond(app, method, params, timeout, state):
            self.assertIs(state, self.state)
            if method == 'ui.inspect':
                return {'session': {'documents': list(documents)}}
            if method == 'app.open':
                documents.append(self.doc())
                return {'opened': True}
            return {'switched': True}

        with patch.object(b, '_request', side_effect=respond) as request:
            self.assertEqual(self.open(), {'opened': True})
            for path in (self.path, self.root / 'unused' / '..' / 'seat.dxf', link):
                self.assertTrue(self.open(path)['reused'])
            methods = self.methods(request)
            self.assertEqual(sum(method == 'app.open' for method, _ in methods), 1)
            self.assertEqual(sum(method == 'engine.execute' for method, _ in methods), 3)
            self.assertEqual(len(documents), 1)

    def test_dirty_existing_tab_is_reused_without_close(self):
        inspected = {'session': {'documents': [self.doc(2, dirty=True)]}}
        with patch.object(b, '_request', side_effect=[inspected, 'switched']) as request:
            result = self.open()
            self.assertTrue(result['reused'])
            self.assertEqual(result['index'], 2)
            self.assertEqual(self.methods(request), [
                ('ui.inspect', {}),
                ('engine.execute', {'command': 'document.switch', 'params': {'index': 2}})])

    def test_concurrent_explicit_state_opens_are_serialized(self):
        documents = []
        barrier = threading.Barrier(2)

        def respond(app, method, params, timeout, state):
            if method == 'ui.inspect':
                snapshot = list(documents)
                # An unprotected second inspection would see the same empty list.
                if not snapshot:
                    time.sleep(0.05)
                return {'session': {'documents': snapshot}}
            if method == 'app.open':
                documents.append(self.doc())
                return {'opened': True}
            return {'switched': True}

        def open_together():
            barrier.wait(timeout=5)
            return self.open()

        with patch.object(b, '_request', side_effect=respond) as request:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(open_together) for _ in range(2)]
                replies = [future.result(timeout=5) for future in futures]
            methods = self.methods(request)
            self.assertEqual(len(documents), 1)
            self.assertEqual(sum(method == 'app.open' for method, _ in methods), 1)
            self.assertEqual(sum(method == 'engine.execute' for method, _ in methods), 1)
            self.assertEqual(sum(reply.get('reused') is True for reply in replies), 1)

    def test_active_matching_tab_is_preferred(self):
        inspected = {'session': {'documents': [self.doc(1, active=True), self.doc(4)]}}
        with patch.object(b, '_request', side_effect=[inspected, 'switched']):
            self.assertEqual(self.open()['index'], 1)

    def test_new_path_opens_without_closing_other_documents(self):
        inspected = {'session': {'documents': [self.doc(path=str(self.root / 'other.dxf'))]}}
        with patch.object(b, '_request', side_effect=[inspected, 'opened']) as request:
            self.assertEqual(self.open(), 'opened')
            self.assertEqual(self.methods(request), [
                ('ui.inspect', {}), ('app.open', {'path': str(self.path)})])

    def test_explicit_reload_closes_matching_saved_tabs_descending(self):
        inspected = {'session': {'documents': [
            self.doc(1), self.doc(3, path=str(self.root / 'other.dxf')), self.doc(5)]}}
        with patch.object(b, '_request', side_effect=[inspected, 'closed', 'closed', 'opened']) as request:
            self.assertEqual(self.open(reload=True), 'opened')
            self.assertEqual(self.methods(request), [
                ('ui.inspect', {}),
                ('engine.execute', {'command': 'close', 'params': {'index': 5}}),
                ('engine.execute', {'command': 'close', 'params': {'index': 1}}),
                ('app.open', {'path': str(self.path)})])

    def test_reload_refuses_dirty_or_missing_source_without_closing(self):
        for dirty, exists in ((True, True), (False, False)):
            with self.subTest(dirty=dirty, exists=exists):
                if not exists:
                    self.path.unlink()
                inspected = {'session': {'documents': [self.doc(dirty=dirty)]}}
                with patch.object(b, '_request', return_value=inspected) as request:
                    with self.assertRaises(b.BridgeError):
                        self.open(reload=True)
                    self.assertEqual(self.methods(request), [('ui.inspect', {})])

    def test_malformed_inspection_refuses_open(self):
        invalid = [None, {}, {'session': {}}, {'session': {'documents': {}}},
                   {'session': {'documents': [None]}},
                   {'session': {'documents': [{'index': True, 'dirty': False, 'path': None}]}},
                   {'session': {'documents': [{'index': -1, 'dirty': False, 'path': None}]}},
                   {'session': {'documents': [{'index': 0, 'dirty': 'false', 'path': None}]}},
                   {'session': {'documents': [{'index': 0, 'dirty': False, 'path': 123}]}},
                   {'session': {'documents': [self.doc(), self.doc()]}}]
        for inspected in invalid:
            with self.subTest(inspected=inspected), patch.object(b, '_request', return_value=inspected) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(self.methods(request), [('ui.inspect', {})])

    def test_relative_or_missing_path_refused_before_request(self):
        for path in ('seat.dxf', '', None, 12):
            with self.subTest(path=path), patch.object(b, '_request') as request:
                with self.assertRaises(b.BridgeError):
                    b.call('cadcraft', 'app.open', {'path': path}, state=self.state)
                request.assert_not_called()

    def test_other_apps_and_methods_pass_through(self):
        for app, method in (('designcraft', 'app.open'), ('cadcraft', 'ui.inspect')):
            with self.subTest(app=app, method=method), patch.object(b, '_request', return_value='reply') as request:
                params = {'path': 'unchanged'}
                self.assertEqual(b.call(app, method, params, state=self.state), 'reply')
                request.assert_called_once_with(app, method, params, 20, self.state)

    def test_reload_flag_rejected_for_other_apps_or_methods(self):
        for app, method in (('designcraft', 'app.open'), ('cadcraft', 'ui.inspect')):
            with self.subTest(app=app, method=method), patch.object(b, '_request') as request:
                with self.assertRaises(b.BridgeError):
                    b.call(app, method, state=self.state, reload_document=True)
                request.assert_not_called()

    def test_transport_failure_after_open_is_never_retried(self):
        inspected = {'session': {'documents': []}}
        error = b.BridgeError('Reply failed; operation may have completed')
        with patch.object(b, '_request', side_effect=[inspected, error]) as request:
            with self.assertRaises(b.BridgeError):
                self.open()
            self.assertEqual(self.methods(request), [
                ('ui.inspect', {}), ('app.open', {'path': str(self.path)})])


if __name__ == '__main__':
    unittest.main()
