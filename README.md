# NoteTaker - Personal Note Management Application

A modern, responsive web application for managing personal notes with a beautiful user interface and full CRUD functionality.

## 🌟 Features

- **Create Notes**: Add new notes with titles and rich content
- **Edit Notes**: Update existing notes with real-time editing
- **Delete Notes**: Remove notes you no longer need
- **Search Notes**: Find notes quickly by searching titles and content
- **Auto-save**: Notes are automatically saved as you type
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **Modern UI**: Beautiful gradient design with smooth animations
- **Real-time Updates**: Instant feedback and updates
- **Translate Notes**: Preview translations of the title and content in eight languages,
  then explicitly save the result as a new note without replacing the original.

See [translation and Neon setup](docs/translation-setup.md) for the current configuration,
campus-network restriction, and verification steps.

## 🚀 Live Demo

The application is deployed and accessible at: **https://3dhkilc88dkk.manus.space**

## 🛠 Technology Stack

### Frontend
- **HTML5**: Semantic markup structure
- **CSS3**: Modern styling with gradients, animations, and responsive design
- **JavaScript (ES6+)**: Interactive functionality and API communication

### Backend
- **Python Flask**: Web framework for API endpoints
- **SQLAlchemy**: ORM for database operations
- **Same-origin API**: The frontend and backend use the same origin

### Database
- **SQLite**: Lightweight, file-based database for data persistence

## 📁 Project Structure

```
notetaking-app/
├── src/
│   ├── models/
│   │   ├── user.py          # User model (template)
│   │   └── note.py          # Note model with database schema
│   ├── routes/
│   │   ├── user.py          # User API routes (template)
│   │   └── note.py          # Note API endpoints
│   └── main.py              # Flask application entry point
├── public/
│   ├── index.html           # Frontend, served by the Vercel CDN
│   └── favicon.ico
├── database/
│   └── app.db               # Local SQLite database (ignored by Git)
├── tests/                   # Backend and frontend regression tests
├── venv/                    # Python virtual environment
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

## 🔧 Local Development Setup

### Prerequisites
- Python 3.11+
- pip (Python package manager)

### Installation Steps

1. **Clone or download the project**
   ```bash
   python -m venv venv
   ```

2. **Activate the virtual environment**
   ```bash
   source venv/bin/activate
   ```

   Remark: On Windows, use `venv\Scripts\activate`

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the application**
   ```bash
   python src/main.py
   ```

5. **Access the application**
   - Open your browser and go to `http://localhost:5001`

## 📡 API Endpoints

### Notes API
- `GET /api/notes` - Get all notes
- `POST /api/notes` - Create a new note
- `GET /api/notes/<id>` - Get a specific note
- `PUT /api/notes/<id>` - Update a note
- `DELETE /api/notes/<id>` - Delete a note
- `GET /api/notes/search?q=<query>` - Search notes

### Request/Response Format
```json
{
  "id": 1,
  "title": "My Note Title",
  "content": "Note content here...",
  "created_at": "2025-09-03T11:26:38.123456",
  "updated_at": "2025-09-03T11:27:30.654321"
}
```

## 🎨 User Interface Features

### Sidebar
- **Search Box**: Real-time search through note titles and content
- **New Note Button**: Create new notes instantly
- **Notes List**: Scrollable list of all notes with previews
- **Note Previews**: Show title, content preview, and last modified date

### Editor Panel
- **Title Input**: Edit note titles
- **Content Textarea**: Rich text editing area
- **Save Button**: Manual save option (auto-save also available)
- **Delete Button**: Remove notes with confirmation
- **Real-time Updates**: Changes reflected immediately

### Design Elements
- **Gradient Background**: Beautiful purple gradient backdrop
- **Glass Morphism**: Semi-transparent panels with backdrop blur
- **Smooth Animations**: Hover effects and transitions
- **Responsive Layout**: Adapts to different screen sizes
- **Modern Typography**: Clean, readable font stack

