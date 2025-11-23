# Foundit - AI-Powered Desktop File Search

> Find files on your desktop using natural language and AI semantic search. Search by meaning, not just keywords!

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🌟 Features

- **🤖 AI-Powered Semantic Search**: Uses sentence transformers to understand what you're looking for
- **💬 ChatGPT-Like Interface**: Talk naturally - "find my resume" or "show me travel documents"
- **🧠 Smart Content Matching**: Finds "calculus homework" when you search for "math assignments"
- **📄 Multi-Format Support**: PDF, DOCX, PPTX, TXT, and code files
- **🎨 Beautiful Modern UI**: Electron-based desktop app with dark theme
- **⚡ Fast Vector Search**: FAISS for lightning-fast similarity search
- **🔒 Local & Private**: Everything runs on your machine - no cloud required
- **💡 Context Aware**: Remembers conversation and understands follow-up questions

## 📸 Screenshots

![Foundit Main Interface](https://via.placeholder.com/800x500?text=Foundit+Interface)

## 🚀 Quick Start

### Prerequisites

Before installing Foundit, make sure you have:

- **Python 3.8 or higher** ([Download Python](https://www.python.org/downloads/))
- **Node.js 16 or higher** ([Download Node.js](https://nodejs.org/))
- **Git** (optional, for cloning the repository)

### Installation

#### Option 1: Clone from GitHub (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/foundit.git
cd foundit

# Install backend dependencies
cd backend
pip install -r requirements.txt
cd ..

# Install frontend dependencies
cd frontend
npm install
cd ..
```

#### Option 2: Download ZIP

1. Download the latest release from [GitHub Releases](https://github.com/yourusername/foundit/releases)
2. Extract the ZIP file
3. Follow the installation steps above (starting from "Install backend dependencies")

### First-Time Setup

The AI model (~80MB) will be downloaded automatically on first run. This only happens once.

## 🎮 Running Foundit

### Windows

**Option 1: Using Terminals**

Open two command prompt or PowerShell windows:

**Terminal 1 - Start Backend:**
```cmd
cd backend
python app.py
```

Wait until you see:
```
Starting Foundit Backend Server...
Loading AI model (this may take a moment)...
Server ready!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

**Terminal 2 - Start Frontend:**
```cmd
cd frontend
npm start
```

The Foundit app window will open automatically!

**Option 2: Create a Batch File**

Create a file named `start-foundit.bat` in the project root:

```batch
@echo off
echo Starting Foundit Backend...
start cmd /k "cd backend && python app.py"
timeout /t 5
echo Starting Foundit Frontend...
cd frontend
npm start
```

Double-click the batch file to start Foundit.

### macOS / Linux

Open two terminal windows:

**Terminal 1 - Start Backend:**
```bash
cd backend
python3 app.py
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm start
```

## 📖 How to Use

### 1. Index Your Files

First time using Foundit? You need to index your files:

1. Click **"Quick Index Desktop"** to scan your Desktop folder
2. Or click **"Select Folder to Index"** to choose any directory
3. Wait for indexing to complete (progress bar will show status)

💡 **Tip**: Start with a smaller folder to test it out!

### 2. Search Naturally

Type queries in plain English:

- "Find my resume"
- "Show me Python code from last month"
- "Where are my tax documents?"
- "Math homework"
- "Budget spreadsheet"

Press Enter or click Search to see results!

### 3. Chat with AI

Ask follow-up questions:

```
You: "find my passport"
AI: *Shows passport.pdf*

You: "summarize it"
AI: *Provides summary of the document*
```

### 4. Open Files

Click any result to open the file in its default application.

## 💡 Example Searches

| What You Type | What Foundit Finds |
|---------------|-------------------|
| "calculus assignments" | Math homework, derivatives problems, integration exercises |
| "javascript tutorials" | JS code, React projects, web development notes |
| "budget planning" | Financial spreadsheets, expense reports, planning docs |
| "meeting notes" | Meeting minutes, discussion summaries, action items |
| "my resume" | CV, professional experience, work history |
| "travel documents" | Passport, visas, boarding passes, itineraries |

## 🔧 Supported File Types

- **Documents**: PDF, DOCX, PPTX, TXT, MD
- **Code**: PY, JS, CPP, H, JAVA, GO, RS, TS, JSX, etc.
- **Data**: JSON, XML, CSV, YAML
- **Text**: All plain text files

## 🏗️ Architecture

```
┌─────────────────────────────┐
│   Electron Frontend         │
│   (Modern UI)               │
└──────────┬──────────────────┘
           │ REST API
┌──────────▼──────────────────┐
│   Python Backend (FastAPI)  │
│   - RAG Engine              │
│   - Document Parser         │
│   - Search Engine           │
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────┐
│   AI Components             │
│   - Sentence Transformers   │
│   - FAISS Vector Index      │
│   - OpenRouter LLM API      │
└─────────────────────────────┘
```

## ⚙️ Configuration

### Backend Configuration

1. Copy `backend/config.example.py` to `backend/config.py`
2. Add your OpenRouter API key (optional, for enhanced chat):

```python
OPENROUTER_API_KEY = "your-api-key-here"
```

Get a free API key at [OpenRouter](https://openrouter.ai/)

### Frontend Configuration

The frontend automatically connects to `http://127.0.0.1:8000`. To change this, edit `frontend/renderer.js`:

```javascript
const API_URL = 'http://127.0.0.1:8000';
```

## 📊 Performance

- **Indexing Speed**: ~10-50 files/second (depends on file size)
- **Search Speed**: <100ms for typical queries
- **AI Model Size**: ~80MB (downloads once)
- **Memory Usage**: ~500MB-1GB during indexing
- **Disk Space**: ~100MB + your indexed files

## 🐛 Troubleshooting

### Backend won't start

**Problem**: Error when running `python app.py`

**Solutions**:
- Make sure Python 3.8+ is installed: `python --version`
- Install requirements: `pip install -r requirements.txt`
- Check for port conflicts (port 8000)
- Try: `python -m pip install --upgrade pip`

### Frontend shows "Backend Offline"

**Problem**: Can't connect to backend

**Solutions**:
- Make sure backend is running on http://127.0.0.1:8000
- Check backend terminal for errors
- Restart both backend and frontend
- Check firewall settings

### No results found

**Problem**: Search returns no results

**Solutions**:
- Make sure you indexed files first ("Quick Index Desktop")
- Try broader search terms
- Verify files contain searchable text (not just images)
- Re-index your files

### Slow indexing

**Problem**: Indexing takes a long time

**Solutions**:
- Normal for large folders (1000+ files)
- PDFs with scanned images take longer
- Index smaller folders first to test
- Close other applications to free up memory

### Module not found errors

**Problem**: Python can't find installed packages

**Solutions**:
- Use a virtual environment:
  ```bash
  python -m venv venv
  venv\Scripts\activate  # Windows
  source venv/bin/activate  # macOS/Linux
  pip install -r requirements.txt
  ```

## 🛠️ Technology Stack

- **Frontend**: Electron, HTML, CSS, JavaScript
- **Backend**: Python, FastAPI
- **AI Model**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector Database**: FAISS
- **LLM**: OpenRouter API (GPT-4, Claude, etc.)
- **Document Parsing**: PyPDF2, python-docx, python-pptx

## 📚 API Documentation

### Endpoints

- `POST /index` - Index files from a directory
- `POST /search` - Search for files using natural language
- `POST /chat` - Chat with AI about files
- `GET /status` - Get indexing status
- `POST /clear-index` - Clear the current index

See full API documentation in [API.md](docs/API.md)

## 🤝 Contributing

Contributions are welcome! Here's how you can help:

- 🐛 Report bugs via [GitHub Issues](https://github.com/yourusername/foundit/issues)
- 💡 Suggest new features
- 🔧 Submit pull requests
- 📖 Improve documentation

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📋 Roadmap

- [ ] Incremental indexing (auto-detect new files)
- [ ] Search filters (file type, date, size)
- [ ] Search history and favorites
- [ ] Better preview/highlighting
- [ ] OCR for scanned PDFs
- [ ] Multi-language support
- [ ] Configurable AI models
- [ ] Cloud sync (optional)
- [ ] Mobile app
- [ ] Browser extension

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Electron](https://www.electronjs.org/)
- Powered by [sentence-transformers](https://www.sbert.net/)
- Uses [FAISS](https://github.com/facebookresearch/faiss) for vector search
- LLM capabilities via [OpenRouter](https://openrouter.ai/)

## 📞 Support

- 📧 Email: support@foundit.app
- 💬 Discord: [Join our community](https://discord.gg/foundit)
- 🐦 Twitter: [@founditapp](https://twitter.com/founditapp)
- 📖 Documentation: [docs.foundit.app](https://docs.foundit.app)

## ⭐ Star History

If you find Foundit useful, please consider giving it a star on GitHub!

---

Made with ❤️ by the Foundit Team
