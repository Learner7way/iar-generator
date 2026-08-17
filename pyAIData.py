#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

from utils.file_reader import is_binary_file, read_text as read_file_content
from core.config import default_config as cfg


def parse_arguments():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(
        description="Генерация Markdown содержимого исходных файлов из IAR проекта"
    )
    parser.add_argument(
        "input_file",
        help="Имя входного .ewp файла (можно указывать с расширением или без)",
    )
    parser.add_argument(
        "proj_dir",
        help="Значение для замены $PROJ_DIR$ (например, C:\\Projects\\MyProject)",
    )
    return parser.parse_args()


def get_script_directory():
    """Получение директории, где находится скрипт"""
    return Path(__file__).parent.absolute()


def find_ewp_file(script_dir, input_name, proj_dir):
    """
    Поиск .ewp файла:
    1. Сначала ищем в PROJ_DIR
    2. Если не нашли, ищем в директории скрипта
    """
    proj_path = Path(proj_dir).resolve()

    input_path = Path(input_name)
    if input_path.suffix.lower() == ".ewp":
        ewp_filename = input_path.name
    else:
        ewp_filename = f"{input_path.stem}.ewp"

    ewp_in_proj = proj_path / ewp_filename
    if ewp_in_proj.exists():
        print(f"   [+] Найден в PROJ_DIR: {ewp_in_proj}")
        return ewp_in_proj

    ewp_in_script = script_dir / ewp_filename
    if ewp_in_script.exists():
        print(f"   [+] Найден в директории скрипта: {ewp_in_script}")
        return ewp_in_script

    return None


def normalize_path(path_str, proj_dir):
    """Нормализация пути с заменой $PROJ_DIR$"""
    path_str = path_str.replace("$PROJ_DIR$", proj_dir)
    return Path(path_str).resolve()


def get_relative_path_for_display(full_path, proj_dir):
    """
    Получение пути для отображения с использованием $PROJ_DIR$.
    """
    try:
        proj_path = Path(proj_dir).resolve()
        full_path = Path(full_path).resolve()

        # Пытаемся получить относительный путь
        rel_path = full_path.relative_to(proj_path)

        # Формируем путь с $PROJ_DIR$ и правильными разделителями
        # Используем as_posix() для получения путей с прямыми слешами
        rel_path_str = rel_path.as_posix()

        # Если путь начинается с точки, оставляем как есть
        if rel_path_str.startswith(".."):
            return f"$PROJ_DIR$/{rel_path_str}"
        else:
            return f"$PROJ_DIR$/{rel_path_str}"

    except (ValueError, FileNotFoundError):
        # Если путь вне PROJ_DIR, пытаемся найти общий родительский каталог
        try:
            # Ищем общую часть пути
            common_parts = []
            for part1, part2 in zip(full_path.parts, proj_path.parts):
                if part1 == part2:
                    common_parts.append(part1)
                else:
                    break

            if common_parts:
                common_path = Path(*common_parts)
                # Считаем количество уровней вверх от proj_dir до общего пути
                levels_up = len(proj_path.parts) - len(common_parts)
                # Путь от общего пути до файла
                remaining = full_path.relative_to(common_path)

                # Формируем путь с поднятием вверх
                up_levels = "../" * levels_up
                rel_path_str = up_levels + remaining.as_posix()
                return f"$PROJ_DIR$/{rel_path_str}"
        except:
            pass

        # Если ничего не получилось, показываем полный путь
        full_path_str = str(full_path).replace("\\", "/")
        # Убираем диск, если есть (C:/ -> /)
        if ":" in full_path_str:
            full_path_str = "/" + full_path_str.split(":", 1)[1]
        return full_path_str


