#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конфигурация конвейера py_generator (Этап 5 ROADMAP).

Читает пути/настройки из pipeline.ini (секция [paths]) с поддержкой
%ENV_VAR% в значениях. Реализация на stdlib (configparser + dataclass),
без внешних зависимостей (в отличие от py_project, где используется
Pydantic Settings).
"""

import configparser
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "pipeline.ini"

_ENV_PATTERN = re.compile(r"%([A-Za-z_][A-Za-z0-9_]*)%")


def expand_env_vars(value: str) -> str:
    """Замена %VAR% на значение переменной окружения (неизвестная — как есть)."""

    def replace(match: "re.Match[str]") -> str:
        name = match.group(1)
        return os.environ.get(name, match.group(0))

    return _ENV_PATTERN.sub(replace, value)


@dataclass(frozen=True)
class PipelineConfig:
    """Пути и настройки конвейера py_generator."""

    output_file: Path  # py_out.md — накопленный вопрос к AI
    answer_file: Path  # py_in.txt — ответ AI
    formatted_file: Path  # py_in_simplified.txt — отформатированный ответ
    buffer_file: Path  # buffer_py_in.txt — резерв исходного ответа
    task_file: Path  # task.txt — текст задачи
    history_dir: Path  # history/ — снапшоты py_out.md
    prompt_file: Path  # promt.md — стандарт C
    prompt_py_file: Path  # promt_py.md — стандарт Python
    ai_config: Path  # ai_config.ini — настройки AI-бэкенда

    @classmethod
    def from_ini(
        cls, path: Optional[Path] = None, base_dir: Optional[Path] = None
    ) -> "PipelineConfig":
        """Загрузка конфигурации из INI (по умолчанию pipeline.ini в корне)."""
        base = Path(base_dir or REPO_ROOT)
        ini_path = Path(path or DEFAULT_CONFIG_PATH)

        parser = configparser.ConfigParser(interpolation=None)
        if ini_path.exists():
            parser.read(ini_path, encoding="utf-8")

        def get(section: str, key: str, default: str) -> str:
            if parser.has_option(section, key):
                return expand_env_vars(parser.get(section, key))
            return default

        def resolve(value: str) -> Path:
            p = Path(value)
            if not p.is_absolute():
                p = base / p
            return p

        return cls(
            output_file=resolve(get("paths", "output_file", "py_out.md")),
            answer_file=resolve(get("paths", "answer_file", "py_in.txt")),
            formatted_file=resolve(
                get("paths", "formatted_file", "py_in_simplified.txt")
            ),
            buffer_file=resolve(get("paths", "buffer_file", "buffer_py_in.txt")),
            task_file=resolve(get("paths", "task_file", "task.txt")),
            history_dir=resolve(get("paths", "history_dir", "history")),
            prompt_file=resolve(get("paths", "prompt_file", "promt.md")),
            prompt_py_file=resolve(get("paths", "prompt_py_file", "promt_py.md")),
            ai_config=resolve(get("paths", "ai_config", "ai_config.ini")),
        )


default_config = PipelineConfig.from_ini()
