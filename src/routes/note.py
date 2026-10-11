from flask import Blueprint, abort, jsonify, request
from src.models.note import Note, db

note_bp = Blueprint('note', __name__)


def read_note_data(existing=None):
    data = request.get_json()
    if not isinstance(data, dict):
        abort(400, description='A JSON object is required.')
    if existing is None and not {'title', 'content'} <= data.keys():
        abort(400, description='Title and content are required.')
    if not {'title', 'content'} & data.keys():
        abort(400, description='Provide a title or content to update.')
    title = data.get('title', existing.title if existing else '')
    content = data.get('content', existing.content if existing else '')
    if not isinstance(title, str) or not isinstance(content, str):
        abort(400, description='Title and content must be strings.')
    title = title.strip()
    if len(title) > 200:
        abort(400, description='Title must be at most 200 characters.')
    if not title and not content.strip():
        abort(400, description='Please enter a title or content.')
    return title or 'Untitled', content


@note_bp.route('/notes', methods=['GET'])
def get_notes():
    notes = Note.query.order_by(Note.updated_at.desc(), Note.id.desc()).all()
    return jsonify([note.to_dict() for note in notes])


@note_bp.route('/notes', methods=['POST'])
def create_note():
    title, content = read_note_data()
    note = Note(title=title, content=content)
    db.session.add(note)
    db.session.commit()
    return jsonify(note.to_dict()), 201


@note_bp.route('/notes/<int:note_id>', methods=['GET'])
def get_note(note_id):
    return jsonify(db.get_or_404(Note, note_id).to_dict())


@note_bp.route('/notes/<int:note_id>', methods=['PUT'])
def update_note(note_id):
    note = db.get_or_404(Note, note_id)
    note.title, note.content = read_note_data(note)
    db.session.commit()
    return jsonify(note.to_dict())


@note_bp.route('/notes/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    note = db.get_or_404(Note, note_id)
    db.session.delete(note)
    db.session.commit()
    return '', 204


@note_bp.route('/notes/search', methods=['GET'])
def search_notes():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])
    notes = Note.query.filter(
        Note.title.contains(query, autoescape=True) | Note.content.contains(query, autoescape=True)
    ).order_by(Note.updated_at.desc(), Note.id.desc()).all()
    return jsonify([note.to_dict() for note in notes])
