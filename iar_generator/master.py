#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Мастер-скрипт для управления генерацией IAR файлов проекта

Использование:
  python master.py <команда> [аргументы]

Команды:
  generate    - Генерация IAR файлов
  info        - Информация о проекте
  check       - Проверка структуры проекта
  clean       - Очистка сгенерированных файлов

Примеры:
  python master.py generate C:\\Projects\\example loop_example_project
  python master.py info C:\\Projects\\example
  python master.py check C:\\Projects\\example
  python master.py clean C:\\Projects\\example
"""

import os
import sys
import argparse
from pathlib import Path

# Добавляем текущую директорию в путь для импорта модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from iar_generator import IARProjectGenerator
from file_finder import FileFinder
from config import IARConfig


def print_header(text):
    """Вывод заголовка"""
    print("\n" + "=" * 70)
    print(f" {text}")
    print("=" * 70)


def print_success(text):
    """Вывод сообщения об успехе"""
    print(f"[OK] {text}")


def print_error(text):
    """Вывод сообщения об ошибке"""
    print(f"[ERROR] {text}")


def print_warning(text):
    """Вывод предупреждения"""
    print(f"[WARN] {text}")


def print_info(text):
    """Вывод информационного сообщения"""
    print(f"[INFO] {text}")


def cmd_generate(args):
    """Команда генерации IAR файлов"""
    print_header(f"Генерация IAR файлов для проекта: {args.project_name}")

    try:
        # Директория скрипта
        script_dir = os.path.dirname(os.path.abspath(__file__))

        # Создание генератора
        generator = IARProjectGenerator(
            project_path=args.project_path,
            project_name=args.project_name,
            script_dir=script_dir,
            output_dir=args.output,
        )

        # Генерация файлов
        generator.generate_all()

        print_success("Генерация завершена")
        return 0

    except Exception as e:
        print_error(f"Ошибка генерации: {e}")
        import traceback

        traceback.print_exc()
        return 1


def cmd_info(args):
    """Команда вывода информации о проекте"""
    print_header(f"Информация о проекте: {args.project_path}")

    project_path = Path(args.project_path)
    if not project_path.exists():
        print_error(f"Директория не найдена: {project_path}")
        return 1

    config = IARConfig()
    finder = FileFinder(project_path, config)

    # Поиск файлов
    source_files, header_files = finder.find_source_files()
    linker_scripts = finder.find_linker_scripts()
    freertos_dir = finder.find_freertos_config()

    # Вывод информации
    print("\n[*] Основная информация:")
    print(f"      Путь: {project_path.absolute()}")
    print(
        f"      Размер: {sum(f.stat().st_size for f in project_path.rglob('*') if f.is_file()) / (1024*1024):.2f} MB"
    )
    print(f"      Файлов всего: {len(list(project_path.rglob('*')))}")

    print("\n[*] Статистика по исходным файлам:")
    print(f"      Исходных файлов: {len(source_files)}")
    print(f"      Заголовочных файлов: {len(header_files)}")
    print(f"      Linker scripts: {len(linker_scripts)}")

    if freertos_dir:
        print("\n[*] FreeRTOS:")
        print(f"      FreeRTOSConfig.h найден в: {freertos_dir}")
    else:
        print("\n[*] FreeRTOS:")
        print("      FreeRTOSConfig.h не найден")

    # Примеры первых нескольких файлов
    if source_files:
        print("\n[*] Примеры исходных файлов (первые 5):")
        for f in source_files[:5]:
            print(f"      - {f}")

    if header_files:
        print("\n[*] Примеры заголовочных файлов (первые 5):")
        for f in header_files[:5]:
            print(f"      - {f}")

    # Проверка наличия IAR директории
    iar_dir = project_path / "iar"
    if iar_dir.exists():
        ewp_files = list(iar_dir.glob("*.ewp"))
        if ewp_files:
            print("\n[*] IAR файлы найдены:")
            for f in ewp_files:
                print(f"      - {f.name}")

    print_success("Информация собрана")
    return 0


def cmd_check(args):
    """Команда проверки структуры проекта"""
    print_header(f"Проверка структуры проекта: {args.project_path}")

    project_path = Path(args.project_path)
    if not project_path.exists():
        print_error(f"Директория не найдена: {project_path}")
        return 1

    issues = []
    warnings = []

    # Проверка наличия исходных файлов
    source_files = list(project_path.rglob("*.c")) + list(project_path.rglob("*.cpp"))
    if not source_files:
        issues.append("Не найдены исходные файлы (.c, .cpp)")

    # Проверка наличия заголовочных файлов
    header_files = list(project_path.rglob("*.h")) + list(project_path.rglob("*.hpp"))
    if not header_files:
        warnings.append("Не найдены заголовочные файлы (.h, .hpp)")

    # Проверка наличия FreeRTOSConfig.h
    freertos_config = None
    for root, dirs, files in os.walk(project_path):
        if "FreeRTOSConfig.h" in files:
            freertos_config = Path(root) / "FreeRTOSConfig.h"
            break

    if not freertos_config:
        warnings.append("FreeRTOSConfig.h не найден")
    else:
        print_info(
            f"FreeRTOSConfig.h найден: {freertos_config.relative_to(project_path)}"
        )

    # Проверка наличия linker script
    icf_files = list(project_path.rglob("*.icf"))
    if not icf_files:
        issues.append("Не найден linker script файл (.icf)")

    # Проверка наличия директории для IAR файлов
    iar_dir = project_path / "iar"
    if not iar_dir.exists():
        warnings.append("Директория 'iar' не существует (будет создана при генерации)")

    # Проверка наличия эталонных файлов
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    templates_dir = script_dir / "ewarm"

    if not templates_dir.exists():
        issues.append(f"Директория с эталонами не найдена: {templates_dir}")
    else:
        template_files = ["project.ewp", "project.ewd", "project.eww", "project.ewt"]
        missing_templates = []
        for tf in template_files:
            if not (templates_dir / tf).exists():
                missing_templates.append(tf)

        if missing_templates:
            issues.append(
                f"Отсутствуют эталонные файлы: {', '.join(missing_templates)}"
            )

    # Вывод результатов
    if issues:
        print("\n[!] Критические проблемы:")
        for issue in issues:
            print(f"      - {issue}")

    if warnings:
        print("\n[!] Предупреждения:")
        for warning in warnings:
            print(f"      - {warning}")

    if not issues and not warnings:
        print_success("Проблем не обнаружено")
    elif issues:
        print_error(f"Обнаружено {len(issues)} критических проблем")
        return 1
    else:
        print_warning(f"Обнаружено {len(warnings)} предупреждений")

    return 0


def cmd_clean(args):
    """Команда очистки сгенерированных файлов"""
    print_header(f"Очистка IAR файлов: {args.project_path}")

    project_path = Path(args.project_path)
    iar_dir = project_path / "iar"

    if not iar_dir.exists():
        print_warning("Директория 'iar' не найдена")
        return 0

    # Поиск IAR файлов
    iar_files = []
    iar_files.extend(iar_dir.glob("*.ewp"))
    iar_files.extend(iar_dir.glob("*.ewd"))
    iar_files.extend(iar_dir.glob("*.eww"))
    iar_files.extend(iar_dir.glob("*.ewt"))
    iar_files.extend(iar_dir.glob("README_IAR_FILES.txt"))

    if not iar_files:
        print_info("IAR файлы не найдены")
        return 0

    print(f"\n[*] Найдено файлов для удаления: {len(iar_files)}")
    for f in iar_files:
        print(f"      - {f.name}")

    if not args.force:
        response = input("\nУдалить эти файлы? (y/N): ")
        if response.lower() != "y":
            print_info("Операция отменена")
            return 0

    # Удаление файлов
    deleted = 0
    for f in iar_files:
        try:
            f.unlink()
            print(f"      [DEL] {f.name}")
            deleted += 1
        except Exception as e:
            print_error(f"Ошибка удаления {f.name}: {e}")

    # Попытка удалить пустую директорию
    try:
        if iar_dir.exists() and not any(iar_dir.iterdir()):
            iar_dir.rmdir()
            print(f"      [DEL] Директория {iar_dir}")
    except Exception:
        pass

    print_success(f"Удалено {deleted} файлов")
    return 0


def main():
    """Основная функция мастер-скрипта"""
    parser = argparse.ArgumentParser(
        description="Мастер-скрипт для управления IAR проектами",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    subparsers = parser.add_subparsers(dest="command", help="Команда")

    # Команда generate
    parser_generate = subparsers.add_parser("generate", help="Генерация IAR файлов")
    parser_generate.add_argument(
        "project_path", help="Путь к корневой директории проекта"
    )
    parser_generate.add_argument("project_name", help="Имя проекта")
    parser_generate.add_argument(
        "-o", "--output", help="Выходная директория для IAR файлов"
    )

    # Команда info
    parser_info = subparsers.add_parser("info", help="Информация о проекте")
    parser_info.add_argument("project_path", help="Путь к корневой директории проекта")

    # Команда check
    parser_check = subparsers.add_parser("check", help="Проверка структуры проекта")
    parser_check.add_argument("project_path", help="Путь к корневой директории проекта")

    # Команда clean
    parser_clean = subparsers.add_parser("clean", help="Очистка сгенерированных файлов")
    parser_clean.add_argument("project_path", help="Путь к корневой директории проекта")
    parser_clean.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Принудительное удаление без подтверждения",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Выполнение команды
    if args.command == "generate":
        return cmd_generate(args)
    elif args.command == "info":
        return cmd_info(args)
    elif args.command == "check":
        return cmd_check(args)
    elif args.command == "clean":
        return cmd_clean(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
