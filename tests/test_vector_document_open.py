"""VectorCraft identity inspection and restoration regressions, without GUI apps."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from artcraft_bridge import bridge as b

class VectorDocumentOpenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.runtime_patch = patch.object(b, 'RUNTIME', self.root / 'runtime')
        self.runtime_patch.start()
        self.path = self.root / 'test.vectorcraft'
        self.path.write_text('saved vector test')
        self.state = {'port': 12345, 'workspace': str(self.root)}

    def tearDown(self):
        self.runtime_patch.stop()
        self.temp.cleanup()

    def doc(self, path=None, dirty=False, title='test.vectorcraft'):
        return {'title': title, 'dirty': dirty, 'path': str(self.path) if path is None else path}

    def open(self, path=None, alias=False, **options):
        params = dict(options, path=str(path or self.path))
        if alias:
            return b.call('vectorcraft', 'engine.execute', {'command': 'document.open', 'params': params}, state=self.state)
        return b.call('vectorcraft', 'app.open', params, state=self.state)

    def responder(self, docs, active=0, failure=None):
        state = {'active': active if docs else None}
        def respond(app, method, params, timeout, session):
            self.assertEqual(app, 'vectorcraft')
            if method == 'ui.inspect':
                return {'documents': [{'title': doc['title'], 'dirty': doc['dirty']} for doc in docs], 'activeDocument': state['active']}
            if method == 'engine.execute' and params.get('command') == 'document.activate':
                state['active'] = params['params']['index']
                return None
            if method == 'engine.execute' and params.get('command') == 'document.inspect':
                self.assertEqual(params['params'], {'depth': 0})
                if failure and state['active'] == failure[0]:
                    raise failure[1]
                return dict(docs[state['active']])
            docs.append(self.doc())
            state['active'] = len(docs)-1
            return {'opened': True}
        return respond, state

    def methods(self, request):
        return [(call.args[1], call.args[2]) for call in request.call_args_list]

    def test_active_dirty_same_path_is_reused_without_activation(self):
        respond, state = self.responder([self.doc(dirty=True)])
        with patch.object(b, '_request', side_effect=respond) as request:
            self.assertEqual(self.open()['index'], 0)
            self.assertEqual(self.methods(request), [('ui.inspect', {}), ('engine.execute', {'command': 'document.inspect', 'params': {'depth': 0}})])
            self.assertEqual(state['active'], 0)

    def test_canonical_and_symlink_reopens_create_one_document(self):
        alias = self.root / 'alias.vectorcraft'
        alias.symlink_to(self.path)
        docs = []
        respond, state = self.responder(docs)
        with patch.object(b, '_request', side_effect=respond) as request:
            self.assertTrue(self.open()['opened'])
            for path in (alias, self.path, self.root / 'unused' / '..' / 'test.vectorcraft'):
                self.assertTrue(self.open(path)['reused'])
            self.assertEqual(len(docs), 1)
            self.assertEqual(sum(method == 'app.open' for method, _ in self.methods(request)), 1)

    def test_inactive_match_is_activated_preserving_dirty_documents(self):
        docs = [self.doc(dirty=True), self.doc(path=str(self.root / 'other.vectorcraft'), dirty=True, title='other')]
        respond, state = self.responder(docs, active=1)
        with patch.object(b, '_request', side_effect=respond):
            self.assertEqual(self.open()['index'], 0)
            self.assertEqual(state['active'], 0)
            self.assertTrue(all(doc['dirty'] for doc in docs))

    def test_new_path_restores_initial_active_before_open(self):
        docs = [self.doc(path=str(self.root / 'a.vectorcraft'), title='a'), self.doc(path=str(self.root / 'b.vectorcraft'), title='b', dirty=True)]
        respond, state = self.responder(docs, active=1)
        with patch.object(b, '_request', side_effect=respond) as request:
            self.assertTrue(self.open()['opened'])
            self.assertEqual(request.call_args_list[-2].args[2], {'command': 'document.activate', 'params': {'index': 1}})
            self.assertEqual(request.call_args_list[-1].args[1], 'app.open')
            self.assertTrue(docs[1]['dirty'])

    def test_relative_saved_path_uses_managed_workspace(self):
        respond, state = self.responder([self.doc(path='test.vectorcraft')])
        with patch.object(b, '_request', side_effect=respond):
            self.assertTrue(self.open()['reused'])
        del self.state['workspace']
        with patch.object(b, '_request', side_effect=respond):
            with self.assertRaises(b.BridgeError):
                self.open()

    def test_pathless_documents_refuse_new_open_and_restore_original(self):
        docs = [self.doc(), {'title': 'Untitled', 'path': None, 'dirty': True}]
        respond, state = self.responder(docs, active=0)
        with patch.object(b, '_request', side_effect=respond) as request:
            with self.assertRaises(b.BridgeError):
                self.open(self.root / 'new.vectorcraft')
            self.assertEqual(state['active'], 0)
            self.assertNotIn('app.open', [method for method, _ in self.methods(request)])
            self.assertTrue(docs[1]['dirty'])
        respond, state = self.responder(docs, active=1)
        with patch.object(b, '_request', side_effect=respond):
            self.assertTrue(self.open()['reused'])

    def test_inspection_failure_restores_original_and_never_opens(self):
        docs = [self.doc(path=str(self.root / 'a.vectorcraft'), title='a'), self.doc(path=str(self.root / 'b.vectorcraft'), title='b')]
        original_error = b.BridgeError('inspection failed')
        respond, state = self.responder(docs, active=1, failure=(0, original_error))
        with patch.object(b, '_request', side_effect=respond) as request:
            with self.assertRaises(b.BridgeError) as raised:
                self.open()
            self.assertIs(raised.exception, original_error)
            self.assertEqual(state['active'], 1)
            self.assertNotIn('app.open', [method for method, _ in self.methods(request)])

    def test_restore_failure_does_not_mask_original_error(self):
        docs = [{'title': 'a', 'dirty': False}, {'title': 'b', 'dirty': False}]
        error = b.BridgeError('original inspection failure')
        replies = [{'documents': docs, 'activeDocument': 1}, {'title': 'b', 'dirty': False, 'path': str(self.root / 'b')}, None, error, b.BridgeError('restore failure')]
        with patch.object(b, '_request', side_effect=replies) as request:
            with self.assertRaises(b.BridgeError) as raised:
                self.open()
            self.assertIs(raised.exception, error)
            self.assertEqual(request.call_args_list[-1].args[2], {'command': 'document.activate', 'params': {'index': 1}})

    def test_failed_activation_reply_attempts_restore_without_resending_open(self):
        error = b.BridgeError('activation may have completed')
        replies = [
            {'documents': [{'title': 'a', 'dirty': False}, {'title': 'b', 'dirty': False}], 'activeDocument': 1},
            {'title': 'b', 'dirty': False, 'path': str(self.root / 'b')},
            error, None]
        with patch.object(b, '_request', side_effect=replies) as request:
            with self.assertRaises(b.BridgeError) as raised:
                self.open()
            self.assertIs(raised.exception, error)
            self.assertEqual(request.call_args_list[-1].args[2], {'command': 'document.activate', 'params': {'index': 1}})
            self.assertNotIn('app.open', [method for method, _ in self.methods(request)])

    def test_same_title_does_not_replace_full_path_identity(self):
        docs = [self.doc(path=str(self.root / 'other' / self.path.name)), self.doc(dirty=True)]
        respond, state = self.responder(docs, active=0)
        with patch.object(b, '_request', side_effect=respond):
            self.assertEqual(self.open()['index'], 1)
            self.assertEqual(state['active'], 1)
            self.assertTrue(docs[1]['dirty'])

    def test_malformed_session_or_document_identity_fails_closed(self):
        invalid = [None, {}, {'documents': [], 'activeDocument': 0}, {'documents': {}, 'activeDocument': None}, {'documents': [None], 'activeDocument': 0}, {'documents': [{'title': 'test', 'dirty': 'false'}], 'activeDocument': 0}, {'documents': [{'title': 'test', 'dirty': False}], 'activeDocument': True}]
        for inspected in invalid:
            with self.subTest(inspected=inspected), patch.object(b, '_request', return_value=inspected) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(len(request.call_args_list), 1)
        for detail in (None, {}, {'path': 123, 'title': 'test', 'dirty': False}, {'path': '', 'title': 'test', 'dirty': False}, {'path': str(self.path), 'title': 'changed', 'dirty': False}, {'path': str(self.path), 'title': 'test', 'dirty': True}):
            with self.subTest(detail=detail), patch.object(b, '_request', side_effect=[{'documents': [{'title': 'test', 'dirty': False}], 'activeDocument': 0}, detail]) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(len(request.call_args_list), 2)

    def test_document_open_alias_is_guarded_and_keeps_import_params(self):
        docs = []
        respond, state = self.responder(docs)
        with patch.object(b, '_request', side_effect=respond) as request:
            self.assertTrue(self.open(alias=True, textAs='outlines')['opened'])
            self.assertEqual(request.call_args_list[-1].args[2], {'command': 'document.open', 'params': {'path': str(self.path), 'textAs': 'outlines'}})
            self.assertTrue(self.open(alias=True)['reused'])
            self.assertEqual(len(docs), 1)
        with patch.object(b, '_request', return_value='reply') as request:
            params = {'command': 'document.open', 'params': {'name': 'fresh', 'dataBase64': 'eA=='}}
            self.assertEqual(b.call('vectorcraft', 'engine.execute', params, state=self.state), 'reply')
            request.assert_called_once_with('vectorcraft', 'engine.execute', params, 20, self.state)

    def test_invalid_paths_reload_and_transport_retry_are_refused(self):
        for path in ('relative.svg', '', None, 123):
            with self.subTest(path=path), patch.object(b, '_request') as request:
                with self.assertRaises(b.BridgeError):
                    b.call('vectorcraft', 'app.open', {'path': path}, state=self.state)
                request.assert_not_called()
        with patch.object(b, '_request') as request:
            with self.assertRaises(b.BridgeError):
                b.call('vectorcraft', 'app.open', {'path': str(self.path)}, state=self.state, reload_document=True)
            request.assert_not_called()
        with patch.object(b, '_request', side_effect=[{'documents': [], 'activeDocument': None}, b.BridgeError('may have completed')]) as request:
            with self.assertRaises(b.BridgeError):
                self.open()
            self.assertEqual(len(request.call_args_list), 2)

    def test_concurrent_explicit_state_opens_create_one_document(self):
        docs = []
        barrier = threading.Barrier(2)
        respond, state = self.responder(docs)
        def delayed(app, method, params, timeout, session):
            if method == 'ui.inspect' and not docs:
                result = respond(app, method, params, timeout, session)
                time.sleep(0.05)
                return result
            return respond(app, method, params, timeout, session)
        def together():
            barrier.wait(timeout=5)
            return self.open()
        with patch.object(b, '_request', side_effect=delayed) as request:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(together) for _ in range(2)]
                replies = [future.result(timeout=5) for future in futures]
            self.assertEqual(len(docs), 1)
            self.assertEqual(sum(method == 'app.open' for method, _ in self.methods(request)), 1)
            self.assertEqual(sum(reply.get('reused') is True for reply in replies), 1)
            self.assertTrue((b.RUNTIME / 'vectorcraft' / 'documents.lock').exists())

if __name__ == '__main__':
    unittest.main()
