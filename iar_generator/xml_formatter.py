#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Модуль для форматирования XML файлов IAR
"""

import xml.etree.ElementTree as ET


class XMLFormatter:
    """Класс для форматирования XML в стиле IAR"""
    
    @staticmethod
    def format_compact(elem, level=0, indent="    "):
        """
        Компактное форматирование XML без лишних пробелов и переносов
        
        :param elem: XML элемент
        :param level: Уровень отступа
        :param indent: Строка отступа
        :return: Отформатированная XML строка
        """
        # Для текстовых узлов возвращаем просто текст
        if elem is None:
            return ""
        
        # Специальная обработка для элементов с текстом
        if elem.text and elem.text.strip():
            # Если есть текст, форматируем компактно
            line = f"{indent * level}<{elem.tag}"
            # Добавляем атрибуты если есть
            for key, value in elem.attrib.items():
                line += f' {key}="{value}"'
            line += f">{elem.text.strip()}</{elem.tag}>"
            return line
        
        # Если есть дети, форматируем с отступами
        children = list(elem)
        if children:
            result = [f"{indent * level}<{elem.tag}"]
            # Добавляем атрибуты
            for key, value in elem.attrib.items():
                result[-1] += f' {key}="{value}"'
            result[-1] += ">"
            
            # Рекурсивно форматируем детей
            for child in children:
                child_str = XMLFormatter.format_compact(child, level + 1, indent)
                if child_str:
                    result.append(child_str)
            
            result.append(f"{indent * level}</{elem.tag}>")
            return "\n".join(result)
        else:
            # Пустой элемент - самозакрывающийся
            line = f"{indent * level}<{elem.tag}"
            for key, value in elem.attrib.items():
                line += f' {key}="{value}"'
            line += "/>"
            return line
    
    @staticmethod
    def create_element(tag, text=None, attrib=None):
        """
        Создание XML элемента
        
        :param tag: Имя тега
        :param text: Текст элемента
        :param attrib: Атрибуты
        :return: Созданный элемент
        """
        elem = ET.Element(tag)
        if attrib:
            for key, value in attrib.items():
                elem.set(key, value)
        if text:
            elem.text = text
        return elem
    
    @staticmethod
    def create_file_element(file_path):
        """
        Создание элемента для файла в IAR проекте
        
        :param file_path: Путь к файлу
        :return: XML элемент
        """
        file_elem = ET.Element("file")
        name_elem = ET.SubElement(file_elem, "name")
        name_elem.text = file_path
        return file_elem
    
    @staticmethod
    def create_group_element(group_name):
        """
        Создание элемента для группы файлов
        
        :param group_name: Имя группы
        :return: XML элемент
        """
        group_elem = ET.Element("group")
        name_elem = ET.SubElement(group_elem, "name")
        name_elem.text = group_name
        return group_elem