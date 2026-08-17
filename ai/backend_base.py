"""Абстрактный базовый класс для LLM-бэкендов (по образцу rlm_agent).

Контракт: любой провайдер реализует `generate(prompt, system=None, **kwargs)`.
Это позволяет конвейеру не зависеть от конкретного провайдера (мок, локальный
llama.cpp/Ollama, DeepSeek API) и подменять его через фабрику `create_backend`.
"""

from abc import ABC, abstractmethod
from typing import Any


class LLMBackend(ABC):
    """Абстрактный провайдер LLM."""

    @abstractmethod
    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        """Сгенерировать текст ответа на промпт."""
        raise NotImplementedError