def parse_ewp_file(ewp_file_path, proj_dir):
    """Чтение и обработка IAR .ewp файла"""
    structure_only_groups = ["firmware", "libs", "middleware"]

    project_files = {"structure_only": [], "full_content": []}

    print(f"\n[*] Анализ файла: {ewp_file_path}")
    print("   Обнаруженные файлы в проекте:")

    try:
        tree = ET.parse(ewp_file_path)
        root = tree.getroot()

        def process_group(group_element, current_group_names):
            group_name = group_element.find("name")
            if group_name is not None and group_name.text:
                group_name_text = group_name.text
                current_group_names.append(group_name_text)

                is_structure_only = any(
                    any(keyword in name.lower() for keyword in structure_only_groups)
                    for name in current_group_names
                )

                for file_elem in group_element.findall("file"):
                    name_elem = file_elem.find("name")
                    if name_elem is not None and name_elem.text:
                        file_path_str = name_elem.text.strip()

                        try:
                            normalized_path = normalize_path(file_path_str, proj_dir)

                            if not normalized_path.exists():
                                print(f"   [!] Файл не существует: {normalized_path}")
                                continue

                            if is_structure_only:
                                project_files["structure_only"].append(normalized_path)
                                print(f"  [структура] {normalized_path}")
                            else:
                                project_files["full_content"].append(normalized_path)
                                print(f"  [полный] {normalized_path}")

                        except Exception as e:
                            print(
                                f"   [!] Ошибка обработки пути '{file_path_str}': {e}"
                            )

                for sub_group in group_element.findall("group"):
                    process_group(sub_group, current_group_names.copy())

        for group in root.findall("group"):
            process_group(group, [])

        project_files["structure_only"] = list(set(project_files["structure_only"]))
        project_files["full_content"] = list(set(project_files["full_content"]))
        project_files["structure_only"].sort()
        project_files["full_content"].sort()

        print(f"\n   Статистика:")
        print(
            f"      - Файлов в группах firmware/libs/middleware: {len(project_files['structure_only'])}"
        )
        print(
            f"      - Файлов для полного анализа: {len(project_files['full_content'])}"
        )

        return project_files

    except ET.ParseError as e:
        print(f"[-] Ошибка парсинга XML: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"[-] Ошибка: файл проекта '{ewp_file_path}' не найден")
        sys.exit(1)
    except Exception as e:
        print(f"[-] Ошибка при чтении файла проекта: {e}")
        sys.exit(1)


def get_directory_tree_structure(files, proj_dir):
    """Построение структуры директорий из списка файлов"""
    print(f"\n[*] Построение структуры директорий из {len(files)} файлов")

    structure = {}
    proj_path = Path(proj_dir).resolve()

    processed_files = 0
    skipped_files = 0

    for file_path in files:
        try:
            file_path = Path(file_path).resolve()

            try:
                rel_path = file_path.relative_to(proj_path)
                parts = rel_path.parts
            except ValueError:
                parts = []
                start_index = -1
                for i, part in enumerate(file_path.parts):
                    if part.lower() in [
                        "project",
                        "firmware",
                        "libs",
                        "middleware",
                        "src",
                    ]:
                        start_index = i
                        break

                if start_index >= 0:
                    parts = file_path.parts[start_index:]
                else:
                    parts = [file_path.name]

            current = structure
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]

            if "_files" not in current:
                current["_files"] = []
            current["_files"].append(parts[-1])

            processed_files += 1

        except Exception as e:
            print(f"   [!] Ошибка построения структуры для {file_path}: {e}")
            skipped_files += 1

    print(
        f"   [*] Построено структуры: {processed_files} файлов обработано, {skipped_files} пропущено"
    )
    return structure


def count_files_in_structure(structure):
    """Подсчет количества файлов в структуре"""
    count = 0
    if "_files" in structure:
        count += len(structure["_files"])

    for key, value in structure.items():
        if key != "_files" and isinstance(value, dict):
            count += count_files_in_structure(value)

    return count


