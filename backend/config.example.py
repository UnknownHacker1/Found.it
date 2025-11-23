"""
Configuration for Foundit
Set your API keys here or use environment variables
"""

import os

# OpenRouter Configuration (Recommended)
# Get your free API key from: https://openrouter.ai/keys
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")  # Add your key here or set env variable

# OpenRouter Model Selection
# Free models:
# - "meta-llama/llama-3.1-8b-instruct:free"
# - "google/gemma-2-9b-it:free"
# - "mistralai/mistral-7b-instruct:free"
#
# Paid models (better quality):
# - "anthropic/claude-3.5-sonnet"
# - "openai/gpt-4-turbo"
# - "google/gemini-pro-1.5"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"


# Alternative: OpenAI (if you prefer GPT-4)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = "gpt-4"


# Alternative: Anthropic Claude
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"


# Alternative: Ollama (local, requires installation)
OLLAMA_MODEL = "llama3.1:8b"
OLLAMA_BASE_URL = "http://localhost:11434"


# LLM Provider Priority
# The system will try providers in this order
# Options: "openrouter", "ollama", "openai", "anthropic"
LLM_PROVIDER_PRIORITY = ["openrouter", "ollama", "openai", "anthropic"]
