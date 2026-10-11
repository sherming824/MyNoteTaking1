import os
import unittest
from unittest.mock import patch

from sqlalchemy.pool import NullPool

from src.config import database_options
from src.main import create_app
from src.models.user import db


class DatabaseConfigTests(unittest.TestCase):
    def test_neon_driver_ssl_and_pooler_configuration(self):
        for prefix in ['postgres', 'postgresql', 'postgresql+psycopg']:
            url, options, local = database_options(f'{prefix}://user:secret@db.example.test/db?sslmode=disable', cloud=True)
            self.assertEqual(url.drivername, 'postgresql+psycopg')
            self.assertEqual(url.query['sslmode'], 'require')
            self.assertIs(options['poolclass'], NullPool)
            self.assertFalse(local)
        url, _, _ = database_options('postgresql://user:secret@db.example.test/db?sslmode=verify-full&channel_binding=require')
        self.assertEqual(url.query['sslmode'], 'verify-full')
        self.assertEqual(url.query['channel_binding'], 'require')

    def test_local_sqlite_only(self):
        self.assertTrue(database_options('sqlite://')[2])
        with self.assertRaises(RuntimeError):
            database_options('sqlite://', cloud=True)

    def test_invalid_url_has_no_credentials_in_error(self):
        with self.assertRaisesRegex(RuntimeError, '^DATABASE_URL is invalid.$'):
            database_options('PRIVATE malformed credentials')

    def test_vercel_requires_external_database_without_filesystem_write(self):
        with patch.dict(os.environ, {'VERCEL': '1', 'DATABASE_URL': ''}), patch('src.main.os.makedirs') as mkdir:
            with self.assertRaisesRegex(RuntimeError, 'DATABASE_URL is required'):
                create_app()
            mkdir.assert_not_called()

    def test_cloud_startup_does_not_connect_or_create_tables(self):
        with patch.dict(os.environ, {'VERCEL': '1', 'DATABASE_URL': 'postgresql://user:secret@db.example.test/db'}):
            with patch.object(db, 'create_all') as create_tables:
                app = create_app()
                self.assertEqual(app.config['SQLALCHEMY_DATABASE_URI'].drivername, 'postgresql+psycopg')
                create_tables.assert_not_called()
                self.assertIsNone(app.static_folder)
                response = app.test_client().get('/')
                self.assertEqual(response.status_code, 307)
                self.assertEqual(response.location, '/index.html')
                with app.app_context():
                    db.engine.dispose()


if __name__ == '__main__':
    unittest.main()