## 🔒 Database Schema

### Notes Table
```sql
CREATE TABLE note (
    id INTEGER PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## 🚀 Deployment

Vercel configuration is included. `src/main.py` exports the Flask `app`, `public/`
contains the frontend, and `.python-version` selects Python 3.12. `vercel.json`
sets a 60-second function duration and excludes local credentials and database files.
Real OpenRouter translation returned HTTP 200 with translated title and paragraphs.
The project owner verified saving the original and translation as separate Neon notes,
reloading, and persistence after restarting the app. A hosted Vercel deployment still
needs verification. See [the verification record](docs/live-verification.md).
Follow [the deployment guide](docs/vercel-deployment.md) to configure the cloud environment.
The local SQLite file must not be used as persistent storage in Vercel Functions.
See [Flask on Vercel](https://vercel.com/docs/frameworks/backend/flask).

This is a shared demonstration app: it does not implement login or per-user note isolation.
The unused user CRUD template is not registered as an API.

## 🔧 Configuration

### Environment Variables
- `FLASK_DEBUG=1`: Opt in to local debug mode. Debug is off by default.
- `SECRET_KEY`: Optional session key, read from the process environment; no hardcoded fallback.
  The current note app does not use sessions. Configure a key before adding session features.
- Start with `python src/main.py`. The local server binds to `127.0.0.1:5001`.
- Restart the server after changing Python code or dependencies when debug mode is off.
- Local configuration is loaded from the ignored `.env`; `.env.example` has empty credential fields.
- `LLM_API_URL`, `LLM_API_KEY`, `LLM_MODEL`: Server-side translation provider settings.
- `LLM_JSON_MODE`: `prompt` by default; `json_object` for providers supporting that format.
- `DATABASE_URL`: Empty means local SQLite; set a Neon PostgreSQL connection for external storage.
- `DATABASE_INIT_URL`: Optional direct PostgreSQL connection used only by `flask init-db`.

### Database and API
- Database file: `database/app.db` at the repository root.
- SQLite tables are created automatically. Initialize PostgreSQL tables explicitly using
  `python -m flask --app src.main init-db` after configuring its connection.
- Changing databases does not migrate existing SQLite notes automatically.
- Titles must be strings of at most 200 characters; content must be a string.
- At least a title or nonblank content is required. An empty title defaults to `Untitled`.
- Maximum HTTP request body size: 1 MiB. API errors are returned as JSON.
- Switching notes saves pending edits first; if saving fails, the editor keeps those edits.
- While a save/delete request is running, editing controls are temporarily disabled.

## Regression Tests

From the repository root after activating the virtual environment:

```cmd
python -m unittest discover -s tests -v
node tests/frontend.test.cjs
python -m pip check
```

Node.js is only required for the frontend logic tests, not for running this Flask app.
Backend tests use a separate in-memory SQLite database. The frontend tests cover
save/switch races, failure recovery, drafts, search, deletion, safe messages, translation
previews, stale responses, and saving translations without replacing the source.
LLM tests use mocked provider responses; they do not confirm live model availability.

## 📱 Browser Compatibility

- Chrome/Chromium (recommended)
- Firefox
- Safari
- Edge
- Mobile browsers (iOS Safari, Chrome Mobile)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

## 🆘 Support

For issues or questions:
1. Check the browser console for error messages
2. Verify the Flask server is running
3. Ensure all dependencies are installed
4. Check network connectivity for the deployed version

## 🎯 Future Enhancements

Potential improvements for future versions:
- User authentication and multi-user support
- Note categories and tags
- Rich text formatting (bold, italic, lists)
- File attachments
- Export functionality (PDF, Markdown)
- Dark/light theme toggle
- Offline support with service workers
- Note sharing capabilities

---

**Built with ❤️ using Flask, SQLite, and modern web technologies**

