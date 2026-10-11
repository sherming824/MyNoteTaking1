from flask import Blueprint, abort, current_app, jsonify, request

from src.services.translation import LANGUAGES, MAX_SOURCE_CHARS, TranslationError, translate

translation_bp = Blueprint('translation', __name__)


@translation_bp.route('/translate', methods=['POST'])
def translate_note():
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, description='A JSON object is required.')
    title = data.get('title', '')
    content = data.get('content', '')
    target = data.get('target_language')
    if not isinstance(title, str) or not isinstance(content, str):
        abort(400, description='Title and content must be strings.')
    if not isinstance(target, str) or target not in LANGUAGES:
        abort(400, description='Choose a supported target language.')
    if not title.strip() and not content.strip():
        abort(400, description='Enter a title or content to translate.')
    if len(title) > 200 or len(title) + len(content) > MAX_SOURCE_CHARS:
        abort(400, description=f'Translate up to {MAX_SOURCE_CHARS} characters at a time, with a title of at most 200 characters.')
    try:
        result = translate(title, content, target, current_app.config)
    except TranslationError as error:
        return jsonify(error=str(error)), error.status
    # A preview has no database side effects. Saving is a separate notes POST.
    return jsonify(result)
