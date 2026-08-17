#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для преобразования свободного формата в строгий формат py_in.txt.
Всегда берет py_in.txt как входной и выходной файл, используя buffer_py_in.txt для промежуточного хранения.

Использование: python py_in_formatter.py
"""

import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

from core.config import default_config as cfg

# Имена файлов из конфигурации конвейера
INPUT_FILE = cfg.answer_file
BUFFER_FILE = cfg.buffer_file


def parse_input_file(file_path):
    """Парсинг входного файла и извлечение операций и содержимого."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Извлекаем все операции create/update/delete
    create_files = re.findall(r"^create\s+`([^`]+)`", content, re.MULTILINE)
    update_files = re.findall(r"^update\s+`([^`]+)`", content, re.MULTILINE)
    delete_files = re.findall(r"^delete\s+`([^`]+)`", content, re.MULTILINE)

    # Также ищем операции без кавычек
    create_files.extend(re.findall(r"^create\s+([^\s]+)", content, re.MULTILINE))
    update_files.extend(re.findall(r"^update\s+([^\s]+)", content, re.MULTILINE))
    delete_files.extend(re.findall(r"^delete\s+([^\s]+)", content, re.MULTILINE))

    # Извлекаем все секции с содержимым файлов
    file_contents = {}

    # Паттерн с кавычками
    content_sections = re.findall(
        r"Файл:\s*`([^`]+)`\s*\n```c\n(.*?)```", content, re.DOTALL
    )
    for file_path, file_content in content_sections:
        file_contents[file_path.strip()] = file_content.strip()

    # Паттерн без кавычек
    content_sections = re.findall(
        r"Файл:\s*([^\s]+)\s*\n```c\n(.*?)```", content, re.DOTALL
    )
    for file_path, file_content in content_sections:
        file_contents[file_path.strip()] = file_content.strip()

    return create_files, update_files, delete_files, file_contents


def generate_py_in(
    output_path, create_files, update_files, delete_files, file_contents
):
    """Генерация структурированного py_in.txt файла."""
    with open(output_path, "w", encoding="utf-8") as f:
        # Заголовок
        f.write("=" * 60 + "\n")
        f.write("AUTO-GENERATED FILE FROM formatter\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")

        # Список файлов для изменения
        f.write("1. Список файлов для изменения\n")
        f.write("-" * 40 + "\n")

        if create_files:
            f.write("\ncreate\n")
            for file_path in sorted(set(create_files)):
                f.write(f"{file_path}\n")

        if update_files:
            f.write("\nupdate\n")
            for file_path in sorted(set(update_files)):
                f.write(f"{file_path}\n")

        if delete_files:
            f.write("\ndelete\n")
            for file_path in sorted(set(delete_files)):
                f.write(f"{file_path}\n")

        f.write("\n" + "=" * 60 + "\n\n")

        # Содержимое файлов
        f.write("2. Содержимое файлов\n")
        f.write("=" * 60 + "\n")

        # Все файлы, для которых есть содержимое (create, update и просто файлы с содержимым)
        all_files_with_content = set(
            create_files + update_files + list(file_contents.keys())
        )

        for file_path in sorted(all_files_with_content):
            if file_path in file_contents:
                f.write(f"\nФайл: `{file_path}`\n")
                f.write("```c\n")
                f.write(file_contents[file_path])
                if not file_contents[file_path].endswith("\n"):
                    f.write("\n")
                f.write("```\n")
            else:
                print(f"[WARN]  Warning: No content for {file_path}")
                # Проверяем, может быть файл с таким именем есть в contents под другим путем
                found = False
                file_name = Path(file_path).name
                for content_path, content in file_contents.items():
                    if file_name in content_path or file_path in content_path:
                        f.write(f"\nФайл: `{file_path}`\n")
                        f.write("```c\n")
                        f.write(content)
                        if not content.endswith("\n"):
                            f.write("\n")
                        f.write("```\n")
                        found = True
                        print(f"   → Matched with: {content_path}")
                        break

                if not found:
                    f.write(f"\nФайл: `{file_path}`\n")
                    f.write("```c\n")
                    f.write("// TODO: Add content\n")
                    f.write("```\n")

        # Удаляемые файлы в конце
        if delete_files:
            f.write("\n" + "=" * 60 + "\n")
            f.write("Удаляемые файлы:\n")
            for file_path in sorted(set(delete_files)):
                # Убираем лишние пробелы и кавычки
                file_path = file_path.strip().strip("`").strip('"').strip("'")
                f.write(f"• `{file_path}` (удален)\n")


def main():
    print("=" * 60)
    print("[PROCESS] PY_IN FORMATTER")
    print("=" * 60)

    # Проверяем наличие py_in.txt
    input_path = Path(INPUT_FILE)
    if not input_path.exists():
        print(f"[ERROR] {INPUT_FILE} not found!")
        print(f"\nPlease create {INPUT_FILE} with your changes description")
        sys.exit(1)

    print(f"\n[*] Reading: {INPUT_FILE}")

    # Создаем резервную копию в buffer_py_in.txt
    buffer_path = Path(BUFFER_FILE)
    shutil.copy2(input_path, buffer_path)
    print(f"[[OK]] Backup created: {BUFFER_FILE}")

    # Парсим входной файл
    create_files, update_files, delete_files, file_contents = parse_input_file(
        INPUT_FILE
    )

    print(f"\n[*] Found in {INPUT_FILE}:")
    print(f"   - Create: {len(create_files)} files")
    print(f"   - Update: {len(update_files)} files")
    print(f"   - Delete: {len(delete_files)} files")
    print(f"   - Content sections: {len(file_contents)} files")

    # Проверяем, что для всех create/update есть содержимое
    missing_content = []
    for file_path in set(create_files + update_files):
        if file_path not in file_contents:
            # Проверяем по имени файла
            file_name = Path(file_path).name
            found = False
            for content_path in file_contents:
                if file_name in content_path or file_path in content_path:
                    found = True
                    break
            if not found:
                missing_content.append(file_path)

    if missing_content:
        print("\n[WARN]  Missing content for:")
        for f in missing_content:
            print(f"   - {f}")

    # Генерируем новый py_in.txt
    generate_py_in(INPUT_FILE, create_files, update_files, delete_files, file_contents)

    print(f"\n[OK] Updated: {INPUT_FILE}")
    print(f"[FILE] Original saved in: {BUFFER_FILE}")
    print("\nNext step: python py_in_updater.py <project_path>")
    print("=" * 60)


if __name__ == "__main__":
    main()
