#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Модуль для поиска файлов в проекте
"""

import os
from pathlib import Path
from typing import Set, List, Tuple, Optional
from config import IARConfig


class FileFinder:
    """Класс для поиска файлов в проекте"""

    def __init__(self, project_path: Path, config: IARConfig = None):
        """
        Инициализация поисковика файлов

        :param project_path: Путь к корню проекта
        :param config: Конфигурация (опционально)
        """
        self.project_path = Path(project_path)
        self.config = config or IARConfig()

    def find_directories_with_files(
        self, base_dir: Path, file_extensions: Set[str], recursive: bool = True
    ) -> List[str]:
        """
        Универсальная функция для поиска директорий, содержащих файлы с указанными расширениями

        :param base_dir: Базовая директория для поиска
        :param file_extensions: Список расширений файлов для поиска
        :param recursive: Искать рекурсивно или только в корне
        :return: Список относительных путей к директориям
        """
        dirs_with_files = set()
        base_path = Path(base_dir)

        if not base_path.exists():
            return []

        if recursive:
            for root, dirs, files in os.walk(base_path):
                # Исключаем ненужные директории
                dirs[:] = [d for d in dirs if d not in self.config.exclude_dirs]

                for file in files:
                    if Path(file).suffix.lower() in file_extensions:
                        try:
                            rel_dir = Path(root).relative_to(self.project_path)
                            dirs_with_files.add(str(rel_dir))
                        except ValueError:
                            # Если не удается сделать относительным, используем абсолютный
                            dirs_with_files.add(str(root))
                        break
        else:
            # Только в текущей директории
            for item in base_path.iterdir():
                if item.is_dir() and item.name not in self.config.exclude_dirs:
                    for file in item.glob("*"):
                        if file.is_file() and file.suffix.lower() in file_extensions:
                            try:
                                rel_dir = item.relative_to(self.project_path)
                                dirs_with_files.add(str(rel_dir))
                            except ValueError:
                                dirs_with_files.add(str(item))
                            break

        return sorted(list(dirs_with_files))

    def find_source_files(self) -> Tuple[List[str], List[str]]:
        """
        Поиск всех исходных файлов в проекте с сохранением структуры

        :return: Кортеж (список исходных файлов, список заголовочных файлов)
        """
        source_files = []
        header_files = []

        print("\n[*] Поиск исходных файлов...")

        for root, dirs, files in os.walk(self.project_path):
            # Исключаем временные и бинарные директории
            dirs[:] = [d for d in dirs if d not in self.config.exclude_dirs]

            for file in files:
                file_ext = Path(file).suffix.lower()
                full_path = Path(root) / file

                try:
                    rel_path = full_path.relative_to(self.project_path)
                except ValueError:
                    # Если не удается сделать относительным, используем имя файла
                    rel_path = file

                if file_ext in self.config.source_extensions:
                    source_files.append(str(rel_path))
                    print(f"   [SRC] {rel_path}")
                elif file_ext in self.config.header_extensions:
                    header_files.append(str(rel_path))
                    print(f"   [HDR] {rel_path}")

        print(
            f"\n[OK] Найдено файлов: {len(source_files)} исходных, {len(header_files)} заголовочных"
        )
        return sorted(source_files), sorted(header_files)

    def find_linker_scripts(self) -> List[str]:
        """
        Поиск linker script файлов (.icf) в проекте

        :return: Список относительных путей к linker script файлам
        """
        icf_files = []

        # Ищем в mcu_platforms
        mcu_platforms_dir = self.project_path / "project" / "mcu_platforms"
        if mcu_platforms_dir.exists():
            icf_files.extend(list(mcu_platforms_dir.glob("**/*.icf")))

        # Ищем в корне проекта
        icf_files.extend(list(self.project_path.glob("*.icf")))

        # Ищем в папке iar
        iar_dir = self.project_path / "iar"
        if iar_dir.exists():
            icf_files.extend(list(iar_dir.glob("*.icf")))

        result = []
        for icf in icf_files:
            try:
                rel_path = icf.relative_to(self.project_path)
                result.append(str(rel_path))
                print(f"   [LINK] {rel_path}")
            except ValueError:
                result.append(str(icf))
                print(f"   [LINK] {icf}")

        return result

    def find_freertos_config(self) -> Optional[str]:
        """
        Поиск файла FreeRTOSConfig.h в проекте

        :return: Относительный путь к директории с FreeRTOSConfig.h или None
        """
        print("\n[*] Поиск FreeRTOSConfig.h...")

        # Сначала ищем во всем проекте
        for root, dirs, files in os.walk(self.project_path):
            if "FreeRTOSConfig.h" in files:
                try:
                    rel_path = Path(root).relative_to(self.project_path)
                    print(f"   [FOUND] FreeRTOSConfig.h в {rel_path}")
                    return str(rel_path)
                except ValueError:
                    print(f"   [FOUND] FreeRTOSConfig.h в {root}")
                    return str(root)

        # Если не нашли, проверяем типичные пути
        for path in self.config.freertos_config_paths:
            full_path = self.project_path / path / "FreeRTOSConfig.h"
            if full_path.exists():
                print(f"   [FOUND] FreeRTOSConfig.h в {path}")
                return path

        print("   [WARN] FreeRTOSConfig.h не найден")
        return None

    def get_include_paths(self) -> List[str]:
        """
        Формирование детального списка путей для поиска заголовочных файлов

        :return: Список путей для include
        """
        include_paths = [
            "$PROJ_DIR$\\..\\",  # Корень проекта
        ]

        # Ищем директории с .h файлами
        h_dirs = self.find_directories_with_files(
            self.project_path, self.config.header_extensions, recursive=True
        )

        for dir_path in h_dirs:
            include_paths.append(f"$PROJ_DIR$\\..\\{dir_path}")

        # Добавляем путь к FreeRTOSConfig.h если найден
        freertos_dir = self.find_freertos_config()
        if freertos_dir:
            freertos_path = f"$PROJ_DIR$\\..\\{freertos_dir}"
            if freertos_path not in include_paths:
                include_paths.append(freertos_path)
                print(f"   [ADD] FreeRTOS include path: {freertos_path}")

        # Удаляем дубликаты и сортируем
        include_paths = sorted(list(set(include_paths)))

        print("\n[*] Пути для поиска заголовочных файлов:")
        for path in include_paths:
            print(f"      {path}")

        return include_paths

    def get_asm_include_paths(self) -> List[str]:
        """
        Формирование списка путей для ассемблера

        :return: Список путей для ассемблера
        """
        asm_paths = [
            "$PROJ_DIR$",
        ]

        # Ищем директории с .s файлами
        asm_dirs = self.find_directories_with_files(
            self.project_path, {".s", ".asm"}, recursive=True
        )

        for dir_path in asm_dirs:
            asm_paths.append(f"$PROJ_DIR$\\..\\{dir_path}")

        # Добавляем путь к FreeRTOSConfig.h для ассемблера если нужно
        freertos_dir = self.find_freertos_config()
        if freertos_dir:
            freertos_path = f"$PROJ_DIR$\\..\\{freertos_dir}"
            if freertos_path not in asm_paths:
                asm_paths.append(freertos_path)

        return sorted(list(set(asm_paths)))
