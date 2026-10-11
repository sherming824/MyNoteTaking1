import json
import unittest
from unittest.mock import patch

import httpx

from src.main import create_app
from src.models.user import db
from src.services.translation import LANGUAGES


class TranslationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({
            'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'LLM_API_URL': 'https://llm.example.test/chat/completions',
            'LLM_API_KEY': 'test-secret', 'LLM_MODEL': 'test-model', 'LLM_JSON_MODE': 'prompt',
        })
        self.client = self.app.test_client()
        self.mock = patch('src.services.translation.httpx.post').start()
        self.addCleanup(patch.stopall)
        self.mock.return_value = self.response({'title': '标题', 'content': '  你好。\n\n第二段。'})

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    @staticmethod
    def response(result, finish='stop'):
        text = result if isinstance(result, str) else json.dumps(result)
        return httpx.Response(200, json={'choices': [{'finish_reason': finish, 'message': {'content': text}}]})

    def translate(self, **overrides):
        data = {'title': 'Title', 'content': 'Hello.', 'target_language': 'zh-CN'}
        data.update(overrides)
        return self.client.post('/api/translate', json=data)

    def test_preview_then_explicit_save_preserves_original(self):
        original = self.client.post('/api/notes', json={'title': 'Original', 'content': 'Hello.'}).json
        result = self.translate()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['content'], '  你好。\n\n第二段。')
        self.assertEqual(self.client.get('/api/notes').json, [original])
        saved = self.client.post('/api/notes', json=result.json)
        self.assertEqual(saved.status_code, 201)
        self.assertNotEqual(saved.json['id'], original['id'])
        self.assertEqual(self.client.get(f"/api/notes/{original['id']}").json, original)

    def test_all_languages_and_server_only_credentials(self):
        for language, name in LANGUAGES.items():
            with self.subTest(language=language):
                result = self.translate(target_language=language)
                self.assertEqual(result.status_code, 200)
                self.assertEqual(result.json['target_language'], language)
                args, kwargs = self.mock.call_args
                self.assertEqual(args[0], self.app.config['LLM_API_URL'])
                self.assertEqual(kwargs['headers']['Authorization'], 'Bearer test-secret')
                self.assertFalse(kwargs['follow_redirects'])
                self.assertIn(name, kwargs['json']['messages'][0]['content'])
                self.assertEqual(json.loads(kwargs['json']['messages'][1]['content']), {'title': 'Title', 'content': 'Hello.'})
                self.assertNotIn('response_format', kwargs['json'])
                self.assertNotIn('test-secret', result.get_data(as_text=True))

    def test_invalid_requests_do_not_call_model(self):
        invalid = [[], {}, {'title': 1}, {'content': []}, {'target_language': []},
                   {'target_language': 'unknown'}, {'title': '', 'content': '  '},
                   {'title': 'x' * 201}, {'content': 'x' * 6000}]
        for data in invalid:
            with self.subTest(data=str(data)[:100]):
                response = (self.client.post('/api/translate', json=data) if isinstance(data, list)
                            else self.translate(**data) if data else self.client.post('/api/translate', json={}))
                self.assertEqual(response.status_code, 400)
        self.mock.assert_not_called()

    def test_limit_uses_unicode_characters_and_blank_fields_stay_blank(self):
        self.assertEqual(self.translate(title='', content='😀' * 6000).status_code, 200)
        self.assertEqual(self.translate(title='', content='text').json['title'], '')
        self.assertEqual(self.translate(content='').json['content'], '')

    def test_json_mode_and_fenced_output(self):
        self.app.config['LLM_JSON_MODE'] = 'json_object'
        self.mock.return_value = self.response('```json\n{"title":"A","content":"B"}\n```')
        self.assertEqual(self.translate().status_code, 200)
        self.assertEqual(self.mock.call_args.kwargs['json']['response_format'], {'type': 'json_object'})

    def test_invalid_or_truncated_model_output_is_not_saved(self):
        outputs = ['not json', [], {'title': 'A'}, {'title': [], 'content': 'B'},
                   {'title': 'A', 'content': 'B', 'extra': 1}, {'title': '', 'content': 'B'},
                   {'title': 'A', 'content': ' '}, {'title': 'A' * 201, 'content': 'B'},
                   {'title': 'A', 'content': 'B' * 50001}]
        for output in outputs:
            self.mock.return_value = self.response(output)
            self.assertEqual(self.translate().status_code, 502)
        self.mock.return_value = self.response({'title': 'A', 'content': 'B'}, finish='length')
        self.assertEqual(self.translate().status_code, 502)
        self.mock.return_value = httpx.Response(200, json={'choices': []})
        self.assertEqual(self.translate().status_code, 502)
        self.assertEqual(self.client.get('/api/notes').json, [])

    def test_upstream_failures_are_sanitized(self):
        for upstream, expected in [(401, 503), (403, 503), (429, 429), (402, 503), (500, 502), (302, 502)]:
            with self.subTest(upstream=upstream):
                self.mock.return_value = httpx.Response(upstream, text='PRIVATE provider credentials')
                response = self.translate()
                self.assertEqual(response.status_code, expected)
                self.assertNotIn('PRIVATE', response.get_data(as_text=True))

    def test_network_timeout_and_connection_failure(self):
        for error, expected in [(httpx.ReadTimeout('secret'), 504), (httpx.ConnectError('secret'), 503)]:
            self.mock.side_effect = error
            response = self.translate()
            self.assertEqual(response.status_code, expected)
            self.assertNotIn('secret', response.get_data(as_text=True))

    def test_missing_configuration_does_not_call_model(self):
        self.app.config['LLM_API_KEY'] = ''
        self.assertEqual(self.translate().status_code, 503)
        self.mock.assert_not_called()

    def test_plaintext_endpoint_is_rejected(self):
        self.app.config['LLM_API_URL'] = 'http://llm.example.test/'
        self.assertEqual(self.translate().status_code, 503)
        self.mock.assert_not_called()


if __name__ == '__main__':
    unittest.main()
