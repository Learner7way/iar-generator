#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Модуль для нормализации путей в проекте
"""

import re
from pathlib import Path


class PathNormalizer:
    """Класс для нормализации путей"""
    
    @staticmethod
    def normalize_path(path):
        """
        Нормализация пути: заменяем множественные выходы из директории на один
        
        Например: $PROJ_DIR$\\..\\..\\..\\..\\Drivers\\... -> $PROJ_DIR$\\..\\Drivers\\...
        
        :param path: Исходный путь
        :return: Нормализованный путь
        """
        if not path or '$PROJ_DIR$' not in path:
            return path
        
        # Разбиваем путь на части
        parts = path.split('\\')
        
        # Находим индекс PROJ_DIR
        proj_dir_index = -1
        for i, part in enumerate(parts):
            if part == '$PROJ_DIR$':
                proj_dir_index = i
                break
        
        if proj_dir_index == -1:
            return path
        
        # Считаем количество выходов (..) после PROJ_DIR
        up_count = 0
        start_index = proj_dir_index + 1
        for i in range(start_index, len(parts)):
            if parts[i] == '..':
                up_count += 1
            else:
                break
        
        # Если больше одного выхода, заменяем на один
        if up_count > 1:
            # Оставляем только один выход
            new_parts = parts[:start_index] + ['..'] + parts[start_index + up_count:]
            return '\\'.join(new_parts)
        
        return path
    
    @staticmethod
    def normalize_all_paths_in_xml(xml_root):
        """
        Нормализация всех путей в XML
        
        :param xml_root: Корневой элемент XML
        :return: Обновленный XML корень
        """
        # Нормализуем пути в элементах name
        for name_elem in xml_root.findall('.//name'):
            if name_elem.text and '$PROJ_DIR$' in name_elem.text:
                name_elem.text = PathNormalizer.normalize_path(name_elem.text)
        
        # Нормализуем пути в элементах state
        for state_elem in xml_root.findall('.//state'):
            if state_elem.text and '$PROJ_DIR$' in state_elem.text:
                state_elem.text = PathNormalizer.normalize_path(state_elem.text)
        
        return xml_root
    
    @staticmethod
    def normalize_eww_content(content):
        """
        Нормализация путей в .eww файле
        
        :param content: Содержимое .eww файла
        :return: Нормализованное содержимое
        """
        # Заменяем множественные выходы
        content = re.sub(r'\$WS_DIR\$\\\.\.(\\\.\.)+', '$WS_DIR$', content)
        return content
    
    @staticmethod
    def make_path_relative_to_project(path, project_path, use_proj_dir=True):
        """
        Преобразование абсолютного пути в относительный с $PROJ_DIR$
        
        :param path: Абсолютный путь
        :param project_path: Путь к проекту
        :param use_proj_dir: Использовать $PROJ_DIR$ или просто относительный путь
        :return: Относительный путь
        """
        try:
            path_obj = Path(path)
            project_obj = Path(project_path)
            
            if path_obj.is_absolute() and project_obj.is_absolute():
                rel_path = path_obj.relative_to(project_obj)
                if use_proj_dir:
                    return f"$PROJ_DIR$\\{rel_path}"
                else:
                    return str(rel_path)
        except (ValueError, TypeError):
            pass
        
        return path
    
    @staticmethod
    def normalize_for_windows(path):
        """
        Приведение пути к Windows формату (обратные слеши)
        
        :param path: Исходный путь
        :return: Путь в Windows формате
        """
        if path:
            return str(path).replace('/', '\\')
        return path