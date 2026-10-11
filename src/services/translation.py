"""Translate through a configured OpenAI-compatible chat-completions endpoint."""
import json
from pathlib import Path
from urllib.parse import urlsplit

import httpx

LANGUAGES = {
    'zh-CN': 'Simplified Chinese',
    'zh-TW': 'Traditional Chinese',
    'en': 'English',
    'ja': 'Japanese',
    'ko': 'Korean',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
}
MAX_SOURCE_CHARS = 6000
PROMPT_PATH = Path(__file__).resolve().parents[2] / 'prompts' / 'translate_prompt.md'


class TranslationError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def translate(title, content, target_language, config):
    endpoint = config.get('LLM_API_URL', '').strip()
    key = config.get('LLM_API_KEY', '').strip()
    model = config.get('LLM_MODEL', '').strip()
    if not endpoint or not key or not model:
        raise TranslationError('Translation service is not configured. Please contact the app owner.', 503)
    parsed = urlsplit(endpoint)
    if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise TranslationError('The translation service URL is not configured correctly.', 503)
    prompt = PROMPT_PATH.read_text(encoding='utf-8').replace('{{TARGET_LANGUAGE}}', LANGUAGES[target_language])
    payload = {
        'model': model,
        'messages': [
            {'role': 'system', 'content': prompt},
            {'role': 'user', 'content': json.dumps({'title': title, 'content': content}, ensure_ascii=False)},
        ],
        'stream': False,
        'temperature': 0.2,
        'max_tokens': 8192,
    }
    # Some campus endpoints do not implement response_format; the prompt plus
    # server-side validation still enforces our application's response contract.
    if config.get('LLM_JSON_MODE') == 'json_object':
        payload['response_format'] = {'type': 'json_object'}
    try:
        response = httpx.post(
            endpoint, headers={'Authorization': f'Bearer {key}'}, json=payload,
            timeout=httpx.Timeout(45, connect=10), follow_redirects=False,
        )
    except httpx.TimeoutException:
        raise TranslationError('Translation timed out. Try a shorter note or retry later.', 504) from None
    except httpx.RequestError:
        raise TranslationError('Cannot reach the translation service. For the PolyU endpoint, connect to the campus network.', 503) from None
    if response.status_code in (401, 403):
        raise TranslationError('The translation service denied access. Check the configured key and campus network access.', 503)
    if response.status_code == 429:
        raise TranslationError('Translation service is busy or its quota is exhausted. Please retry later.', 429)
    if response.status_code == 402:
        raise TranslationError('Translation service credit is unavailable. Please contact the app owner.', 503)
    if not response.is_success:
        # Never return an upstream error body: it may contain internal settings.
        raise TranslationError('The translation service could not complete the request. Please retry later.')
    try:
        choice = response.json()['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise ValueError('Incomplete output')
        text = choice['message']['content'].strip()
        # Accept only a single JSON object, optionally fenced by the provider.
        if text.startswith('```json\n') and text.endswith('\n```'):
            text = text[8:-4]
        result = json.loads(text)
        if not isinstance(result, dict) or set(result) != {'title', 'content'}:
            raise ValueError('Unexpected fields')
        if not all(isinstance(result[k], str) for k in ('title', 'content')):
            raise ValueError('Expected strings')
        if len(result['title']) > 200 or len(result['content']) > 50000:
            raise ValueError('Output too long')
        if (title.strip() and not result['title'].strip()) or (content.strip() and not result['content'].strip()):
            raise ValueError('Missing translation')
        if not title.strip():
            result['title'] = ''
        if not content.strip():
            result['content'] = ''
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise TranslationError('The model returned an incomplete or invalid translation. Try again with a shorter note.') from None
    return {**result, 'target_language': target_language}
