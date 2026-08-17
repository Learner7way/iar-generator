#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

"""
Конфигурация и константы для генератора IAR файлов
"""

import os
from pathlib import Path

# Стандартные расширения исходных файлов
SOURCE_EXTENSIONS = {'.c', '.cpp', '.s', '.asm', '.icf', '.mac'}
HEADER_EXTENSIONS = {'.h', '.hpp'}

# Директории для исключения при поиске исходных файлов
EXCLUDE_DIRS = {'bin', 'iar', 'Debug', 'Release',
                '.git', '__pycache__', 'settings', 'docs', 'resources', 'utils',
                'build', 'obj', 'list', 'out'}

# Конфигурации по умолчанию
DEFAULT_CONFIGURATIONS = ['STM32L412RB_NUCLEO']

# Имена файлов по умолчанию
TEMPLATE_NAMES = {
    'ewp': 'project.ewp',
    'ewd': 'project.ewd',
    'eww': 'project.eww',
    'ewt': 'project.ewt'
}

# Пути для поиска FreeRTOSConfig.h
FREERTOS_CONFIG_PATHS = [
    'project/mcu_platforms/STM32L4/inc',
    'project/mcu_platforms/inc',
    'project/config',
    'project/inc',
    'config',
    'inc'
]


class IARConfig:
    """Класс конфигурации для IAR генератора"""
    
    def __init__(self):
        self.source_extensions = SOURCE_EXTENSIONS
        self.header_extensions = HEADER_EXTENSIONS
        self.exclude_dirs = EXCLUDE_DIRS
        self.default_configs = DEFAULT_CONFIGURATIONS
        self.template_names = TEMPLATE_NAMES
        self.freertos_config_paths = FREERTOS_CONFIG_PATHS
        self.chip_info = {
            'default': 'STM32L412RB',
            'family': 'STM32L4',
            'fpu': 'FPU_SP_DP'
        }