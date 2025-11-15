# Foundit Setup Guide - Conversational AI File Assistant

Complete setup instructions for running Foundit with local AI (Ollama).

## Prerequisites

- **Python 3.8+** installed
- **Node.js 16+** and npm installed
- **Ollama** installed (for local LLM)
- **8GB+ RAM** recommended
- **Windows OS** (tested on Windows 10/11)

---

## Step 1: Install Ollama

Ollama runs the local LLM (Llama 3.1) on your machine.

### Download and Install

1. Go to https://ollama.com/download
2. Download Ollama for Windows
3. Run the installer
4. Ollama will start automatically

### Pull the Llama 3.1 Model

Open Command Prompt or PowerShell:

```bash
ollama pull llama3.1:8b
```

This downloads the 8B parameter Llama 3.1 model (~4.7GB). First time will take a few minutes.

### Verify Ollama is Running

```bash
ollama list
```

You should see `llama3.1:8b` in the list.

---

## Step 2: Install Python Dependencies

```bash
cd d:\Foundit\backend
pip install -r requirements.txt
```

This installs:
- FastAPI (web framework)
- sentence-transformers (for embeddings)
- FAISS (vector search)
- PyPDF2, python-docx, python-pptx (document parsing)
- requests (for Ollama communication)

**Note**: First run will download the embedding model (~80MB).

---

## Step 3: Install Node.js Dependencies

```bash
cd d:\Foundit\frontend
npm install
```

This installs Electron and other frontend dependencies.

---

## Step 4: Start the Application

### Option A: Using the Batch File (Easiest)

Double-click `start.bat` in the Foundit folder. This opens both backend and frontend automatically.

### Option B: Manual Start

**Terminal 1 - Backend:**
```bash
cd d:\Foundit\backend
python app.py
```

Wait for:
```
RAG engine ready! You can now chat with your files.
Server ready!
INFO:     Uvicorn running on http://127.0.0.1:8001
```

**Terminal 2 - Frontend:**
```bash
cd d:\Foundit\frontend
npm start
```

The Electron app will open!

---

## Step 5: Index Your Files

1. In the app sidebar, click **"Index Desktop"**
2. Wait for indexing to complete (progress bar shows status)
3. When done, you'll see "X files indexed" in the sidebar

---

## Step 6: Start Chatting!

Now you can chat with the AI about your files:

### Example Conversations:

**You:** "Find my resume"
**AI:** "I found your resume: Professional_CV_2024.pdf. This document contains your work experience, education, and skills."

**You:** "Show me travel documents"
**AI:** "I found 3 travel-related files. Here are the most relevant: [displays i94 forms, passports, flight tickets]"

**You:** "Where's the Q3 budget file?"
**AI:** "I found your Q3 budget: Q3_Financial_Report.xlsx. This spreadsheet contains quarterly expenses and revenue projections."

---

## How It Works

### 1. **Indexing Phase**
- Scans your files
- Extracts text from PDFs, Word docs, PowerPoints, code files
- Generates vector embeddings using sentence-transformers
- Stores in FAISS vector database

### 2. **Chat Phase**
- You ask a question in natural language
- **LLM (Llama 3.1)** understands your intent and extracts search terms
- **Vector search** finds candidate files with similar content
- **LLM reasons** about which files best match your request
- Returns results with explanation

### 3. **Why It's Smart**
- Understands **concepts**, not just keywords
- "resume" finds your CV even without the word "resume" in it
- "travel documents" finds i94 forms, passports, visas
- "Q3 budget" understands you want financial docs for that quarter

---

## Switching to OpenAI/Claude (Optional)

Want to use GPT-4 or Claude instead of local Ollama?

### For OpenAI:

1. Install the SDK:
```bash
pip install openai
```

2. Set your API key:
```bash
set OPENAI_API_KEY=your-api-key-here
```

3. Edit [backend/app.py](d:\Foundit\backend\app.py) line ~202:
```python
# Change this:
rag_engine = RAGEngine(search_engine)

# To this:
from llm_provider import OpenAIProvider
llm = OpenAIProvider(model="gpt-4")
rag_engine = RAGEngine(search_engine, llm_provider=llm)
```

### For Anthropic Claude:

1. Install the SDK:
```bash
pip install anthropic
```

2. Set your API key:
```bash
set ANTHROPIC_API_KEY=your-api-key-here
```

3. Edit [backend/app.py](d:\Foundit\backend\app.py) similarly with `AnthropicProvider`.

---

## Troubleshooting

### "RAG engine not ready"
- Make sure Ollama is running: `ollama serve`
- Make sure Llama 3.1 is installed: `ollama list`
- Restart the backend

### "Backend Offline" in UI
- Check backend terminal for errors
- Make sure it's running on port 8001
- Try restarting

### "No files found"
- Make sure you indexed files first
- Try re-indexing with "Clear Index" then "Index Desktop"

### Slow responses
- Normal for first query (model loading)
- Subsequent queries should be faster
- With GPU: much faster
- Without GPU: 5-15 seconds per response is normal

### Out of memory
- Close other applications
- Use smaller model: `ollama pull llama3.1:7b` (not :8b)
- Or switch to OpenAI/Claude (uses their servers)

---

## File Structure

```
Foundit/
├── backend/
│   ├── app.py              # FastAPI server
│   ├── rag_engine.py       # RAG pipeline
│   ├── llm_provider.py     # LLM abstraction layer
│   ├── search_engine.py    # Vector search
│   ├── indexer.py          # File indexing
│   ├── document_parser.py  # Text extraction
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── index-chat.html     # Chat UI
│   ├── styles-chat.css     # Styles
│   ├── renderer-chat.js    # UI logic
│   ├── main.js             # Electron main process
│   └── package.json        # Node dependencies
├── start.bat               # Quick start script
└── README.md               # Documentation
```

---

## Performance Tips

1. **Use SSD**: Faster file indexing
2. **GPU**: If you have NVIDIA GPU, install CUDA for faster LLM
3. **Limit scope**: Index only important folders, not entire drive
4. **Re-index**: Only when you add many new files

---

## Privacy & Security

- **100% Local**: All processing happens on your machine
- **No cloud**: Your files never leave your computer
- **No tracking**: No analytics or telemetry
- **Open source**: All code is visible and auditable

---

## Need Help?

- Check logs in backend terminal
- Try different queries
- Re-index files if results are poor
- Make sure Ollama is running

Enjoy using Foundit!
