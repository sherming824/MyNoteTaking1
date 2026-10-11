import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify, redirect, send_from_directory
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException

from src.models.user import db
from src.routes.note import note_bp
from src.routes.translation import translation_bp
from src.config import database_options


def create_app(test_config=None):
    root = os.path.dirname(os.path.dirname(__file__))
    cloud = bool(os.environ.get('VERCEL'))
    public = os.path.join(root, 'public')
    app = Flask(__name__, static_folder=None if cloud else public)
    if not cloud:
        load_dotenv(os.path.join(root, '.env'), override=False)
    database_path = os.path.join(root, 'database', 'app.db')
    raw_database_url = os.environ.get('DATABASE_URL', '').strip()
    if cloud and not raw_database_url and not test_config:
        raise RuntimeError('DATABASE_URL is required on Vercel.')
    app.config.update(
        SECRET_KEY=os.environ.get('SECRET_KEY'),
        SQLALCHEMY_DATABASE_URI=raw_database_url or f'sqlite:///{database_path}',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        MAX_CONTENT_LENGTH=1024 * 1024,
        LLM_API_URL=os.environ.get('LLM_API_URL', ''),
        LLM_API_KEY=os.environ.get('LLM_API_KEY', ''),
        LLM_MODEL=os.environ.get('LLM_MODEL', ''),
        LLM_JSON_MODE=os.environ.get('LLM_JSON_MODE', 'prompt'),
        DATABASE_INIT_URL=os.environ.get('DATABASE_INIT_URL', ''),
    )
    if test_config:
        app.config.update(test_config)
    url, engine_options, local_sqlite = database_options(
        app.config['SQLALCHEMY_DATABASE_URI'], cloud=cloud and not app.testing,
    )
    if local_sqlite and app.config['SQLALCHEMY_DATABASE_URI'] == f'sqlite:///{database_path}':
        os.makedirs(os.path.dirname(database_path), exist_ok=True)
    app.config['SQLALCHEMY_DATABASE_URI'] = url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = engine_options
    db.init_app(app)
    app.register_blueprint(note_bp, url_prefix='/api')
    app.register_blueprint(translation_bp, url_prefix='/api')
    # The unused user CRUD template is not an authentication system.
    # The frontend and API share an origin, so no CORS is needed.
    if local_sqlite:
        with app.app_context():
            db.create_all()

    @app.cli.command('init-db')
    def init_database():
        """Explicitly initialize cloud tables, rather than writing on every cold start."""
        direct = app.config['DATABASE_INIT_URL']
        if direct:
            init_url, options, _ = database_options(direct, cloud=True)
            engine = create_engine(init_url, **options)
            try:
                db.metadata.create_all(bind=engine)
            finally:
                engine.dispose()
        else:
            db.create_all()
        print('Database tables initialized.')

    @app.errorhandler(HTTPException)
    def http_error(error):
        response = error.get_response()
        response.data = app.json.dumps({'error': error.description})
        response.content_type = 'application/json'
        return response

    @app.errorhandler(SQLAlchemyError)
    def database_error(error):
        db.session.rollback()
        app.logger.exception('Database operation failed')
        return jsonify(error='Could not complete the database operation. Please try again.'), 500

    @app.route('/')
    def index():
        # In Vercel, public files are served by its CDN, outside the function.
        if cloud:
            return redirect('/index.html', code=307)
        return send_from_directory(public, 'index.html')

    if not cloud:
        @app.route('/index.html')
        def index_file():
            return send_from_directory(public, 'index.html')

        @app.route('/favicon.ico')
        def favicon():
            return send_from_directory(public, 'favicon.ico')

    return app


app = create_app()

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=os.environ.get('FLASK_DEBUG') == '1')
