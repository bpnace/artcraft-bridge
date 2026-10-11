"""PdfCraft safe identity-based open and tab activation regressions."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from artcraft_bridge import bridge as b

class PdfDocumentOpenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.runtime_patch = patch.object(b, 'RUNTIME', self.root / 'runtime')
        self.runtime_patch.start()
        self.path = self.root / 'test.pdf'
        self.path.write_text('saved test pdf')
        self.state = {'port': 12345}

    def tearDown(self):
        self.runtime_patch.stop()
        self.temp.cleanup()

    def doc(self, tab=0, doc=12, active=True, dirty=False, path=None, name='test.pdf'):
        return {'tab': tab, 'doc': doc, 'active': active, 'dirty': dirty, 'path': str(self.path) if path is None else path, 'name': name}

    def inspected(self, docs):
        return {'documents': docs}

    def widget(self, **changes):
        return dict({'clickable': True, 'enabled': True, 'id': 'tab-button', 'label': 'test.pdf', 'rect': [2, 2, 102, 32], 'role': 'Button', 'toggled': 'false'}, **changes)

    def widgets(self, *widgets):
        return {'widgets': list(widgets), 'count': len(widgets), 'truncated': False}

    def open(self, path=None, reload=False):
        return b.call('pdfcraft', 'ui.open', {'path': str(path or self.path)}, state=self.state, reload_document=reload)

    def methods(self, request):
        return [(call.args[1], call.args[2]) for call in request.call_args_list]

    def test_active_same_path_preserves_dirty_tab_without_mutation(self):
        with patch.object(b, '_request', return_value=self.inspected([self.doc(dirty=True)])) as request:
            result = self.open()
            self.assertTrue(result['reused'])
            self.assertEqual(result['doc'], 12)
            self.assertEqual(self.methods(request), [('ui.state', {})])

    def test_canonical_new_and_repeated_paths_open_once(self):
        alias = self.root / 'alias.pdf'
        alias.symlink_to(self.path)
        docs = []
        def respond(app, method, params, timeout, state):
            self.assertEqual(app, 'pdfcraft')
            if method == 'ui.state':
                return self.inspected(list(docs))
            self.assertEqual(method, 'ui.open')
            self.assertEqual(params, {'path': str(self.path)})
            docs.append(self.doc())
            return {'opened': True}
        with patch.object(b, '_request', side_effect=respond) as request:
            self.assertTrue(self.open(alias)['opened'])
            for path in (self.path, alias, self.root / 'unused' / '..' / 'test.pdf'):
                self.assertTrue(self.open(path)['reused'])
            self.assertEqual(len(docs), 1)
            self.assertEqual(sum(method == 'ui.open' for method, _ in self.methods(request)), 1)

    def test_inactive_named_button_activates_and_verifies_doc_identity(self):
        before = self.inspected([self.doc(active=False), self.doc(1, 13, path=str(self.root / 'other.pdf'), name='other.pdf')])
        after = self.inspected([self.doc(dirty=True), self.doc(1, 13, active=False, path=str(self.root / 'other.pdf'), name='other.pdf')])
        with patch.object(b, '_request', side_effect=[before, self.widgets(self.widget()), {'clicked': True}, after]) as request:
            self.assertEqual(self.open()['doc'], 12)
            self.assertEqual(self.methods(request), [('ui.state', {}), ('ui.inspect', {'query': 'test.pdf', 'limit': 512}), ('ui.click', {'id': 'tab-button'}), ('ui.state', {})])

    def test_ambiguous_paths_or_names_refused_without_click_or_open(self):
        cases = [[self.doc(active=False), self.doc(1, 13, active=False)],
                 [self.doc(active=False), self.doc(1, 13, path=str(self.root / 'other.pdf'))]]
        for docs in cases:
            with self.subTest(docs=docs), patch.object(b, '_request', return_value=self.inspected(docs)) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(self.methods(request), [('ui.state', {})])

    def test_active_match_can_reuse_even_with_existing_clean_duplicate(self):
        docs = [self.doc(active=False), self.doc(1, 13, dirty=True)]
        with patch.object(b, '_request', return_value=self.inspected(docs)) as request:
            self.assertEqual(self.open()['doc'], 13)
            self.assertEqual(self.methods(request), [('ui.state', {})])

    def test_unsafe_or_ambiguous_widgets_fail_before_click(self):
        invalid = [None, {}, self.widgets(), self.widgets(self.widget(), self.widget(id='another')),
                   dict(self.widgets(self.widget()), truncated=True),
                   dict(self.widgets(self.widget()), count=3),
                   self.widgets(self.widget(enabled=False)), self.widgets(self.widget(clickable=False)),
                   self.widgets(self.widget(toggled='true')), self.widgets(self.widget(id=123)),
                   self.widgets(self.widget(rect=[2, 2, 1, 3])), self.widgets(self.widget(role='Label'))]
        for widgets in invalid:
            with self.subTest(widgets=widgets), patch.object(b, '_request', side_effect=[self.inspected([self.doc(active=False)]), widgets]) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(len(request.call_args_list), 2)

    def test_activation_must_verify_original_doc_and_path(self):
        wrong = [self.inspected([self.doc(active=False)]), self.inspected([self.doc(doc=99)]), self.inspected([self.doc(path=str(self.root / 'other.pdf'))])]
        for after in wrong:
            with self.subTest(after=after), patch.object(b, '_request', side_effect=[self.inspected([self.doc(active=False)]), self.widgets(self.widget()), {}, after]) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(sum(method == 'ui.click' for method, _ in self.methods(request)), 1)
                self.assertNotIn('ui.open', [method for method, _ in self.methods(request)])

    def test_invalid_documents_fail_closed(self):
        bad_docs = [None, {}, {'documents': {}}, self.inspected([None]), self.inspected([self.doc(), self.doc()]), self.inspected([self.doc(tab=True)]), self.inspected([self.doc(doc=-1)]), self.inspected([self.doc(active='true')]), self.inspected([self.doc(dirty='false')]), self.inspected([self.doc(path=1)]), self.inspected([self.doc(name=None)]), self.inspected([self.doc(), self.doc(1,13)])]
        for inspected in bad_docs:
            with self.subTest(inspected=inspected), patch.object(b, '_request', return_value=inspected) as request:
                with self.assertRaises(b.BridgeError):
                    self.open()
                self.assertEqual(self.methods(request), [('ui.state', {})])

    def test_missing_relative_paths_and_reload_refused_before_transport(self):
        for path in (None, '', 'test.pdf', 123):
            with self.subTest(path=path), patch.object(b, '_request') as request:
                with self.assertRaises(b.BridgeError):
                    b.call('pdfcraft', 'ui.open', {'path': path}, state=self.state)
                request.assert_not_called()
        with patch.object(b, '_request') as request:
            with self.assertRaises(b.BridgeError):
                self.open(reload=True)
            request.assert_not_called()

    def test_transport_failure_is_never_retried(self):
        with patch.object(b, '_request', side_effect=[self.inspected([]), b.BridgeError('may have completed')]) as request:
            with self.assertRaises(b.BridgeError):
                self.open()
            self.assertEqual(self.methods(request), [('ui.state', {}), ('ui.open', {'path': str(self.path)})])
        with patch.object(b, '_request', side_effect=[self.inspected([self.doc(active=False)]), self.widgets(self.widget()), b.BridgeError('may have completed')]) as request:
            with self.assertRaises(b.BridgeError):
                self.open()
            self.assertEqual(len(request.call_args_list), 3)

    def test_concurrent_explicit_state_opens_create_one_document(self):
        docs = []
        barrier = threading.Barrier(2)
        def respond(app, method, params, timeout, state):
            if method == 'ui.state':
                snapshot = list(docs)
                if not snapshot:
                    time.sleep(0.05)
                return self.inspected(snapshot)
            docs.append(self.doc())
            return {'opened': True}
        def together():
            barrier.wait(timeout=5)
            return self.open()
        with patch.object(b, '_request', side_effect=respond) as request:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(together) for _ in range(2)]
                replies = [future.result(timeout=5) for future in futures]
            self.assertEqual(len(docs), 1)
            self.assertEqual(sum(method == 'ui.open' for method, _ in self.methods(request)), 1)
            self.assertEqual(sum(reply.get('reused') is True for reply in replies), 1)
            self.assertTrue((b.RUNTIME / 'pdfcraft' / 'documents.lock').exists())

    def test_other_pdf_methods_pass_through(self):
        with patch.object(b, '_request', return_value='reply') as request:
            self.assertEqual(b.call('pdfcraft', 'ui.state', {}, state=self.state), 'reply')
            request.assert_called_once_with('pdfcraft', 'ui.state', {}, 20, self.state)

if __name__ == '__main__':
    unittest.main()
