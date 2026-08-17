#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Модуль для загрузки эталонных файлов IAR
"""

import os
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple
from config import IARConfig, TEMPLATE_NAMES


class TemplateLoader:
    """Класс для загрузки эталонных файлов IAR"""
    
    def __init__(self, templates_dir: Path, config: IARConfig = None):
        """
        Инициализация загрузчика эталонов
        
        :param templates_dir: Путь к директории с эталонными файлами
        :param config: Конфигурация
        """
        self.templates_dir = Path(templates_dir)
        self.config = config or IARConfig()
        self.template_files = self._check_templates()
    
    def _check_templates(self) -> Dict[str, Path]:
        """
        Проверка наличия всех эталонных файлов
        
        :return: Словарь с путями к эталонным файлам
        :raises FileNotFoundError: Если какой-то эталонный файл не найден
        """
        template_files = {}
        
        for file_type, filename in self.config.template_names.items():
            file_path = self.templates_dir / filename
            if not file_path.exists():
                raise FileNotFoundError(
                    f"Эталонный файл не найден: {file_path}\n"
                    f"Поместите файл {filename} в папку {self.templates_dir}"
                )
            template_files[file_type] = file_path
        
        return template_files
    
    def load_ewp_template(self) -> Tuple[ET.ElementTree, ET.Element]:
        """
        Загрузка эталонного .ewp файла
        
        :return: Кортеж (дерево XML, корневой элемент)
        """
        tree = ET.parse(self.template_files['ewp'])
        root = tree.getroot()
        return tree, root
    
    def load_ewd_template(self) -> Tuple[ET.ElementTree, ET.Element]:
        """
        Загрузка эталонного .ewd файла
        
        :return: Кортеж (дерево XML, корневой элемент)
        """
        tree = ET.parse(self.template_files['ewd'])
        root = tree.getroot()
        return tree, root
    
    def load_ewt_template(self) -> Tuple[ET.ElementTree, ET.Element]:
        """
        Загрузка эталонного .ewt файла
        
        :return: Кортеж (дерево XML, корневой элемент)
        """
        tree = ET.parse(self.template_files['ewt'])
        root = tree.getroot()
        return tree, root
    
    def load_eww_template(self) -> str:
        """
        Загрузка эталонного .eww файла
        
        :return: Содержимое файла как строка
        """
        with open(self.template_files['eww'], 'r', encoding='utf-8') as f:
            return f.read()
    
    def extract_configurations(self) -> list:
        """
        Извлечение списка конфигураций из эталонного .ewp файла
        
        :return: Список конфигураций
        """
        try:
            tree, root = self.load_ewp_template()
            configurations = []
            
            for config in root.findall('.//configuration/name'):
                if config.text:
                    configurations.append(config.text)
            
            return configurations or self.config.default_configs
        except Exception:
            return self.config.default_configs
    
    def get_template_info(self) -> Dict:
        """
        Получение информации об эталонных файлах
        
        :return: Словарь с информацией
        """
        info = {}
        for file_type, file_path in self.template_files.items():
            info[file_type] = {
                'path': str(file_path),
                'size': file_path.stat().st_size,
                'modified': file_path.stat().st_mtime
            }
        return info