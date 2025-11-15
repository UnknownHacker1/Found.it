# Foundit - AI-Powered Desktop File Search

Find files on your desktop using AI semantic search. Search by meaning, not just keywords!

## Features

- **AI-Powered Semantic Search**: Uses sentence transformers to understand what you're looking for
- **Smart Content Matching**: Finds "calculus homework" when you search for "math assignments"
- **Multi-Format Support**: PDF, DOCX, PPTX, TXT, and code files
- **Beautiful Modern UI**: Electron-based desktop app with dark theme
- **Fast Vector Search**: FAISS for lightning-fast similarity search
- **Local & Private**: Everything runs on your machine - no cloud required

## How It Works

1. **Index**: Scan your Desktop (or any folder) to extract text from files
2. **Embed**: AI converts text into vector embeddings that capture semantic meaning
3. **Search**: Type a query and AI finds files with similar content
4. **Results**: See ranked results with similarity scores

## Technology Stack

- **Frontend**: Electron + HTML/CSS/JavaScript
- **Backend**: Python + FastAPI
- **AI Model**: sentence-transformers (all-MiniLM-L6-v2)
- **Vector DB**: FAISS
- **Document Parsing**: PyPDF2, python-docx, python-pptx

## Installation

### Prerequisites

- Python 3.8+
- Node.js 16+
- npm

### Step 1: Install Python Backend

```bash
cd backend
pip install -r requirements.txt
```

**Note**: On first run, the AI model (~80MB) will be downloaded automatically.

### Step 2: Install Electron Frontend

```bash
cd frontend
npm install
```

## Running the App

### Start Backend (Terminal 1)

```bash
cd backend
python app.py
```

You should see:
```
Starting Foundit Backend Server...
Loading AI model (this may take a moment)...
Server ready!
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Start Frontend (Terminal 2)

```bash
cd frontend
npm start
```

The Electron app will open!

## Usage

### 1. Index Your Files

- Click **"Quick Index Desktop"** to scan your Desktop folder
- Or click **"Select Folder to Index"** to choose a custom directory
- Wait for indexing to complete (progress bar will show)

### 2. Search

- Type a query like:
  - "Math homework"
  - "Python code"
  - "Meeting notes from last week"
  - "Budget spreadsheet"
- Press Enter or click Search
- Results appear with similarity scores

### 3. Open Files

- Click any result to open the file

## Example Searches

| Query | Finds |
|-------|-------|
| "calculus assignments" | Math homework, derivatives problems, integration exercises |
| "javascript tutorials" | JS code, React projects, web development notes |
| "budget planning" | Financial spreadsheets, expense reports, planning docs |
| "team meeting notes" | Meeting minutes, discussion summaries, action items |

## Supported File Types

- **Documents**: PDF, DOCX, PPTX, TXT, MD
- **Code**: CPP, H, PY, JS, JAVA, GO, RS, etc.
- **Data**: JSON, XML, CSV, YAML

## Architecture

```
┌─────────────────────────────┐
│  Electron Frontend          │
│  (Modern UI)                │
└──────────┬──────────────────┘
           │ HTTP/REST API
┌──────────▼──────────────────┐
│  Python Backend (FastAPI)   │
│  - File Indexer             │
│  - Document Parser          │
│  - Search Engine            │
└──────────┬──────────────────┘
           │
┌──────────▼──────────────────┐
│  AI Components              │
│  - sentence-transformers    │
│  - FAISS Vector Index       │
└─────────────────────────────┘
```

## API Endpoints

- `POST /index` - Index files from a directory
- `POST /search` - Search for files
- `GET /status` - Get indexing status
- `POST /clear-index` - Clear the index

## Performance

- **Indexing Speed**: ~10-50 files/second (depends on file size)
- **Search Speed**: <100ms for typical queries
- **Model Size**: ~80MB (downloads once)
- **Memory Usage**: ~500MB-1GB (during indexing)

## Troubleshooting

### Backend won't start
- Make sure you installed all requirements: `pip install -r requirements.txt`
- Check Python version: `python --version` (needs 3.8+)

### "Backend Offline" in UI
- Make sure backend is running on http://127.0.0.1:8000
- Check backend terminal for errors

### No results found
- Make sure you indexed files first (click "Quick Index Desktop")
- Try broader search terms
- Check that your files contain searchable text

### Slow indexing
- Normal for large files/folders
- PDFs with scanned images (no text) will be empty
- Progress bar shows status

## Future Enhancements

- [ ] Incremental indexing (auto-detect new files)
- [ ] Search filters (file type, date, size)
- [ ] Search history
- [ ] Better preview/highlighting
- [ ] OCR for scanned PDFs
- [ ] Multi-language support
- [ ] Configurable AI models

## License

MIT

## Contributing

Pull requests welcome! Areas to improve:
- Better document parsing
- UI/UX enhancements
- Performance optimizations
- Additional file format support
