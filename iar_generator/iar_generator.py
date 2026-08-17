#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Основной модуль генератора IAR файлов
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

from config import IARConfig
from file_finder import FileFinder
from path_normalizer import PathNormalizer
from xml_formatter import XMLFormatter
from template_loader import TemplateLoader


class IARProjectGenerator:
    """
    Генератор файлов IAR проекта (ewp, ewd, eww, ewt) с использованием эталонных файлов
    """
    
    def __init__(self, project_path: str, project_name: str, script_dir: str, output_dir: str = None):
        """
        Инициализация генератора
        
        :param project_path: Путь к корневой директории проекта
        :param project_name: Имя проекта
        :param script_dir: Директория, откуда запущен скрипт
        :param output_dir: Директория для выходных файлов (по умолчанию: {project_path}/iar)
        """
        self.project_path = Path(project_path)
        if not self.project_path.exists():
            raise FileNotFoundError(f"Проект не найден: {project_path}")
        
        self.project_name = project_name
        self.script_dir = Path(script_dir)
        
        # Конфигурация
        self.config = IARConfig()
        
        # Директория с эталонными файлами
        self.templates_dir = self.script_dir / 'ewarm'
        
        # Загрузчик эталонов
        self.template_loader = TemplateLoader(self.templates_dir, self.config)
        
        # Поисковик файлов
        self.file_finder = FileFinder(self.project_path, self.config)
        
        # Нормализатор путей
        self.path_normalizer = PathNormalizer()
        
        # Форматтер XML
        self.xml_formatter = XMLFormatter()
        
        # Выходная директория для IAR файлов
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = self.project_path / 'iar'
        
        # Создаём выходную директорию
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Пути к генерируемым файлам
        self.ewp_file = self.output_dir / f"{self.project_name}.ewp"
        self.ewd_file = self.output_dir / f"{self.project_name}.ewd"
        self.eww_file = self.output_dir / f"{self.project_name}.eww"
        self.ewt_file = self.output_dir / f"{self.project_name}.ewt"
        
        # Конфигурации проекта (определяем из эталонного файла)
        self.configurations = self.template_loader.extract_configurations()
        
        # Информация о проекте
        self.project_info = {
            'name': project_name,
            'path': self.project_path,
            'chip': self.config.chip_info['default'],
            'chip_family': self.config.chip_info['family'],
            'fpu': self.config.chip_info['fpu']
        }
        
        self._print_init_info()
    
    def _print_init_info(self):
        """Вывод информации при инициализации"""
        print("\n" + "=" * 70)
        print(f"Генератор IAR файлов для проекта: {self.project_name}")
        print("=" * 70)
        print(f"Корень проекта: {self.project_path}")
        print(f"Директория скрипта: {self.script_dir}")
        print(f"Эталонные файлы: {self.templates_dir}")
        print(f"Выходная директория: {self.output_dir}")
        print(f"Конфигурации: {', '.join(self.configurations)}")
        print("=" * 70)
    
    def _create_folder_groups(self, parent_elem, folder_tree, current_path):
        """
        Рекурсивное создание групп на основе дерева папок
        
        :param parent_elem: Родительский XML элемент
        :param folder_tree: Дерево папок
        :param current_path: Текущий путь
        """
        if '__files__' in folder_tree:
            for file_path in folder_tree['__files__']:
                file_elem = ET.SubElement(parent_elem, "file")
                name_elem = ET.SubElement(file_elem, "name")
                name_elem.text = file_path
                name_elem.tail = "\n"
        
        for folder_name, sub_tree in folder_tree.items():
            if folder_name != '__files__':
                group = ET.SubElement(parent_elem, "group")
                name_elem = ET.SubElement(group, "name")
                name_elem.text = folder_name
                name_elem.tail = "\n"
                new_path = f"{current_path}\\{folder_name}" if current_path else folder_name
                self._create_folder_groups(group, sub_tree, new_path)
    
    def _build_folder_tree(self, all_files, existing_paths):
        """
        Построение дерева папок из списка файлов
        
        :param all_files: Список всех файлов
        :param existing_paths: Множество существующих путей
        :return: Дерево папок
        """
        folder_tree = {}
        
        for file_path in all_files:
            file_path_win = self.path_normalizer.normalize_for_windows(file_path)
            full_path = f"$PROJ_DIR$\\..\\{file_path_win}"
            
            # Пропускаем уже существующие файлы
            if full_path in existing_paths:
                continue
            
            # Разбиваем путь на компоненты
            path_parts = Path(file_path).parts
            
            # Определяем, с какого уровня начинать
            # Если путь начинается с 'project', убираем этот уровень
            start_index = 0
            if len(path_parts) > 0 and path_parts[0] == 'project':
                start_index = 1
            
            # Добавляем файл в дерево, начиная с нужного уровня
            current_level = folder_tree
            for i, part in enumerate(path_parts[start_index:-1]):
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]
            
            if '__files__' not in current_level:
                current_level['__files__'] = []
            current_level['__files__'].append(full_path)
        
        return folder_tree
    
    def update_xml_with_file_list(self, xml_root, all_files):
        """
        Обновление XML дерева, добавляя все найденные файлы
        Сохраняем существующие группы из эталона и добавляем новые
        
        :param xml_root: Корневой элемент XML
        :param all_files: Список всех файлов
        :return: Обновленный XML корень
        """
        # Находим все существующие группы и файлы в эталоне
        existing_paths = set()
        for file_elem in xml_root.findall('.//file/name'):
            if file_elem.text:
                existing_paths.add(file_elem.text)
        
        # Строим дерево папок для новых файлов
        folder_tree = self._build_folder_tree(all_files, existing_paths)
        
        # Добавляем новые файлы в корень проекта
        if folder_tree:
            # Ищем или создаем корневую группу для новых файлов
            root_group = None
            for group in xml_root.findall('group'):
                if group.find('name') is not None and group.find('name').text == 'project':
                    root_group = group
                    break
            
            if root_group is None:
                root_group = ET.SubElement(xml_root, 'group')
                ET.SubElement(root_group, 'name').text = 'project'
            
            self._create_folder_groups(root_group, folder_tree, "")
        
        return xml_root
    
    def update_include_paths(self, xml_root, include_paths):
        """
        Обновление include paths в настройках ICCARM
        
        :param xml_root: Корневой элемент XML
        :param include_paths: Список путей для include
        :return: Обновленный XML корень
        """
        # Ищем настройки ICCARM
        for config in xml_root.findall('.//configuration'):
            for settings in config.findall('settings'):
                name_elem = settings.find('name')
                if name_elem is not None and name_elem.text == 'ICCARM':
                    data = settings.find('data')
                    if data is not None:
                        # Ищем существующую опцию CCIncludePath2 или создаем новую
                        include_option = None
                        for option in data.findall('option'):
                            opt_name = option.find('name')
                            if opt_name is not None and opt_name.text == 'CCIncludePath2':
                                include_option = option
                                # Удаляем все существующие state
                                for state in include_option.findall('state'):
                                    include_option.remove(state)
                                break
                        
                        if include_option is None:
                            include_option = ET.SubElement(data, 'option')
                            ET.SubElement(include_option, 'name').text = 'CCIncludePath2'
                        
                        # Добавляем новые пути
                        for path in include_paths:
                            state_elem = ET.SubElement(include_option, 'state')
                            state_elem.text = path
        
        return xml_root
    
    def update_asm_include_paths(self, xml_root, asm_paths):
        """
        Обновление include paths для ассемблера
        
        :param xml_root: Корневой элемент XML
        :param asm_paths: Список путей для ассемблера
        :return: Обновленный XML корень
        """
        for config in xml_root.findall('.//configuration'):
            for settings in config.findall('settings'):
                name_elem = settings.find('name')
                if name_elem is not None and name_elem.text == 'AARM':
                    data = settings.find('data')
                    if data is not None:
                        # Ищем или создаем опцию AUserIncludes
                        include_option = None
                        for option in data.findall('option'):
                            opt_name = option.find('name')
                            if opt_name is not None and opt_name.text == 'AUserIncludes':
                                include_option = option
                                for state in include_option.findall('state'):
                                    include_option.remove(state)
                                break
                        
                        if include_option is None:
                            include_option = ET.SubElement(data, 'option')
                            ET.SubElement(include_option, 'name').text = 'AUserIncludes'
                        
                        for path in asm_paths:
                            state_elem = ET.SubElement(include_option, 'state')
                            state_elem.text = path
        
        return xml_root
    
    def update_linker_scripts(self, xml_root, linker_scripts):
        """
        Обновление путей к linker script в настройках ILINK
        
        :param xml_root: Корневой элемент XML
        :param linker_scripts: Список linker script файлов
        :return: Обновленный XML корень
        """
        if not linker_scripts:
            return xml_root
        
        # Используем первый найденный linker script
        linker_script = linker_scripts[0]
        linker_path = f"$PROJ_DIR$\\..\\{linker_script}"
        
        for config in xml_root.findall('.//configuration'):
            for settings in config.findall('settings'):
                name_elem = settings.find('name')
                if name_elem is not None and name_elem.text == 'ILINK':
                    data = settings.find('data')
                    if data is not None:
                        # Обновляем IlinkIcfFile
                        for option in data.findall('option'):
                            opt_name = option.find('name')
                            if opt_name is not None and opt_name.text == 'IlinkIcfFile':
                                state = option.find('state')
                                if state is not None:
                                    state.text = linker_path
                                break
        
        return xml_root
    
    def update_project_name_in_ewp(self, xml_root):
        """
        Обновление имени проекта в различных местах .ewp файла
        
        :param xml_root: Корневой элемент XML
        :return: Обновленный XML корень
        """
        # Обновляем имена выходных файлов
        for config in xml_root.findall('.//configuration'):
            # Обновляем в General settings
            for settings in config.findall('settings'):
                name_elem = settings.find('name')
                if name_elem is not None and name_elem.text == 'General':
                    data = settings.find('data')
                    if data is not None:
                        for option in data.findall('option'):
                            opt_name = option.find('name')
                            if opt_name is not None:
                                # Обновляем пути ExePath, ObjPath, ListPath, BrowseInfoPath
                                if opt_name.text in ['ExePath', 'ObjPath', 'ListPath', 'BrowseInfoPath']:
                                    for state in option.findall('state'):
                                        if state.text and 'Project' in state.text:
                                            # Сохраняем структуру пути, меняем только имя
                                            parts = state.text.split('\\')
                                            if parts and parts[0] == 'Project':
                                                parts[0] = self.project_name
                                                state.text = '\\'.join(parts)
                
                # Обновляем в ILINK settings
                if name_elem is not None and name_elem.text == 'ILINK':
                    data = settings.find('data')
                    if data is not None:
                        for option in data.findall('option'):
                            opt_name = option.find('name')
                            if opt_name is not None:
                                if opt_name.text == 'IlinkOutputFile':
                                    for state in option.findall('state'):
                                        if state.text and 'Project' in state.text:
                                            state.text = state.text.replace('Project', self.project_name)
        
        return xml_root
    
    def generate_ewp_file(self, source_files, header_files, linker_scripts):
        """
        Генерация .ewp файла проекта на основе эталона
        
        :param source_files: Список исходных файлов
        :param header_files: Список заголовочных файлов
        :param linker_scripts: Список linker script файлов
        """
        print(f"\n[*] Генерация {self.ewp_file.name}...")
        
        # Загружаем эталонный файл
        tree, root = self.template_loader.load_ewp_template()
        
        # Нормализуем все пути в эталонном файле
        root = self.path_normalizer.normalize_all_paths_in_xml(root)
        
        # Обновляем имя проекта
        root = self.update_project_name_in_ewp(root)
        
        # Добавляем все исходные файлы
        all_files = source_files + header_files
        root = self.update_xml_with_file_list(root, all_files)
        
        # Обновляем include paths
        include_paths = self.file_finder.get_include_paths()
        root = self.update_include_paths(root, include_paths)
        
        # Обновляем asm include paths
        asm_paths = self.file_finder.get_asm_include_paths()
        root = self.update_asm_include_paths(root, asm_paths)
        
        # Обновляем linker scripts
        root = self.update_linker_scripts(root, linker_scripts)
        
        # Форматируем XML компактно
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_str += self.xml_formatter.format_compact(root)
        
        with open(self.ewp_file, 'w', encoding='UTF-8') as f:
            f.write(xml_str)
        
        print(f"[OK] Сгенерирован {self.ewp_file.name}")
        print(f"      Добавлено файлов: {len(all_files)}")
    
    def generate_ewd_file(self):
        """Генерация .ewd файла на основе эталона"""
        print(f"\n[*] Генерация {self.ewd_file.name}...")
        
        # Загружаем эталонный файл
        tree, root = self.template_loader.load_ewd_template()
        
        # Нормализуем все пути
        root = self.path_normalizer.normalize_all_paths_in_xml(root)
        
        # Форматируем XML
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_str += self.xml_formatter.format_compact(root)
        
        with open(self.ewd_file, 'w', encoding='UTF-8') as f:
            f.write(xml_str)
        
        print(f"[OK] Сгенерирован {self.ewd_file.name}")
    
    def generate_eww_file(self):
        """Генерация .eww файла на основе эталона"""
        print(f"\n[*] Генерация {self.eww_file.name}...")
        
        # Загружаем эталонный файл
        content = self.template_loader.load_eww_template()
        
        # Заменяем имя проекта
        content = content.replace('Project', self.project_name)
        
        # Нормализуем пути
        content = self.path_normalizer.normalize_eww_content(content)
        
        with open(self.eww_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"[OK] Сгенерирован {self.eww_file.name}")
    
    def generate_ewt_file(self):
        """Генерация .ewt файла на основе эталона"""
        print(f"\n[*] Генерация {self.ewt_file.name}...")
        
        # Загружаем эталонный файл
        tree, root = self.template_loader.load_ewt_template()
        
        # Нормализуем пути
        root = self.path_normalizer.normalize_all_paths_in_xml(root)
        
        # Форматируем XML
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_str += self.xml_formatter.format_compact(root)
        
        # Дополнительная обработка для самозакрывающихся тегов
        xml_str = xml_str.replace('></extraArgs>', '/>')
        xml_str = xml_str.replace('></extensions>', '/>')
        xml_str = xml_str.replace('></cmdline>', '/>')
        
        with open(self.ewt_file, 'w', encoding='UTF-8') as f:
            f.write(xml_str)
        
        print(f"[OK] Сгенерирован {self.ewt_file.name}")
    
    def generate_readme(self):
        """Генерация README файла с описанием сгенерированных файлов"""
        readme_file = self.output_dir / "README_IAR_FILES.txt"
        
        include_paths = self.file_finder.get_include_paths()
        
        content = f"""# IAR Project Files for {self.project_name}

Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Сгенерированные файлы

1. **{self.project_name}.ewp** - основной файл проекта
   - Конфигурации: {', '.join(self.configurations)}
   - Настройки из эталонного файла
   - Все заголовочные файлы (.h) добавлены в проект
   - Правильные include paths для поиска .h файлов
   - Сохранена структура папок из файловой системы
   - Нормализованы пути (убраны множественные выходы из директории)

2. **{self.project_name}.ewd** - настройки отладчика (из эталона)

3. **{self.project_name}.eww** - рабочее пространство
   - Ссылка на проект

4. **{self.project_name}.ewt** - настройки C-STAT (из эталона)

## Пути для поиска заголовочных файлов (include paths)

Следующие пути автоматически добавлены в проект:
{chr(10).join(include_paths)}

## Использование

1. Откройте IAR Embedded Workbench
2. Выберите File -> Open -> Workspace...
3. Откройте файл: `{self.eww_file}`
4. Выберите нужную конфигурацию в выпадающем списке
5. Стройте проект (F7) или отлаживайте (Ctrl+D)

## Важно

- Все пути нормализованы: множественные `..\\..\\..\\` заменены на один `..\\`
- Эталонные настройки загружены из {self.templates_dir}
"""
        
        with open(readme_file, 'w', encoding='UTF-8') as f:
            f.write(content)
        
        print(f"[OK] Сгенерирован README: {readme_file}")
    
    def generate_all(self):
        """Генерация всех файлов IAR проекта"""
        print("\n" + "=" * 70)
        print(f"Генерация IAR файлов для проекта {self.project_name}")
        print("=" * 70)
        
        # Поиск исходных файлов
        source_files, header_files = self.file_finder.find_source_files()
        
        # Поиск linker scripts
        linker_scripts = self.file_finder.find_linker_scripts()
        
        if not source_files and not header_files:
            print("[WARN] Внимание: файлы не найдены!")
            return
        
        print(f"\n[*] Статистика:")
        print(f"      - Исходных файлов: {len(source_files)}")
        print(f"      - Заголовочных файлов: {len(header_files)}")
        print(f"      - Linker scripts: {len(linker_scripts)}")
        
        # Генерация файлов
        self.generate_ewp_file(source_files, header_files, linker_scripts)
        self.generate_ewd_file()
        self.generate_eww_file()
        self.generate_ewt_file()
        self.generate_readme()
        
        print("\n" + "=" * 70)
        print("Генерация IAR файлов завершена успешно!")
        print("=" * 70)
        print(f"\nСгенерированные файлы находятся в:")
        print(f"   {self.output_dir}")
        print("\nФайлы:")
        print(f"   {self.ewp_file.name}")
        print(f"   {self.ewd_file.name}")
        print(f"   {self.eww_file.name}")
        print(f"   {self.ewt_file.name}")
        print(f"   README_IAR_FILES.txt")
        print("=" * 70)