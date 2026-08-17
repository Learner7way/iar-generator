#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Запрос к LLM через абстракцию бэкенда (замена pyAIqesion.py + start_chrome_debug.py).

Читает вопрос из py_out.md, отправляет бэкенду (мок или OpenAI-compatible API),
сохраняет ответ в py_in.txt. Chrome/Selenium больше не нужен.

Конфигурация: ai_config.ini (секция [backend]) с переопределением переменными
окружения AI_BACKEND / AI_MODEL / AI_BASE_URL / AI_API_KEY / AI_TIMEOUT / AI_MAX_TOKENS.

Использование: python -m ai.ask
"""

import configparser
import os
import sys
from pathlib import Path
from typing import Any, Dict

from ai.backends import create_backend
from core.config import default_config
from utils.file_reader import read_text

SCRIPT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = default_config.ai_config
INPUT_FILE = default_config.output_file
OUTPUT_FILE = default_config.answer_file

DEFAULT_BACKEND_CONFIG: Dict[str, Any] = {
    "type": "mock",
    "model": "local-model",
    "base_url": "http://127.0.0.1:8080/v1",
    "api_key": "",
    "timeout": 120,
    "max_tokens": 4096,
}

_ENV_KEYS = {
    "type": "AI_BACKEND",
    "model": "AI_MODEL",
    "base_url": "AI_BASE_URL",
    "api_key": "AI_API_KEY",
    "timeout": "AI_TIMEOUT",
    "max_tokens": "AI_MAX_TOKENS",
}


def load_backend_config(path: Path = DEFAULT_CONFIG) -> Dict[str, Any]:
    """Загрузка конфига бэкенда: INI → переменные окружения → значения по умолчанию."""
    cfg = dict(DEFAULT_BACKEND_CONFIG)

    if path.exists():
        parser = configparser.ConfigParser()
        parser.read(path, encoding="utf-8")
        if parser.has_section("backend"):
            for key in cfg:
                if parser.has_option("backend", key):
                    cfg[key] = parser.get("backend", key)

    for key, env_name in _ENV_KEYS.items():
        value = os.getenv(env_name)
        if value:
            cfg[key] = value

    cfg["timeout"] = int(cfg["timeout"])
    cfg["max_tokens"] = int(cfg["max_tokens"])
    return cfg


def ask(question: str, config: Dict[str, Any]) -> str:
    """Отправка вопроса бэкенду и получение ответа."""
    backend = create_backend(config)
    return backend.generate(question)


def main() -> int:
    if not INPUT_FILE.exists():
        print(f"[ERROR] Файл вопроса не найден: {INPUT_FILE}")
        print("[INFO] Сначала запустите предыдущие шаги конвейера")
        return 1

    question, read_error = read_text(INPUT_FILE)
    if question is None:
        print(f"[ERROR] Не удалось прочитать вопрос: {read_error}")
        return 1

    config = load_backend_config()
    print(f"[INFO] Бэкенд: {config['type']}, модель: {config['model']}")
    if config["type"] == "mock":
        print("[WARN] Используется mock-бэкенд — ответ не от реальной LLM")

    answer = ask(question, config)
    OUTPUT_FILE.write_text(answer, encoding="utf-8")
    print(f"[OK] Ответ сохранён: {OUTPUT_FILE} ({len(answer)} символов)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
