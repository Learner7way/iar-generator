"""Пакет AI-интеграции py_generator (по образцу rlm_agent)."""

from ai.backend_base import LLMBackend
from ai.backends import MockBackend, OpenAICompatibleBackend, create_backend

__all__ = ["LLMBackend", "MockBackend", "OpenAICompatibleBackend", "create_backend"]
__version__ = "0.1.0"