def print_tree(structure, indent="", output_lines=None, max_files=None):
    """Рекурсивный вывод дерева директорий"""
    if output_lines is None:
        output_lines = []

    items = list(structure.keys())
    dirs = [k for k in items if k != "_files"]
    dirs.sort()

    if max_files is not None:
        total_files_in_branch = count_files_in_structure(structure)
        if total_files_in_branch > max_files:
            line = f"{indent}└── ... ({total_files_in_branch} файлов, показаны только первые {max_files})"
            output_lines.append(line)
            return output_lines

    for i, dir_name in enumerate(dirs):
        is_last_dir = (i == len(dirs) - 1) and (
            "_files" not in structure or not structure["_files"]
        )
        prefix = "└── " if is_last_dir else "├── "
        line = f"{indent}{prefix}[DIR] {dir_name}/"
        output_lines.append(line)

        new_indent = indent + ("    " if is_last_dir else "│   ")
        print_tree(structure[dir_name], new_indent, output_lines, max_files)

    if "_files" in structure and structure["_files"]:
        files = sorted(structure["_files"])

        if max_files is not None and len(files) > max_files:
            for j in range(max_files):
                is_last_file = (j == max_files - 1) and not dirs
                prefix = "└── " if is_last_file else "├── "
                line = f"{indent}{prefix}    {files[j]}"
                output_lines.append(line)

            remaining = len(files) - max_files
            line = f"{indent}└── ... и еще {remaining} файлов"
            output_lines.append(line)
        else:
            for j, file_name in enumerate(files):
                is_last_file = (j == len(files) - 1) and not dirs
                prefix = "└── " if is_last_file else "├── "
                line = f"{indent}{prefix}    {file_name}"
                output_lines.append(line)

    return output_lines


def get_language_for_file(file_path):
    """Определение языка для подсветки синтаксиса по расширению"""
    extension = file_path.suffix.lower()
    lang_map = {
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".hpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".py": "python",
        ".md": "markdown",
        ".txt": "text",
        ".json": "json",
        ".xml": "xml",
        ".s": "asm",
        ".S": "asm",
        ".asm": "asm",
        ".inc": "asm",
        ".make": "makefile",
        ".mk": "makefile",
        ".cmake": "cmake",
        ".sh": "bash",
        ".bash": "bash",
        ".bat": "batch",
        ".cmd": "batch",
        ".ps1": "powershell",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".js": "javascript",
        ".ts": "typescript",
        ".php": "php",
        ".rb": "ruby",
        ".go": "go",
        ".rs": "rust",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".icf": "text",
    }
    return lang_map.get(extension, "")


def append_to_file(file_path, content):
    """Дописывает содержимое в конец файла"""
    try:
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"[-] Ошибка при записи в файл {file_path}: {e}")
        return False


def generate_markdown_content(project_files, proj_dir, ewp_file_name):
    """Генерация Markdown содержимого для добавления в файл"""
    lines = []

    # Простой разделитель
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"\n\n---")
    lines.append(f"## Анализ IAR проекта: {timestamp}")
    lines.append(f"**EWP файл:** {ewp_file_name}")
    lines.append(f"**PROJ_DIR:** {proj_dir}")
    lines.append(f"**Сгенерировано:** {Path(__file__).name}")
    lines.append("")

    # Статистика
    lines.append("### Общая информация\n")
    lines.append(
        f"- **Файлов в группах firmware/libs/middleware (только структура):** {len(project_files['structure_only'])}"
    )
    lines.append(
        f"- **Файлов для полного анализа:** {len(project_files['full_content'])}"
    )

    # СТРУКТУРА ДИРЕКТОРИЙ
    if project_files["structure_only"]:
        lines.append("\n### Структура директорий (firmware/libs/middleware)")
        lines.append(
            "*Эти директории содержат системные/библиотечные файлы, поэтому показывается только структура без содержимого*\n"
        )

        structure = get_directory_tree_structure(
            project_files["structure_only"], proj_dir
        )
        total_files_in_structure = count_files_in_structure(structure)
        print(f"   [*] Всего файлов в структуре: {total_files_in_structure}")

        if structure:
            lines.append("```")
            root_display = get_relative_path_for_display(Path(proj_dir), proj_dir)
            lines.append(f"[DIR] $PROJ_DIR$/../")

            tree_lines = print_tree(structure, indent="", max_files=None)
            lines.extend(tree_lines)
            lines.append("```")
            lines.append(f"\n*Всего файлов в структуре: {total_files_in_structure}*")
        else:
            lines.append("*Директории пусты*")

        lines.append("\n---")

    # ПОЛНОЕ СОДЕРЖИМОЕ ФАЙЛОВ
    if project_files["full_content"]:
        lines.append("\n### Содержимое файлов (прикладной код)\n")

        text_files = [f for f in project_files["full_content"] if not is_binary_file(f)]
        binary_files = [f for f in project_files["full_content"] if is_binary_file(f)]

        if not text_files:
            lines.append("*В проекте не найдено текстовых файлов для анализа*\n")
        else:
            lines.append(
                f"**Найдено файлов для анализа:** {len(text_files)} (исключено {len(binary_files)} бинарных файлов)\n"
            )

            file_count = 0
            error_count = 0

            for file_path in text_files:
                display_path = get_relative_path_for_display(file_path, proj_dir)
                lines.append(f"#### `{display_path}`\n")

                content, encoding_or_error = read_file_content(file_path)

                if content is not None:
                    lang = get_language_for_file(file_path)
                    lines.append(f"*Кодировка: {encoding_or_error}*\n")
                    lines.append(f"```{lang}")
                    lines.append(content.rstrip())
                    lines.append("```\n")
                    file_count += 1
                else:
                    lines.append(f"*[Ошибка чтения файла: {encoding_or_error}]*\n")
                    error_count += 1

                lines.append("---")

            lines.append("\n### Статистика по файлам\n")
            lines.append(f"- **Успешно обработано:** {file_count}")
            lines.append(f"- **Бинарных (пропущено):** {len(binary_files)}")
            if error_count > 0:
                lines.append(f"- **Ошибок чтения:** {error_count}")
            lines.append(f"- **Всего найдено:** {len(project_files['full_content'])}")

    lines.append(f"\n---\n")

    return "\n".join(lines)


