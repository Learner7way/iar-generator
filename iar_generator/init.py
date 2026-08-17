#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Пакет для генерации IAR файлов проектов
"""

from .iar_generator import IARProjectGenerator
from .file_finder import FileFinder
from .config import IARConfig
from .path_normalizer import PathNormalizer
from .xml_formatter import XMLFormatter
from .template_loader import TemplateLoader

__version__ = '1.0.0'
__author__ = 'IAR Generator Team'