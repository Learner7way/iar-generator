#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для сбора информации из .ewp файлов проектов IAR.
Использование: python pyIAR_xmlValue.py "C:\Projects\example project"
Результат дописывается в конец файла py_out.md в текущей директории.
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
import re
from datetime import datetime

def find_ewp_files(project_dir):
    """Поиск всех .ewp файлов в директории проекта."""
    project_path = Path(project_dir)
    if not project_path.exists():
        print(f"Ошибка: Директория {project_dir} не существует")
        return None
    
    return list(project_path.rglob("*.ewp"))

def parse_xml_file(file_path):
    """Парсинг XML файла."""
    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
        return None

def extract_include_paths(settings_data):
    """Извлечение путей включения из секции ICCARM."""
    paths = []
    for option in settings_data.findall('.//option'):
        name_elem = option.find('name')
        if name_elem is not None and name_elem.text == 'CCIncludePath2':
            for state in option.findall('state'):
                if state.text and state.text.strip():
                    paths.append(state.text.strip())
    return paths

def extract_asm_include_paths(settings_data):
    """Извлечение путей включения для ассемблера из секции AARM."""
    paths = []
    for option in settings_data.findall('.//option'):
        name_elem = option.find('name')
        if name_elem is not None and name_elem.text == 'AUserIncludes':
            for state in option.findall('state'):
                if state.text and state.text.strip():
                    paths.append(state.text.strip())
    return paths

def extract_defines(settings_data):
    """Извлечение определений препроцессора из секции ICCARM."""
    defines = []
    for option in settings_data.findall('.//option'):
        name_elem = option.find('name')
        if name_elem is not None and name_elem.text == 'CCDefines':
            for state in option.findall('state'):
                if state.text and state.text.strip():
                    defines.append(state.text.strip())
    return defines

def extract_asm_defines(settings_data):
    """Извлечение определений для ассемблера из секции AARM."""
    defines = []
    for option in settings_data.findall('.//option'):
        name_elem = option.find('name')
        if name_elem is not None and name_elem.text == 'ADefines':
            for state in option.findall('state'):
                if state.text and state.text.strip():
                    defines.append(state.text.strip())
    return defines

def extract_linker_files(settings_data):
    """Извлечение файлов линкера из секции ILINK."""
    linker_files = []
    for option in settings_data.findall('.//option'):
        name_elem = option.find('name')
        if name_elem is not None and name_elem.text == 'IlinkIcfFile':
            for state in option.findall('state'):
                if state.text and state.text.strip():
                    linker_files.append(state.text.strip())
    return linker_files

def process_ewp_file(ewp_path):
    """Обработка EWP файла проекта."""
    result = {
        'path': ewp_path,
        'configurations': {}
    }
    
    root = parse_xml_file(ewp_path)
    if root is None:
        return result
    
    # Получаем все конфигурации
    for config in root.findall('.//configuration'):
        config_name_elem = config.find('name')
        if config_name_elem is None:
            continue
        
        current_config = config_name_elem.text
        config_data = {
            'include_paths': [],
            'asm_include_paths': [],
            'defines': [],
            'asm_defines': [],
            'linker_files': []
        }
        
        # Обрабатываем каждую секцию настроек
        for settings in config.findall('settings'):
            name_elem = settings.find('name')
            if name_elem is None:
                continue
            
            data = settings.find('data')
            if data is None:
                continue
            
            if name_elem.text == 'ICCARM':
                config_data['include_paths'].extend(extract_include_paths(data))
                config_data['defines'].extend(extract_defines(data))
            elif name_elem.text == 'AARM':
                config_data['asm_include_paths'].extend(extract_asm_include_paths(data))
                config_data['asm_defines'].extend(extract_asm_defines(data))
            elif name_elem.text == 'ILINK':
                config_data['linker_files'].extend(extract_linker_files(data))
        
        result['configurations'][current_config] = config_data
    
    return result

def format_output(results, project_dir):
    """Форматирование результатов в Markdown."""
    lines = []
    
    # Заголовок с датой
    lines.append(f"{'='*60}")
    
    for file_result in results:
        rel_path = os.path.relpath(file_result['path'], project_dir)
        lines.append(f"\n### {rel_path}")
        
        for config_name, config_data in file_result['configurations'].items():
            lines.append(f"\n#### Конфигурация: `{config_name}`")
            
            if config_data.get('include_paths'):
                lines.append("\n**Пути включения заголовочных файлов:**")
                for path in config_data['include_paths']:
                    lines.append(f"- `{path}`")
            
            if config_data.get('asm_include_paths'):
                lines.append("\n**Пути включения (Ассемблер):**")
                for path in config_data['asm_include_paths']:
                    lines.append(f"- `{path}`")
            
            if config_data.get('defines'):
                lines.append("\n**Определения препроцессора (C/C++):**")
                for define in config_data['defines']:
                    lines.append(f"- `{define}`")
            
            if config_data.get('asm_defines'):
                lines.append("\n**Определения (Ассемблер):**")
                for define in config_data['asm_defines']:
                    lines.append(f"- `{define}`")
            
            if config_data.get('linker_files'):
                lines.append("\n**Файлы линкера:**")
                for linker in config_data['linker_files']:
                    lines.append(f"- `{linker}`")
    
    lines.append(f"{'='*60}\n")
    
    return "\n".join(lines)

def append_to_file(file_path, new_content):
    """Дописывает новое содержимое в конец файла."""
    try:
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(new_content)
        return True
    except Exception as e:
        print(f"Ошибка при записи в файл {file_path}: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Использование: python pyIAR_xmlValue.py <путь_к_проекту>")
        print("Пример: python pyIAR_xmlValue.py \"C:\\Projects\\example project\"")
        sys.exit(1)
    
    project_dir = sys.argv[1]
    
    # Поиск .ewp файлов
    print(f"Поиск .ewp файлов в {project_dir}...")
    ewp_files = find_ewp_files(project_dir)
    
    if not ewp_files:
        print("Не найдено .ewp файлов в указанной директории")
        sys.exit(1)
    
    print(f"\nНайдено .ewp файлов: {len(ewp_files)}")
    
    # Обрабатываем каждый файл
    results = []
    for ewp_file in ewp_files:
        print(f"Обработка {ewp_file}...")
        results.append(process_ewp_file(ewp_file))
    
    # Форматируем результат
    new_content = format_output(results, project_dir)
    
    # Дописываем в конец файла py_out.txt
    output_file = Path.cwd() / "py_out.md"
    
    # Проверяем, существует ли файл, если нет - создаем с заголовком
    if not output_file.exists():
        print(f"\nФайл {output_file} не найден, создаем новый...")
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("# IAR Project Analysis\n\n")
    
    if append_to_file(output_file, new_content):
        print(f"\nРезультат дописан в конец файла {output_file}")
    else:
        print(f"\nОшибка при записи в файл {output_file}")
        sys.exit(1)

if __name__ == "__main__":
    main()