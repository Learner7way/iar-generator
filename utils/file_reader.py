#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Чтение файлов с автоопределением кодировки и детекцией бинарных файлов.

Извлечено из pyAIData.py (Этап 2 ROADMAP) и усилено сигнатурной проверкой
по содержимому (идея из py_project: file_collector).

Ограничение: слепое декодирование не различает перекрывающиеся кодировки
(например, реальный cp866-файл может быть прочитан как cp1251 — байты
валидны в обеих). Порядок кодировок: utf-8 → cp1251 → cp866 → koi8-r →
windows-1251 → latin-1 (latin-1 — страховка, декодирует любой байт).
"""

from pathlib import Path
from typing import List, Optional, Tuple

# Расширения, считающиеся бинарными (быстрая проверка по имени файла)
BINARY_EXTENSIONS = frozenset(
    {
        ".exe",
        ".bin",
        ".hex",
        ".o",
        ".obj",
        ".lib",
        ".dll",
        ".so",
        ".pyc",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".ico",
        ".pdf",
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".iso",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wmv",
        ".flv",
        ".mkv",
        ".ttf",
        ".otf",
        ".woff",
        ".woff2",
        ".eot",
    }
)

# Сигнатуры бинарных форматов (проверка по содержимому)
BINARY_SIGNATURES = (
    b"\x00",  # NUL-байты
    b"\xff\xd8\xff",  # JPEG
    b"\x89PNG\r\n\x1a\n",  # PNG
    b"GIF87a",  # GIF
    b"GIF89a",  # GIF
    b"PK\x03\x04",  # ZIP / DOCX / XLSX
    b"%PDF",  # PDF
)

# Порядок попыток декодирования (latin-1 в конце как «всеядная» страховка)
DEFAULT_ENCODINGS: List[str] = [
    "utf-8",
    "cp1251",
    "cp866",
    "koi8-r",
    "windows-1251",
    "latin-1",
]

# Лимит размера файла по умолчанию, МБ
DEFAULT_MAX_SIZE_MB = 10.0


def is_binary_by_extension(path) -> bool:
    """Быстрая проверка бинарности по расширению файла."""
    return Path(path).suffix.lower() in BINARY_EXTENSIONS


def is_binary_by_content(path, sample_size: int = 1024) -> bool:
    """Проверка бинарности по содержимому: NUL-байты, сигнатуры, UTF-8-проба."""
    try:
        with open(path, "rb") as f:
            sample = f.read(sample_size)
        if not sample:
            return False
        if b"\x00" in sample:
            return True
        for signature in BINARY_SIGNATURES:
            if sample.startswith(signature):
                return True
        try:
            sample.decode("utf-8")
            return False
        except UnicodeDecodeError:
            return True
    except OSError:
        # Файл не читается — считаем бинарным (безопасно для конвейера)
        return True


def is_binary_file(path, sample_size: int = 1024) -> bool:
    """Файл считается бинарным, если он бинарен по расширению ИЛИ по содержимому."""
    if is_binary_by_extension(path):
        return True
    return is_binary_by_content(path, sample_size)


def exceeds_size_limit(path, max_size_mb: Optional[float] = None) -> bool:
    """Превышает ли файл лимит размера (0/None — без лимита)."""
    limit = DEFAULT_MAX_SIZE_MB if max_size_mb is None else max_size_mb
    if limit <= 0:
        return False
    try:
        return Path(path).stat().st_size > limit * 1024 * 1024
    except OSError:
        return True


def read_text(
    path, encodings: Optional[List[str]] = None, max_size_mb: Optional[float] = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Чтение текстового файла с попыткой нескольких кодировок.

    :param path: Путь к файлу.
    :param encodings: Список кодировок для попытки (по умолчанию DEFAULT_ENCODINGS).
    :param max_size_mb: Лимит размера в МБ (None — DEFAULT_MAX_SIZE_MB).
    :return: Кортеж (содержимое, кодировка) или (None, сообщение_об_ошибке).
    """
    if exceeds_size_limit(path, max_size_mb):
        return (
            None,
            f"файл превышает лимит размера ({max_size_mb or DEFAULT_MAX_SIZE_MB} МБ)",
        )

    if encodings is None:
        encodings = DEFAULT_ENCODINGS

    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read(), encoding
        except UnicodeDecodeError:
            continue
        except OSError as e:
            return None, str(e)

    return None, "неподдерживаемая кодировка"
