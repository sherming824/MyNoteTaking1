const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const html = fs.readFileSync(path.join(__dirname, '../public/index.html'), 'utf8');
const source = html.slice(html.indexOf('class NoteTaker {'), html.indexOf('// Initialize the app'));
const note = (id, title, content) => ({id, title, content, updated_at: '2026-10-11T01:00:00'});

function setup() {
    const elements = new Map();
    const element = () => ({value: '', textContent: '', innerHTML: '', style: {}, disabled: false,
        events: {}, focus() {}, addEventListener(name, fn) {this.events[name] = fn;},
        replaceChildren(...children) {this.children = children;}});
    const document = {getElementById(id) {
        if (!elements.has(id)) elements.set(id, element());
        return elements.get(id);
    }, createElement: element};
    const events = {};
    const timers = new Map();
    let timerId = 0;
    const context = vm.createContext({document, window: {addEventListener(name, fn) {events[name] = fn;}},
        confirm: () => true, AbortController,
        setTimeout(fn) {timers.set(++timerId, fn); return timerId;},
        clearTimeout(id) {timers.delete(id);}});
    vm.runInContext(source + '; this.NoteTaker = NoteTaker;', context);
    context.NoteTaker.prototype.init = function () {this.bindEvents();};
    const app = new context.NoteTaker();
    app.notes = [note(1, 'A', 'original A'), note(2, 'B', 'original B')];
    app.currentNote = app.notes[0];
    document.getElementById('noteTitle').value = 'A';
    document.getElementById('noteContent').value = 'original A';
    document.getElementById('targetLanguage').value = 'zh-CN';
    return {app, document, events, timers};
}

test('switch saves the previous note before selecting another', async () => {
    const {app, document} = setup();
    document.getElementById('noteContent').value = 'edited A';
    let called = false;
    app.request = async (url, options) => {
        assert.equal(url, '/api/notes/1');
        assert.equal(JSON.parse(options.body).content, 'edited A');
        called = true;
        return note(1, 'A', 'edited A');
    };
    await app.selectNote(2);
    assert.ok(called);
    assert.equal(app.currentNote.id, 2);
    assert.equal(app.notes.find(n => n.id === 1).content, 'edited A');
    assert.equal(document.getElementById('noteContent').value, 'original B');
});

test('failed save keeps edits and prevents switching or creating a new note', async () => {
    const {app, document} = setup();
    document.getElementById('noteContent').value = 'unsaved';
    app.request = async () => {throw new Error('offline');};
    await app.selectNote(2);
    await app.createNewNote();
    assert.equal(app.currentNote.id, 1);
    assert.equal(document.getElementById('noteContent').value, 'unsaved');
    assert.equal(app.busy, false);
});

test('pending save locks edits and rejects duplicate saves and switches', async () => {
    const {app, document} = setup();
    let finish;
    let requests = 0;
    app.request = () => {requests++; return new Promise(resolve => {finish = resolve;});};
    const pending = app.saveNote();
    assert.equal(document.getElementById('noteContent').disabled, true);
    await app.saveNote();
    await app.selectNote(2);
    await app.createNewNote();
    assert.equal(requests, 1);
    assert.equal(app.currentNote.id, 1);
    finish(note(1, 'A', 'original A'));
    await pending;
    assert.equal(document.getElementById('noteContent').disabled, false);
});

test('unsaved draft is saved before switching and delete is hidden until saved', async () => {
    const {app, document} = setup();
    await app.createNewNote();
    assert.equal(document.getElementById('deleteBtn').style.display, 'none');
    document.getElementById('noteContent').value = 'draft';
    app.request = async () => note(3, 'Untitled', 'draft');
    await app.selectNote(2);
    assert.equal(app.notes.find(n => n.id === 3).content, 'draft');
    assert.equal(app.currentNote.id, 2);
    assert.equal(document.getElementById('deleteBtn').style.display, '');
});

test('selecting the same note does not erase unsaved edits', async () => {
    const {app, document} = setup();
    document.getElementById('noteContent').value = 'unsaved';
    await app.selectNote(1);
    assert.equal(document.getElementById('noteContent').value, 'unsaved');
});

test('active search survives list rerenders', () => {
    const {app, document} = setup();
    document.getElementById('searchBox').value = '  no match  ';
    app.renderNotesList();
    assert.match(document.getElementById('notesList').innerHTML, /No notes found/);
    app.showEditor();
    app.renderNotesList();
    assert.match(document.getElementById('notesList').innerHTML, /No notes found/);
});

test('delete cancels pending autosave and removes only the requested note', async () => {
    const {app, document, timers} = setup();
    document.getElementById('noteContent').events.input();
    const timer = app.saveTimeout;
    assert.ok(timers.has(timer));
    app.request = async (url, options) => {
        assert.equal(url, '/api/notes/1'); assert.equal(options.method, 'DELETE'); return null;
    };
    await app.deleteNote();
    assert.equal(timers.has(timer), false);
    assert.equal(app.notes.length, 1);
    assert.equal(app.notes[0].id, 2);
    assert.equal(app.currentNote, null);
});

test('page unload warns for unsaved changes', () => {
    const {document, events} = setup();
    document.getElementById('noteContent').value = 'unsaved';
    let prevented = false;
    events.beforeunload({preventDefault() {prevented = true;}});
    assert.ok(prevented);
});

test('server errors are displayed as text', () => {
    const {app, document} = setup();
    app.showMessage('<img src=x onerror=alert(1)>', 'error');
    const message = document.getElementById('messageArea').children[0];
    assert.equal(message.textContent, '<img src=x onerror=alert(1)>');
    assert.equal(message.innerHTML, '');
});

