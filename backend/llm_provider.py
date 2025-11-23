"""
LLM Provider - Abstraction layer for different LLM backends
Supports: Ollama (local), OpenAI, Anthropic Claude
Easy switching between providers via configuration
"""

from typing import List, Dict, Optional
from abc import ABC, abstractmethod
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""

    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text from prompt"""
        pass

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Chat with message history"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama provider for local LLMs (Llama, Mistral, etc.)"""

    def __init__(self, model: str = "llama3.1:8b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

        try:
            import requests
            self.requests = requests
            self.available = True
        except ImportError:
            logger.error("requests library not installed")
            self.available = False

    def is_available(self) -> bool:
        """Check if Ollama is running"""
        if not self.available:
            return False

        try:
            response = self.requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using Ollama"""
        try:
            response = self.requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["response"]
            else:
                raise Exception(f"Ollama API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Error generating with Ollama: {e}")
            raise

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Chat using Ollama chat API"""
        try:
            response = self.requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": 0.7,
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                return response.json()["message"]["content"]
            else:
                raise Exception(f"Ollama API error: {response.status_code}")

        except Exception as e:
            logger.error(f"Error chatting with Ollama: {e}")
            raise


class OpenAIProvider(LLMProvider):
    """OpenAI provider (GPT-4, GPT-3.5, etc.)"""

    def __init__(self, model: str = "gpt-4", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")

        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
            self.available = True
        except ImportError:
            logger.error("openai library not installed")
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing OpenAI: {e}")
            self.available = False

    def is_available(self) -> bool:
        """Check if OpenAI is available"""
        return self.available and self.api_key is not None

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error generating with OpenAI: {e}")
            raise

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Chat using OpenAI"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"Error chatting with OpenAI: {e}")
            raise


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider - Access to many models through one API"""

    def __init__(
        self,
        model: str = "meta-llama/llama-3.1-8b-instruct:free",
        api_key: Optional[str] = None,
        site_url: str = "http://localhost",
        app_name: str = "Foundit"
    ):
        self.model = model
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.site_url = site_url
        self.app_name = app_name
        self.base_url = "https://openrouter.ai/api/v1"

        try:
            import requests
            self.requests = requests
            self.available = True
        except ImportError:
            logger.error("requests library not installed")
            self.available = False

    def is_available(self) -> bool:
        """Check if OpenRouter is available"""
        return self.available and self.api_key is not None

    def _make_request(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Make request to OpenRouter API"""
        try:
            response = self.requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "HTTP-Referer": self.site_url,
                    "X-Title": self.app_name,
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.3,  # Lower temperature for faster, more focused responses
                    "top_p": 0.9
                },
                timeout=10  # Faster timeout for query expansion (10 seconds max)
            )

            if response.status_code == 200:
                content = response.json()["choices"][0]["message"]["content"]
                # Clean up special tokens from model output
                content = content.replace("<s>", "").replace("</s>", "")
                content = content.replace("[INST]", "").replace("[/INST]", "")
                content = content.replace("[OUT]", "").replace("[/OUT]", "")
                content = content.strip()
                return content
            else:
                raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

        except Exception as e:
            logger.error(f"Error with OpenRouter: {e}")
            raise

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using OpenRouter"""
        messages = [{"role": "user", "content": prompt}]
        return self._make_request(messages, max_tokens)

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Chat using OpenRouter"""
        return self._make_request(messages, max_tokens)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider"""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
            self.available = True
        except ImportError:
            logger.error("anthropic library not installed")
            self.available = False
        except Exception as e:
            logger.error(f"Error initializing Anthropic: {e}")
            self.available = False

    def is_available(self) -> bool:
        """Check if Anthropic is available"""
        return self.available and self.api_key is not None

    def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using Claude"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"Error generating with Claude: {e}")
            raise

    def chat(self, messages: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        """Chat using Claude"""
        try:
            # Convert messages to Claude format
            claude_messages = []
            for msg in messages:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=claude_messages
            )
            return response.content[0].text

        except Exception as e:
            logger.error(f"Error chatting with Claude: {e}")
            raise


class LLMFactory:
    """Factory for creating LLM providers"""

    @staticmethod
    def create(provider_type: str = "openrouter", **kwargs) -> LLMProvider:
        """
        Create an LLM provider

        Args:
            provider_type: "openrouter", "ollama", "openai", or "anthropic"
            **kwargs: Provider-specific arguments

        Returns:
            LLMProvider instance
        """
        providers = {
            "openrouter": OpenRouterProvider,
            "ollama": OllamaProvider,
            "openai": OpenAIProvider,
            "anthropic": AnthropicProvider,
        }

        if provider_type not in providers:
            raise ValueError(f"Unknown provider: {provider_type}")

        provider_class = providers[provider_type]
        provider = provider_class(**kwargs)

        if not provider.is_available():
            logger.warning(f"{provider_type} is not available")

        return provider

    @staticmethod
    def create_best_available(**kwargs) -> LLMProvider:
        """
        Create the best available provider
        Priority: OpenRouter > Ollama (free, local) > OpenAI > Anthropic
        """
        # Try OpenRouter first (easiest, many free models)
        try:
            provider = OpenRouterProvider(**kwargs.get("openrouter", {}))
            if provider.is_available():
                logger.info("Using OpenRouter")
                return provider
        except Exception as e:
            logger.warning(f"OpenRouter not available: {e}")

        # Try Ollama (free and local)
        try:
            provider = OllamaProvider(**kwargs.get("ollama", {}))
            if provider.is_available():
                logger.info("Using Ollama (local LLM)")
                return provider
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")

        # Try OpenAI
        try:
            provider = OpenAIProvider(**kwargs.get("openai", {}))
            if provider.is_available():
                logger.info("Using OpenAI")
                return provider
        except Exception as e:
            logger.warning(f"OpenAI not available: {e}")

        # Try Anthropic
        try:
            provider = AnthropicProvider(**kwargs.get("anthropic", {}))
            if provider.is_available():
                logger.info("Using Anthropic Claude")
                return provider
        except Exception as e:
            logger.warning(f"Anthropic not available: {e}")

        raise Exception("No LLM provider available")
