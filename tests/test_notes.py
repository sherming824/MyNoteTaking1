import unittest
from unittest.mock import patch

from sqlalchemy.exc import OperationalError

from src.main import create_app
from src.models.user import db


class NotesTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app({'TESTING': True, 'SQLALCHEMY_DATABASE_URI': 'sqlite://'})
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
            db.engine.dispose()

    def create_note(self, title='Test note', content='Original content'):
        response = self.client.post('/api/notes', json={'title': title, 'content': content})
        self.assertEqual(response.status_code, 201)
        return response.json

    def test_crud_and_search(self):
        note = self.create_note()
        url = f"/api/notes/{note['id']}"
        self.assertEqual(self.client.get(url).json['content'], 'Original content')
        self.assertEqual(self.client.put(url, json={'content': 'Updated body'}).status_code, 200)
        results = self.client.get('/api/notes/search?q=Updated').json
        self.assertEqual([r['id'] for r in results], [note['id']])
        self.assertEqual(self.client.get('/api/notes/search?q=Test').json[0]['id'], note['id'])
        self.assertEqual(self.client.delete(url).status_code, 204)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get('/api/notes').json, [])

    def test_missing_notes_return_json_404(self):
        for method in ['get', 'put', 'delete']:
            with self.subTest(method=method):
                response = getattr(self.client, method)('/api/notes/99999', json={'title': 'x'})
                self.assertEqual(response.status_code, 404)
                self.assertIn('error', response.json)

    def test_invalid_payloads_return_400_without_inserting(self):
        for data in [[], ['title', 'content'], 123, {}, {'title': 'x'},
                     {'title': None, 'content': 'x'}, {'title': [], 'content': 'x'},
                     {'title': 'x', 'content': {}}, {'title': ' ', 'content': '\n'},
                     {'title': 'x'*201, 'content': 'x'}]:
            with self.subTest(data=data):
                response = self.client.post('/api/notes', json=data)
                self.assertEqual(response.status_code, 400)
                self.assertIn('error', response.json)
        self.assertEqual(self.client.get('/api/notes').json, [])

    def test_invalid_update_preserves_original(self):
        note = self.create_note()
        url = f"/api/notes/{note['id']}"
        for data in [{'title': None}, {'content': []}, {'title': 'x'*201}, {'other': 'x'}]:
            self.assertEqual(self.client.put(url, json=data).status_code, 400)
        self.assertEqual(self.client.get(url).json['title'], note['title'])
        self.assertEqual(self.client.get(url).json['content'], note['content'])

    def test_malformed_json_and_wrong_content_type(self):
        for data, content_type, expected in [('{', 'application/json', 400),
                                            ('null', 'application/json', 400),
                                            ('x', 'text/plain', 415)]:
            response = self.client.post('/api/notes', data=data, content_type=content_type)
            self.assertEqual(response.status_code, expected)
            self.assertIn('error', response.json)

    def test_size_limit(self):
        response = self.client.post('/api/notes', json={'title': 'x', 'content': 'x'*1048576})
        self.assertEqual(response.status_code, 413)

    def test_title_boundary_and_content_formatting(self):
        body = '  indented\n\nlast line\n'
        note = self.create_note('x'*200, body)
        self.assertEqual(note['content'], body)
        self.assertEqual(self.create_note('', 'body')['title'], 'Untitled')

    def test_search_treats_wildcards_as_text(self):
        self.create_note('Ordinary', 'plain')
        note = self.create_note('100%_done', 'literal marker')
        self.assertEqual([n['id'] for n in self.client.get('/api/notes/search?q=%25_').json], [note['id']])
        self.assertEqual(self.client.get('/api/notes/search?q=%20%20').json, [])

    def test_database_errors_are_sanitized_and_rolled_back(self):
        with patch.object(db.session, 'commit', side_effect=OperationalError('PRIVATE SQL', {}, Exception('PRIVATE SECRET'))):
            with self.assertLogs(self.app.logger.name, level='ERROR'):
                response = self.client.post('/api/notes', json={'title': 'Failed', 'content': 'body'})
        self.assertEqual(response.status_code, 500)
        self.assertNotIn('PRIVATE', response.get_data(as_text=True))
        self.assertEqual(self.client.get('/api/notes').json, [])
        self.create_note()

    def test_routes_and_default_configuration(self):
        with self.client.get('/') as response:
            self.assertEqual(response.status_code, 200)
        with self.client.get('/index.html') as response:
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'translateBtn', response.data)
        with self.client.get('/favicon.ico') as response:
            self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get('/.env').status_code, 404)
        for path in ['/api/missing', '/api/users', '/does-not-exist']:
            self.assertEqual(self.client.get(path).status_code, 404)
        response = self.client.get('/api/notes', headers={'Origin': 'https://unrelated.example'})
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)
        self.assertFalse(self.app.debug)


if __name__ == '__main__':
    unittest.main()