def main():
    args = parse_arguments()

    script_dir = get_script_directory()
    ewp_file_path = find_ewp_file(script_dir, args.input_file, args.proj_dir)

    if not ewp_file_path:
        print(f"\n[-] Ошибка: EWP файл не найден!")
        print(f"   Искали: {args.input_file}")
        print(f"   В PROJ_DIR: {args.proj_dir}")
        print(f"   В директории скрипта: {script_dir}")
        sys.exit(1)

    # Жестко задаем выходной файл из конфигурации конвейера
    output_file_path = cfg.output_file

    print("=" * 60)
    print("ГЕНЕРАТОР ДОКУМЕНТАЦИИ IAR ПРОЕКТА")
    print("=" * 60)
    print(f"Директория скрипта: {script_dir}")
    print(f"Найден EWP файл: {ewp_file_path}")
    print(f"Выходной файл: {output_file_path}")
    print(f"PROJ_DIR: {args.proj_dir}")
    print()

    print("Анализ EWP файла...")
    project_files = parse_ewp_file(ewp_file_path, args.proj_dir)

    if not project_files["structure_only"] and not project_files["full_content"]:
        print("\nПредупреждение: не найдено валидных файлов для обработки")
        sys.exit(0)

    print()
    print("Генерация Markdown содержимого...")

    # Генерируем содержимое
    markdown_content = generate_markdown_content(
        project_files, args.proj_dir, ewp_file_path.name
    )

    # Проверяем существование файла (не создаем шапку, просто дописываем)
    if not output_file_path.exists():
        print(f"\n[*] Файл {output_file_path} не найден, создаем новый...")
        with open(output_file_path, "w", encoding="utf-8") as f:
            f.write("# IAR Project Analysis\n\n")

    # Дописываем в конец файла
    if append_to_file(output_file_path, markdown_content):
        print(f"\n[+] Результат дописан в конец файла: {output_file_path}")

        # Вывод статистики в консоль
        print("\nСтатистика обработки:")
        print(
            f"   Файлов в группах firmware/libs/middleware: {len(project_files['structure_only'])}"
        )
        print(f"   Файлов для полного анализа: {len(project_files['full_content'])}")

        if project_files["full_content"]:
            binary_count = sum(
                1 for f in project_files["full_content"] if is_binary_file(f)
            )
            text_count = len(project_files["full_content"]) - binary_count
            print(f"\n   Файлы для полного анализа:")
            print(f"   - Текстовых: {text_count}")
            print(f"   - Бинарных (пропущено): {binary_count}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
