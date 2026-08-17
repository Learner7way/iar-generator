"""LLM-бэкенды для AI-конвейера py_generator.

Повторяет паттерн rlm_agent/src/llm_backends.py:
- MockBackend — для тестов и прогона конвейера без реальной LLM;
- OpenAICompatibleBackend — OpenAI-совместимый chat/completions клиент
  (работает с llama.cpp, Ollama, DeepSeek API и любым OpenAI-compatible сервером);
- create_backend(config) — фабрика по типу из конфига.
"""

import os
from typing import Any

import requests

from ai.backend_base import LLMBackend


class MockBackend(LLMBackend):
    """Мок-бэкенд: возвращает предзаданный ответ (или имитацию ответа AI)."""

    def __init__(self, response: str | None = None, timeout: int = 120) -> None:
        self.response = response
        self.timeout = timeout

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        if self.response is not None:
            return self.response
        # Имитация ответа AI в формате конвейера: create/update блок
        return (
            "**Файл:** `src/mock_file.c`\n"
            "```c\n"
            "int mock_function(void) { return 0; }\n"
            "```\n"
        )


class OpenAICompatibleBackend(LLMBackend):
    """Клиент OpenAI-совместимого chat/completions API."""

    def __init__(
        self,
        model: str = "local-model",
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: int = 120,
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.api_key = api_key or os.getenv("AI_API_KEY", "not-needed")
        self.base_url = base_url or os.getenv("AI_BASE_URL", "http://127.0.0.1:8080/v1")
        # 0/None — без таймаута (локальные модели могут отвечать долго)
        self.timeout = timeout if timeout not in (0, None) else None
        self.max_tokens = max_tokens
        self.url = self.base_url.rstrip("/") + "/chat/completions"

    def generate(self, prompt: str, system: str | None = None, **kwargs: Any) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        timeout_note = "без таймаута" if self.timeout is None else f"{self.timeout}с"
        print(
            f"[*] Ожидание ответа LLM ({timeout_note}), Ctrl+C для отмены...",
            flush=True,
        )
        response = requests.post(
            self.url, headers=headers, json=payload, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


def create_backend(config: dict[str, Any]) -> LLMBackend:
    """Фабрика бэкенда по конфигу (аналог rlm_agent create_backend).

    :param config: Словарь с ключами type/model/base_url/api_key/timeout/max_tokens.
    """
    backend_type = str(config.get("type", "mock")).lower()
    timeout = int(config.get("timeout", 120))

    if backend_type == "mock":
        return MockBackend(timeout=timeout)

    if backend_type in ("openai-compatible", "openai_compatible", "openai"):
        return OpenAICompatibleBackend(
            model=config.get("model", "local-model"),
            api_key=config.get("api_key"),
            base_url=config.get("base_url"),
            timeout=timeout,
            max_tokens=int(config.get("max_tokens", 4096)),
        )

    raise ValueError(f"Unknown backend type: {backend_type}")