const translated = {title: '译文标题', content: '翻译后的正文', target_language: 'zh-CN'};

test('translation previews current unsaved text without saving or replacing the original', async () => {
    const {app, document} = setup();
    document.getElementById('noteContent').value = 'unsaved source';
    app.request = async (url, options, timeout) => {
        assert.equal(url, '/api/translate');
        assert.equal(JSON.parse(options.body).content, 'unsaved source');
        assert.equal(timeout, 60000);
        return translated;
    };
    await app.translateNote();
    assert.equal(document.getElementById('translatedContent').value, translated.content);
    assert.equal(document.getElementById('noteContent').value, 'unsaved source');
    assert.equal(app.currentNote.content, 'original A');
    assert.equal(app.notes.length, 2);
    assert.equal(document.getElementById('saveTranslationBtn').disabled, false);
});

test('saving a preview creates one new note and preserves the unsaved original editor', async () => {
    const {app, document} = setup();
    document.getElementById('noteContent').value = 'unsaved source';
    app.request = async () => translated;
    await app.translateNote();
    let finish;
    let calls = 0;
    app.request = (url, options) => {
        calls++;
        assert.equal(url, '/api/notes');
        assert.equal(options.method, 'POST');
        assert.deepEqual(JSON.parse(options.body), {title: translated.title, content: translated.content});
        return new Promise(resolve => {finish = resolve;});
    };
    const pending = app.saveTranslation();
    await app.saveTranslation();
    finish(note(3, translated.title, translated.content));
    await pending;
    await app.saveTranslation();
    assert.equal(calls, 1);
    assert.equal(app.notes.length, 3);
    assert.equal(app.currentNote.id, 1);
    assert.equal(document.getElementById('noteContent').value, 'unsaved source');
    assert.ok(app.hasUnsavedChanges());
    assert.equal(document.getElementById('saveTranslationBtn').disabled, true);
});

test('source edits and language changes prevent saving a stale translation', async () => {
    for (const [id, value, event] of [['noteContent', 'changed', 'input'], ['targetLanguage', 'ja', 'change']]) {
        const {app, document} = setup();
        app.request = async () => translated;
        await app.translateNote();
        document.getElementById(id).value = value;
        document.getElementById(id).events[event]();
        app.request = () => assert.fail('A stale preview must not be saved');
        await app.saveTranslation();
        assert.equal(document.getElementById('saveTranslationBtn').disabled, true);
        assert.match(document.getElementById('translationStatus').textContent, /changed/);
    }
});

test('duplicate translation clicks issue only one request and edits during it invalidate the result', async () => {
    const {app, document} = setup();
    let finish;
    let calls = 0;
    app.request = () => {calls++; return new Promise(resolve => {finish = resolve;});};
    const pending = app.translateNote();
    await app.translateNote();
    document.getElementById('noteContent').value = 'changed while pending';
    finish(translated);
    await pending;
    assert.equal(calls, 1);
    assert.equal(document.getElementById('saveTranslationBtn').disabled, true);
    assert.equal(app.isTranslating, false);
});

test('switching notes discards a late translation response', async () => {
    const {app, document} = setup();
    let finish;
    app.request = () => new Promise(resolve => {finish = resolve;});
    const pending = app.translateNote();
    await app.selectNote(2);
    finish(translated);
    await pending;
    assert.equal(app.currentNote.id, 2);
    assert.equal(app.translation, null);
    assert.equal(document.getElementById('translationPreview').style.display, 'none');
});

test('a failed preview or failed save keeps the source and supports retry', async () => {
    const {app, document} = setup();
    app.request = async () => {throw new Error('Campus network unavailable');};
    await app.translateNote();
    assert.equal(document.getElementById('noteContent').value, 'original A');
    assert.equal(app.isTranslating, false);
    assert.match(document.getElementById('translationStatus').textContent, /Campus network/);
    app.request = async () => translated;
    await app.translateNote();
    app.request = async () => {throw new Error('Database unavailable');};
    await app.saveTranslation();
    assert.equal(app.translation.content, translated.content);
    assert.equal(app.translationSaved, false);
    assert.equal(document.getElementById('saveTranslationBtn').disabled, false);
    assert.equal(app.notes.length, 2);
});

test('empty or oversized source is rejected before sending a translation request', async () => {
    const {app, document} = setup();
    app.request = () => assert.fail('Invalid source must not be sent');
    document.getElementById('noteTitle').value = '';
    document.getElementById('noteContent').value = ' ';
    await app.translateNote();
    document.getElementById('noteContent').value = '😀'.repeat(6001);
    await app.translateNote();
    assert.equal(app.translation, null);
});

test('translation saving reschedules autosave of an edited existing original', async () => {
    const {app, document, timers} = setup();
    document.getElementById('noteContent').value = 'edited original';
    document.getElementById('noteContent').events.input();
    app.request = async () => translated;
    await app.translateNote();
    let finish;
    app.request = () => new Promise(resolve => {finish = resolve;});
    const pending = app.saveTranslation();
    timers.get(app.saveTimeout)(); // The timer fires while another write is pending.
    finish(note(3, translated.title, translated.content));
    await pending;
    app.request = async (url, options) => {
        assert.equal(url, '/api/notes/1');
        assert.equal(JSON.parse(options.body).content, 'edited original');
        return note(1, 'A', 'edited original');
    };
    await timers.get(app.saveTimeout)();
    assert.equal(app.currentNote.content, 'edited original');
});
