#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для добавления содержимого promt.md в py_out.md.

Оба файла должны находиться в директории со скриптом.
Если py_out.md не существует - он будет создан.
Если promt.md не существует - будет показана ошибка.

Использование: python add_prompt_to_py_out.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

from core.config import default_config as cfg


def get_script_directory():
    """Получение директории, где находится скрипт"""
    return Path(__file__).parent.absolute()


def check_file_exists(file_path):
    """Проверка существования файла"""
    return file_path.exists()


def read_file(file_path):
    """Чтение содержимого файла"""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[-] Error reading file {file_path}: {e}")
        return None


def write_file(file_path, content):
    """Запись содержимого в файл"""
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[-] Error writing file {file_path}: {e}")
        return False


def append_to_file(file_path, content):
    """Добавление содержимого в конец файла"""
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[-] Error appending to file {file_path}: {e}")
        return False


def main():
    print("=" * 60)
    print("ADD PROMPT TO PY_OUT.MD")
    print("=" * 60)

    script_dir = get_script_directory()
    prompt_file = cfg.prompt_file
    py_out_file = cfg.output_file

    print(f"Script directory: {script_dir}")
    print(f"Prompt file: {prompt_file}")
    print(f"Target file: {py_out_file}")

    # Проверяем наличие promt.md
    if not check_file_exists(prompt_file):
        print("\n[ERROR] promt.md not found!")
        print(f"   File not found: {prompt_file}")
        print("\n   Please make sure promt.md exists in the script directory.")
        sys.exit(1)

    # Читаем содержимое promt.md
    print("\n[*] Reading promt.md...")
    prompt_content = read_file(prompt_file)
    if prompt_content is None:
        sys.exit(1)

    print(f"[+] promt.md size: {len(prompt_content)} bytes")

    # Проверяем существование py_out.md
    if not check_file_exists(py_out_file):
        print("\n[*] py_out.md not found, creating new file...")
        # Создаем новый файл с базовой структурой
        header = f"""# Prompt Analysis
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Source: promt.md

"""
        if write_file(py_out_file, header + prompt_content):
            print(f"[+] Created {py_out_file} with prompt content")
            print(f"\nStatistics:")
            print(f"   - File created: {py_out_file}")
            print(f"   - Content size: {len(prompt_content)} bytes")
        else:
            sys.exit(1)
    else:
        # Читаем текущее содержимое py_out.md
        print("\n[*] Reading existing py_out.md...")
        existing_content = read_file(py_out_file)
        if existing_content is None:
            sys.exit(1)

        print(f"[+] Existing py_out.md size: {len(existing_content)} bytes")

        # Добавляем разделитель и новое содержимое
        separator = "\n\n---\n"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        header = f"## Prompt Addition: {timestamp}\n\n"

        new_content = separator + header + prompt_content

        if append_to_file(py_out_file, new_content):
            print(f"[+] Content appended to {py_out_file}")
            print(f"\nStatistics:")
            print(f"   - Original size: {len(existing_content)} bytes")
            print(f"   - Added size: {len(new_content)} bytes")
            print(f"   - New total: {len(existing_content) + len(new_content)} bytes")
        else:
            sys.exit(1)

    print("\n" + "=" * 60)
    print("OPERATION COMPLETED SUCCESSFULLY")
    print("=" * 60)


if __name__ == "__main__":
    main()
