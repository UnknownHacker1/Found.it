# OpenRouter Setup - Quick Start Guide

OpenRouter gives you access to many AI models (including free ones!) through a single API.

## Step 1: Get Your Free API Key

1. Go to https://openrouter.ai/keys
2. Sign up with Google/GitHub (takes 30 seconds)
3. Click "Create Key"
4. Copy your API key (starts with `sk-or-...`)

## Step 2: Add API Key to Foundit

Open [backend/config.py](d:\Foundit\backend\config.py) and paste your key:

```python
OPENROUTER_API_KEY = "sk-or-v1-your-key-here"
```

That's it!

## Step 3: Start Foundit

```bash
# Terminal 1 - Backend
cd d:\Foundit\backend
python app.py

# Terminal 2 - Frontend
cd d:\Foundit\frontend
npm start
```

You should see:
```
Using OpenRouter with model: meta-llama/llama-3.1-8b-instruct:free
RAG engine ready! You can now chat with your files.
```

## Available Models

### Free Models (No cost!)
```python
# In config.py, change OPENROUTER_MODEL to:

"meta-llama/llama-3.1-8b-instruct:free"     # Llama 3.1 (recommended)
"google/gemma-2-9b-it:free"                 # Google Gemma
"mistralai/mistral-7b-instruct:free"        # Mistral
"microsoft/phi-3-medium-128k-instruct:free" # Phi-3
```

### Paid Models (Better quality, low cost)
```python
"anthropic/claude-3.5-sonnet"     # Best overall (~$3 per million tokens)
"openai/gpt-4-turbo"              # GPT-4 (~$10 per million tokens)
"google/gemini-pro-1.5"           # Fast and cheap (~$1 per million tokens)
"meta-llama/llama-3.1-70b-instruct" # Llama 70B (~$0.50 per million)
```

## Cost Estimation (Paid Models)

For typical use with Foundit:
- **Free models**: $0 (completely free!)
- **Paid models**: ~$0.01 - $0.05 per search (very cheap)
- **Monthly usage**: ~$1-5 for regular use

The free models work great for most file searching!

## Troubleshooting

### "RAG engine not ready"
- Make sure you copied the API key correctly
- Check that `OPENROUTER_API_KEY` in config.py has your key
- Restart the backend server

### "OpenRouter API error: 401"
- API key is invalid
- Get a new key from https://openrouter.ai/keys

### "OpenRouter API error: 429"
- Rate limit reached (unlikely with free models)
- Wait a minute and try again

## Why OpenRouter?

- **Easy**: One API for many models
- **Free options**: Multiple free models available
- **No setup**: No need to install Ollama or run local models
- **Fast**: Cloud-based, works on any computer
- **Cheap**: Paid models are very affordable
- **Flexible**: Switch models instantly

## Privacy Note

With OpenRouter, your queries and file content are sent to their servers (and the model provider). If you need 100% local/private:

1. Remove the API key from config.py
2. Install Ollama: https://ollama.com
3. Run: `ollama pull llama3.1:8b`
4. Restart backend - it will auto-detect Ollama

## Example Usage

**You:** "Find my resume"
→ OpenRouter API call (~$0.001)
→ AI finds your CV

**You:** "Show travel documents"
→ OpenRouter API call (~$0.001)
→ AI finds passports, visas, i94s

Totally worth it!
