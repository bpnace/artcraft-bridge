"""PhotoCraft document identity and safe reload regressions, without desktop apps."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from artcraft_bridge import bridge as b

class PhotoDocumentOpenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.runtime_patch = patch.object(b, 'RUNTIME', self.root / 'runtime')
        self.runtime_patch.start()
        self.path = self.root / 'photo.pcraft'
        self.path.write_text('saved test project')
        self.state = {'port': 12345}

    def tearDown(self):
        self.runtime_patch.stop()
        self.temp.cleanup()

    def doc(self, index=0, dirty=False, path=None):
        return {'index': index, 'dirty': dirty, 'path': str(self.path) if path is None else path}

    def inspected(self, docs, active=None):
        return {'session': {'documents': docs, 'active': active}}

    def open(self, path=None, reload=False):
        return b.call('photocraft', 'app.open', {'path': str(path or self.path)}, state=self.state, reload_document=reload)

    def methods(self, request):
        return [(call.args[1], call.args[2]) for call in request.call_args_list]

    def test_repeated_and_symlink_paths_activate_existing_document(self):
        link = self.root / 'linked.pcraft'
        link.symlink_to(self.path)
        docs = []
        def respond(app, method, params, timeout, state):
            self.assertEqual(app, 'photocraft')
            if method == 'ui.inspect':
                return self.inspected(list(docs), 0 if docs else None)
            if method == 'app.open':
                docs.append(self.doc())
                return {'opened': True}
            self.assertEqual(params, {'command': 'document.activate', 'params': {'document': 0}})
            return {'activated': True}
        with patch.object(b, '_request', side_effect=respond) as request:
            self.assertTrue(self.open()['opened'])
            for path in (self.path, link, self.root / 'unused' / '..' / self.path.name):
                self.assertTrue(self.open(path)['reused'])
            self.assertEqual(len(docs), 1)
            self.assertEqual(sum(method == 'app.open' for method, _ in self.methods(request)), 1)

    def test_dirty_tab_is_activated_without_closing_or_reload(self):
        with patch.object(b, '_request', side_effect=[self.inspected([self.doc(2, True)], 2), 'activated']) as request:
            self.assertEqual(self.open()['index'], 2)
            self.assertEqual(self.methods(request), [('ui.inspect', {}), ('engine.execute', {'command': 'document.activate', 'params': {'document': 2}})])

    def test_session_active_index_selects_matching_tab(self):
        with patch.object(b, '_request', side_effect=[self.inspected([self.doc(1), self.doc(3)], 1), 'activated']):
            self.assertEqual(self.open()['index'], 1)

    def test_active_other_path_chooses_last_matching_tab(self):
        docs = [self.doc(1), self.doc(2, path=str(self.root / 'other.pcraft')), self.doc(3)]
        with patch.object(b, '_request', side_effect=[self.inspected(docs, 2), 'activated']):
            self.assertEqual(self.open()['index'], 3)

    def test_new_path_preserves_other_documents(self):
        docs = [self.doc(4, True, str(self.root / 'other.pcraft'))]
        with patch.object(b, '_request', side_effect=[self.inspected(docs, 4), 'opened']) as request:
            self.assertEqual(self.open(), 'opened')
            self.assertEqual(self.methods(request), [('ui.inspect', {}), ('app.open', {'path': str(self.path)})])

    def test_reload_closes_only_matching_clean_tabs_in_descending_order(self):
        docs = [self.doc(1), self.doc(3, True, str(self.root / 'other.pcraft')), self.doc(5)]
        with patch.object(b, '_request', side_effect=[self.inspected(docs, 5), 'closed', 'closed', 'opened']) as request:
            self.assertEqual(self.open(reload=True), 'opened')
            self.assertEqual(self.methods(request), [('ui.inspect', {}), ('engine.execute', {'command': 'file.close', 'params': {'document': 5}}), ('engine.execute', {'command': 'file.close', 'params': {'document': 1}}), ('app.open', {'path': str(self.path)})])

    def test_reload_refuses_any_dirty_match_or_missing_file(self):
        for dirty, exists in ((True, True), (False, False)):
            with self.subTest(dirty=dirty, exists=exists):
                if not exists:
                    self.path.unlink()
                with patch.object(b, '_request', return_value=self.inspected([self.doc(0), self.doc(1, dirty)], 0)) as request:
                    with self.assertRaises(b.BridgeError):
                        self.open(reload=True)
                    self.assertEqual(self.methods(request), [('ui.inspect', {})])

    def test_malformed_photo_inspection_fails_closed(self):
        malformed = [None, {}, {'session': {'documents': []}}, self.inspected({}, None), self.inspected([None], None), self.inspected([self.doc(), self.doc()], 0), self.inspected([{'index': True, 'dirty': False, 'path': None}], None), self.inspected([{'index': 0, 'dirty': 'false', 'path': None}], 0), self.inspected([{'index': 0, 'dirty': False, 'path': 12}], 0), self.inspected([self.doc()], True), self.inspected([self.doc()], 3), self.inspected([], '0')]
        for inspected in malformed:
            with self.subTest(inspected=inspected), patch.object(b, '_request', return_value=inspected) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(self.methods(request), [('ui.inspect', {})])

    def test_relative_or_missing_path_rejected_before_transport(self):
        for path in ('photo.pcraft', '', None, 12):
            with self.subTest(path=path), patch.object(b, '_request') as request:
                with self.assertRaises(b.BridgeError):
                    b.call('photocraft', 'app.open', {'path': path}, state=self.state)
                request.assert_not_called()

    def test_concurrent_explicit_state_opens_create_one_document(self):
        docs = []
        barrier = threading.Barrier(2)
        def respond(app, method, params, timeout, state):
            if method == 'ui.inspect':
                snapshot = list(docs)
                if not snapshot:
                    time.sleep(0.05)
                return self.inspected(snapshot, 0 if snapshot else None)
            if method == 'app.open':
                docs.append(self.doc())
                return {'opened': True}
            return {'activated': True}
        def together():
            barrier.wait(timeout=5)
            return self.open()
        with patch.object(b, '_request', side_effect=respond) as request:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(together) for _ in range(2)]
                replies = [future.result(timeout=5) for future in futures]
            self.assertEqual(len(docs), 1)
            self.assertEqual(sum(method == 'app.open' for method, _ in self.methods(request)), 1)
            self.assertEqual(sum(reply.get('reused') is True for reply in replies), 1)
            self.assertTrue((b.RUNTIME / 'photocraft' / 'documents.lock').exists())
            self.assertFalse((b.RUNTIME / 'cadcraft' / 'documents.lock').exists())

    def test_other_methods_and_apps_pass_through(self):
        for app, method in (('photocraft', 'ui.inspect'), ('filmcraft', 'app.open'), ('effectcraft', 'engine.execute')):
            with self.subTest(app=app, method=method), patch.object(b, '_request', return_value='reply') as request:
                self.assertEqual(b.call(app, method, {'x': 1}, state=self.state), 'reply')
                request.assert_called_once_with(app, method, {'x': 1}, 20, self.state)
        with patch.object(b, '_request') as request:
            with self.assertRaises(b.BridgeError):
                b.call('photocraft', 'engine.execute', state=self.state, reload_document=True)
            request.assert_not_called()

    def test_partial_open_or_close_transport_failure_is_not_retried(self):
        scenarios = [([self.inspected([], None), b.BridgeError('may have completed')], False, 'app.open'), ([self.inspected([self.doc()], 0), b.BridgeError('may have completed')], True, 'engine.execute')]
        for replies, reload, lastmethod in scenarios:
            with self.subTest(reload=reload), patch.object(b, '_request', side_effect=replies) as request:
                with self.assertRaises(b.BridgeError):
                    self.open(reload=reload)
                self.assertEqual(len(request.call_args_list), 2)
                self.assertEqual(request.call_args_list[-1].args[1], lastmethod)

if __name__ == '__main__':
    unittest.main()
