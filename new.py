#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

import os
import sys
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
import shutil
from datetime import datetime
import argparse
import re

class IARProjectFilesGenerator:
    """
    Генератор файлов IAR проекта (ewp, ewd, eww, ewt) с учётом строгой структуры проекта
    """
    
    # Стандартные расширения исходных файлов
    SOURCE_EXTENSIONS = {'.c', '.cpp', '.s', '.asm', '.icf', '.mac'}
    HEADER_EXTENSIONS = {'.h', '.hpp'}
    
    # Директории для исключения при поиске исходных файлов
    EXCLUDE_DIRS = {'bin', 'iar', 'Debug', 'Release', 'Flash_ST-Link', 
                    '.git', '__pycache__', 'settings', 'docs', 'resources', 'utils'}
    
    def __init__(self, project_path, project_name, output_dir=None):
        """
        Инициализация генератора
        
        :param project_path: Путь к корневой директории проекта
        :param project_name: Имя проекта (Gyro, MyProject, и т.д.)
        :param output_dir: Директория для выходных файлов (по умолчанию: {project_path}/iar)
        """
        self.project_path = Path(project_path)
        if not self.project_path.exists():
            raise FileNotFoundError(f"Проект не найден: {project_path}")
        
        self.project_name = project_name
        self.project_name_lower = project_name.lower()
        
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
        
        # Конфигурации проекта
        self.configurations = ['Debug', 'Release', 'Flash_ST-Link']
        
        # Информация о проекте
        self.project_info = {
            'name': project_name,
            'path': self.project_path,
            'chip': 'STM32L412RB',
            'chip_family': 'STM32L4',
            'fpu': 'FPU_SP_DP'  # Single precision and double precision
        }
        
        print(f"\n🔧 Генератор IAR файлов для проекта: {self.project_name}")
        print(f"📁 Корень проекта: {self.project_path}")
        print(f"📁 Выходная директория: {self.output_dir}")
    
    def find_source_files(self):
        """
        Поиск всех исходных файлов в проекте с сохранением структуры
        """
        source_files = []
        header_files = []
        
        print("\n🔍 Поиск исходных файлов...")
        
        for root, dirs, files in os.walk(self.project_path):
            # Исключаем временные и бинарные директории
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            
            for file in files:
                file_ext = Path(file).suffix.lower()
                full_path = Path(root) / file
                rel_path = full_path.relative_to(self.project_path)
                
                if file_ext in self.SOURCE_EXTENSIONS:
                    source_files.append(str(rel_path))
                    print(f"  📄 Исходный: {rel_path}")
                elif file_ext in self.HEADER_EXTENSIONS:
                    header_files.append(str(rel_path))
                    print(f"  📑 Заголовочный: {rel_path}")
        
        print(f"\n✅ Найдено файлов: {len(source_files)} исходных, {len(header_files)} заголовочных")
        return sorted(source_files), sorted(header_files)
    
    def find_linker_scripts(self):
        """
        Поиск linker script файлов (.icf) в проекте
        """
        icf_files = []
        
        # Ищем в mcu_platforms
        mcu_platforms_dir = self.project_path / 'project' / 'mcu_platforms'
        if mcu_platforms_dir.exists():
            icf_files.extend(list(mcu_platforms_dir.glob('**/*.icf')))
        
        # Ищем в корне проекта
        icf_files.extend(list(self.project_path.glob('*.icf')))
        
        # Ищем в папке iar
        icf_files.extend(list(self.output_dir.glob('*.icf')))
        
        result = []
        for icf in icf_files:
            rel_path = icf.relative_to(self.project_path)
            result.append(str(rel_path))
            print(f"  📄 Linker script: {rel_path}")
        
        return result
    
    def get_include_paths(self):
        """
        Формирование списка путей для поиска заголовочных файлов
        """
        include_paths = [
            "$PROJ_DIR$\\..\\",  # Корень проекта
            "$PROJ_DIR$\\..\\project",
            "$PROJ_DIR$\\..\\project\\app",
            "$PROJ_DIR$\\..\\project\\build_variant",
            "$PROJ_DIR$\\..\\project\\firmware",
            "$PROJ_DIR$\\..\\project\\mcu_platforms",
            "$PROJ_DIR$\\..\\project\\mcu_platforms\\stm32l412",
            "$PROJ_DIR$\\..\\project\\middleware",
            "$PROJ_DIR$\\..\\project\\modules",
            "$PROJ_DIR$\\..\\project\\modules_configs",
            "$PROJ_DIR$\\..\\project\\libs",
        ]
        
        # Добавляем все подпапки modules
        modules_dir = self.project_path / 'project' / 'modules'
        if modules_dir.exists():
            for module in modules_dir.iterdir():
                if module.is_dir():
                    include_paths.append(f"$PROJ_DIR$\\..\\project\\modules\\{module.name}")
                    # Добавляем подпапки модулей
                    for subdir in module.iterdir():
                        if subdir.is_dir():
                            include_paths.append(f"$PROJ_DIR$\\..\\project\\modules\\{module.name}\\{subdir.name}")
        
        # Добавляем все подпапки mcu_platforms/stm32l412
        mcu_dir = self.project_path / 'project' / 'mcu_platforms' / 'stm32l412'
        if mcu_dir.exists():
            for subdir in mcu_dir.iterdir():
                if subdir.is_dir() and subdir.name not in self.EXCLUDE_DIRS:
                    include_paths.append(f"$PROJ_DIR$\\..\\project\\mcu_platforms\\stm32l412\\{subdir.name}")
        
        # Удаляем дубликаты и сортируем
        include_paths = sorted(list(set(include_paths)))
        
        print("\n📁 Пути для поиска заголовочных файлов:")
        for path in include_paths:
            print(f"   {path}")
        
        return include_paths
    
    def generate_ewp_file(self, source_files, header_files, linker_scripts):
        """
        Генерация .ewp файла проекта с правильными include paths
        """
        print(f"\n📝 Генерация {self.ewp_file.name}...")
        
        # Создаём корневой элемент
        root = ET.Element("project")
        ET.SubElement(root, "fileVersion").text = "4"
        
        # Генерируем конфигурации
        for config_name in self.configurations:
            config_elem = ET.SubElement(root, "configuration")
            ET.SubElement(config_elem, "name").text = config_name
            
            toolchain = ET.SubElement(config_elem, "toolchain")
            ET.SubElement(toolchain, "name").text = "ARM"
            
            debug = "1" if config_name != "Release" else "0"
            ET.SubElement(config_elem, "debug").text = debug
            
            # Настройки General
            self._add_general_settings(config_elem, config_name)
            
            # Настройки компилятора ICCARM с include paths
            self._add_iccarm_settings(config_elem, config_name)
            
            # Настройки ассемблера AARM
            self._add_aarm_settings(config_elem, config_name)
            
            # Настройки OBJCOPY
            self._add_objcopy_settings(config_elem, config_name)
            
            # Настройки CUSTOM
            self._add_custom_settings(config_elem)
            
            # Настройки линкера ILINK
            self._add_ilink_settings(config_elem, config_name, linker_scripts)
            
            # Настройки IARCHIVE
            self._add_iarchive_settings(config_elem, config_name)
            
            # Настройки BUILDACTION
            self._add_buildaction_settings(config_elem)
        
        # Добавляем все исходные файлы (включая заголовочные)
        all_files = source_files + header_files
        for file_path in all_files:
            file_elem = ET.SubElement(root, "file")
            # Используем $PROJ_DIR$ для относительных путей
            file_path_win = file_path.replace('/', '\\')
            ET.SubElement(file_elem, "name").text = f"$PROJ_DIR$\\..\\{file_path_win}"
        
        # Форматируем XML
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ", encoding='UTF-8')
        
        with open(self.ewp_file, 'wb') as f:
            f.write(xml_str)
        
        print(f"✅ Сгенерирован {self.ewp_file.name}")
        print(f"   Добавлено файлов: {len(all_files)}")

    # ИСПРАВЛЕНО: Настройки General приведены в точное соответствие с эталоном
    def _add_general_settings(self, config_elem, config_name):
        """Добавление общих настроек"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "General"
        ET.SubElement(settings, "archiveVersion").text = "3"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "37"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1"
        
        # Опции без version (значения строго по эталону)
        regular_options = [
            ("GEndianMode", "0"),
            ("Input description", "Full formatting, without multibyte support."),
            ("Output description", "Full formatting, without multibyte support."),
            ("GOutputBinary", "0"),
            ("OGCoreOrChip", "1"),
            ("RTDescription", "A complete configuration of the C/C++14 runtime library. Full locale interface, C locale, file descriptor support, multibytes in printf and scanf, and hex floats in strtod."),
            ("OGProductVersion", "9.60.3.7274"),
            ("OGLastSavedByProductVersion", "9.60.3.7274"),
            ("GenLowLevelInterface", "1"),
            ("GEndianModeBE", "1"),
            ("OGBufferedTerminalOutput", "0"),
            ("GenStdoutInterface", "0"),
            ("RTConfigPath2", "$TOOLKIT_DIR$\\inc\\c\\DLib_Config_Full.h"),
            ("OGUseCmsis", "0"),
            ("OGUseCmsisDspLib", "0"),
            ("GRuntimeLibThreads", "0"),
            ("GFPUDeviceSlave", f"{self.project_info['chip']}\tST {self.project_info['chip']}"),
            ("NEON", "0"),
            ("OGCMSISPackSelectDevice", ""),
            ("OgLibHeap", "0"),
            ("OGLibAdditionalLocale", "0"),
            ("OGPrintfMultibyteSupport", "0"),
            ("OGScanfMultibyteSupport", "0"),
            ("GenLocaleTags", ""),
            ("GenLocaleDisplayOnly", ""),
            ("TrustZone", "0"),
            ("OGAarch64Abi", "0"),
            ("OG_32_64Device", "0"),
            ("BuildFilesPath", f"{config_name}\\"),
            ("PointerAuthentication", "0"),
            ("FPU64", "1"),
            ("GOutputSo", "0"),
            ("ExePath", f"{config_name}\\Exe"),
            ("ObjPath", f"{config_name}\\Obj"),
            ("ListPath", f"{config_name}\\List"),
            ("BrowseInfoPath", f"{config_name}\\BrowseInfo"),
            ("OGChipSelectEditMenu", f"{self.project_info['chip']}\tST {self.project_info['chip']}"),
            ("DSPExtension", "1"),
        ]
        
        # Опции с version (значения строго по эталону)
        versioned_options = [
            ("GRuntimeLibSelectSlave", "2", "0"),
            ("GBECoreSlave", "39", "34"),
            ("NrRegs", "1", "0"),
            ("GFPUCoreSlave2", "39", "34"),
            ("OGPrintfVariant", "1", "0"),
            ("OGScanfVariant", "1", "0"),
            ("TrustZoneModes", "0", "0"),
            ("OG_32_64DeviceCoreSlave", "39", "34"),
            ("CoreVariant", "39", "34"),
            ("FPU2", "4", "0"),
            ("GRuntimeLibSelect", "2", "0"),
        ]
        
        # Добавляем обычные опции
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        # Добавляем опции с version
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    # ИСПРАВЛЕНО: Пути включения приведены в соответствие с эталоном
    def _add_iccarm_settings(self, config_elem, config_name):
        """
        Добавление настроек компилятора ICCARM с правильными include paths
        """
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "ICCARM"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "39"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Обычные опции
        regular_options = [
            ("CCPreprocFile", "0"),
            ("CCPreprocComments", "0"),
            ("CCPreprocLine", "1"),
            ("CCListCFile", "0"),
            ("CCListCMnemonics", "0"),
            ("CCListCMessages", "0"),
            ("CCListAssFile", "0"),
            ("CCListAssSource", "0"),
            ("CCEnableRemarks", "0"),
            ("CCDiagSuppress", ""),
            ("CCDiagRemark", ""),
            ("CCDiagWarning", ""),
            ("CCDiagError", ""),
            ("CCObjPrefix", "1"),
            ("IEndianMode", "1"),
            ("IExtraOptionsCheck", "0"),
            ("IExtraOptions", ""),
            ("CCRequirePrototypes", "0"),
            ("CCDiagWarnAreErr", "0"),
            ("CCCompilerRuntimeInfo", "0"),
            ("CCLibConfigHeader", "1"),
            ("CCStdIncCheck", "0"),
            ("CCCodeSection", ".text"),
            ("IProcessorMode2", "1"),
            ("CCOptLevelSlave", "3" if config_name == "Debug" else "1"),
            ("CCPosIndRopi", "0"),
            ("CCPosIndRwpi", "0"),
            ("CCPosIndNoDynInit", "0"),
            ("IccLang", "0"),
            ("IccCDialect", "1"),
            ("IccAllowVLA", "0"),
            ("IccStaticDestr", "1"),
            ("IccCppInlineSemantics", "0"),
            ("IccCmsis", "1"),
            ("IccFloatSemantics", "0"),
            ("CCOptimizationNoSizeConstraints", "0"),
            ("CCNoLiteralPool", "0"),
            ("CCGuardCalls", "1"),
            ("CCEncSource", "2"),
            ("CCEncOutput", "2"),
            ("CCEncOutputBom", "1"),
            ("CCEncInput", "1"),
            ("IccExceptions2", "0"),
            ("IccRTTI2", "0"),
            ("OICompilerExtraOption", "1"),
            ("CCStackProtection", "0"),
            ("CCPointerAutentiction", "0"),
            ("CCBranchTargetIdentification", "0"),
            ("CCPosRadRwpi", "0"),
            ("CCPosSharedSlave", "0"),
            ("CCDebugInfo", "1" if config_name != "Release" else "0"),
            ("IProcessor", "1"),
            ("IFpuProcessor", "1"),
            ("CCLangConformance", "0"),
            ("CCSignedPlainChar", "1"),
            ("OutputFile", "$FILE_BNAME$.o"),
            ("CCOptLevel", "3" if config_name == "Debug" else "1"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CCAllowList", "11111110", "1"),
            ("CCOptStrategy", "1", "0"),
            ("CCOptStrategySlave", "1", "0"),
        ]
        
        # Добавляем обычные опции
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        # Добавляем опции с version
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        # Include paths - используем множественные state элементы (исправлено по эталону)
        include_paths = self.get_detailed_include_paths()
        
        include_option = ET.SubElement(data, "option")
        ET.SubElement(include_option, "name").text = "CCIncludePath2"
        
        # Добавляем каждый путь как отдельный state элемент
        for path in include_paths:
            state_elem = ET.SubElement(include_option, "state")
            state_elem.text = path
        
        # Defines
        defines_option = ET.SubElement(data, "option")
        ET.SubElement(defines_option, "name").text = "CCDefines"
        
        # Добавляем defines в точности как в эталоне
        defines = ["USE_FULL_LL_DRIVER", "STM32L412xx"]
        for define in defines:
            state_elem = ET.SubElement(defines_option, "state")
            state_elem.text = define
        
        # PreInclude
        preinclude_option = ET.SubElement(data, "option")
        ET.SubElement(preinclude_option, "name").text = "PreInclude"
        ET.SubElement(preinclude_option, "state")

    # ИСПРАВЛЕНО: Детальные пути включения приведены в соответствие с эталоном
    def get_detailed_include_paths(self):
        """
        Формирование детального списка путей для поиска заголовочных файлов
        """
        include_paths = [
            "$PROJ_DIR$\\..\\",  # Корень проекта
            "$PROJ_DIR$\\..\\project",
            "$PROJ_DIR$\\..\\project\\app",
            "$PROJ_DIR$\\..\\project\\build_variant",
            "$PROJ_DIR$\\..\\project\\firmware",
            "$PROJ_DIR$\\..\\project\\firmware\\stm32\\CMSIS\\inc",
            "$PROJ_DIR$\\..\\project\\firmware\\stm32\\STM32L4xx_LL_drivers\\inc",
            "$PROJ_DIR$\\..\\project\\libs",
            "$PROJ_DIR$\\..\\project\\mcu_platforms",
            "$PROJ_DIR$\\..\\project\\mcu_platforms\\stm32l412",
            "$PROJ_DIR$\\..\\project\\mcu_platforms\\stm32l412\\button",
            "$PROJ_DIR$\\..\\project\\mcu_platforms\\stm32l412\\led",
            "$PROJ_DIR$\\..\\project\\mcu_platforms\\stm32l412\\uart",
            "$PROJ_DIR$\\..\\project\\middleware",
            "$PROJ_DIR$\\..\\project\\middleware\\FreeRTOS\\",
            "$PROJ_DIR$\\..\\project\\middleware\\FreeRTOS\\include",
            "$PROJ_DIR$\\..\\project\\middleware\\FreeRTOS\\portable\\IAR\\ARM_CM4F",
            "$PROJ_DIR$\\..\\project\\modules",
            "$PROJ_DIR$\\..\\project\\modules\\button",
            "$PROJ_DIR$\\..\\project\\modules\\led",
            "$PROJ_DIR$\\..\\project\\modules\\uart",
            "$PROJ_DIR$\\..\\project\\modules_configs",
        ]
        
        # Удаляем дубликаты и сортируем
        include_paths = sorted(list(set(include_paths)))
        
        print("\n📁 Пути для поиска заголовочных файлов:")
        for path in include_paths:
            print(f"   {path}")
        
        return include_paths

    def _add_aarm_settings(self, config_elem, config_name):
        """Добавление настроек ассемблера AARM"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "AARM"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "12"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Обычные опции
        regular_options = [
            ("AWarnEnable", "0"),
            ("AWarnWhat", "0"),
            ("AWarnOne", ""),
            ("AWarnRange1", ""),
            ("AWarnRange2", ""),
            ("AltRegisterNames", "0"),
            ("ADefines", ""),
            ("AList", "0"),
            ("AListHeader", "1"),
            ("AListing", "1"),
            ("Includes", "0"),
            ("MacDefs", "0"),
            ("MacExps", "1"),
            ("MacExec", "0"),
            ("OnlyAssed", "0"),
            ("MultiLine", "0"),
            ("PageLengthCheck", "0"),
            ("PageLength", "80"),
            ("TabSpacing", "8"),
            ("AXRef", "0"),
            ("AXRefDefines", "0"),
            ("AXRefInternal", "0"),
            ("AXRefDual", "0"),
            ("ALimitErrorsCheck", "0"),
            ("ALimitErrorsEdit", "100"),
            ("AIgnoreStdInclude", "1" if config_name == "Debug" else "0"),
            ("AExtraOptionsCheckV2", "0"),
            ("AExtraOptionsV2", ""),
            ("AsmNoLiteralPool", "0"),
            ("PreInclude", ""),
            ("A_32_64Device", "1"),
            ("AObjPrefix", "1"),
            ("AEndian", "1"),
            ("ACaseSensitivity", "1"),
            ("ADebug", "1" if config_name != "Release" else "0"),
            ("AProcessor", "1"),
            ("AFpuProcessor", "1"),
            ("AOutputFile", "$FILE_BNAME$.o"),
        ]
        
        # Опции с version
        versioned_options = [
            ("MacroChars", "0", "0"),
        ]
        
        # Добавляем обычные опции
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        # Добавляем опции с version
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        # User Includes для ассемблера
        user_includes_option = ET.SubElement(data, "option")
        ET.SubElement(user_includes_option, "name").text = "AUserIncludes"
        
        asm_includes = [
            "$PROJ_DIR$",
            "$PROJ_DIR$\\..\\project\\middleware\\FreeRTOS\\portable\\IAR\\ARM_CM4F",
            "$PROJ_DIR$\\..\\project\\modules_configs\\",
        ]
        
        for inc_path in asm_includes:
            state_elem = ET.SubElement(user_includes_option, "state")
            state_elem.text = inc_path

    # ИСПРАВЛЕНО: Добавлен параметр config_name для методов, где он используется
    def _add_objcopy_settings(self, config_elem, config_name):
        """Добавление настроек OBJCOPY"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "OBJCOPY"
        ET.SubElement(settings, "archiveVersion").text = "0"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "1"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1"
        
        # Опции OBJCOPY
        options = [
            ("OCOutputOverride", "1" if config_name == "Debug" else "0"),
            ("OOCOutputFile", f"{self.project_name}.hex" if config_name == "Debug" else ""),
            ("OOCCommandLineProducer", "1"),
            ("OOCObjCopyEnable", "1" if config_name == "Debug" else "0"),
        ]
        
        for name, value in options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            if value:
                ET.SubElement(option, "state").text = str(value)
            else:
                ET.SubElement(option, "state")
        
        # Опция с version
        output_format_option = ET.SubElement(data, "option")
        ET.SubElement(output_format_option, "name").text = "OOCOutputFormat"
        ET.SubElement(output_format_option, "version").text = "3"
        state_elem = ET.SubElement(output_format_option, "state")
        state_elem.text = "1" if config_name == "Debug" else "0"

    def _add_custom_settings(self, config_elem):
        """Добавление настроек CUSTOM"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "CUSTOM"
        ET.SubElement(settings, "archiveVersion").text = "4"
        
        data = ET.SubElement(settings, "data")
        
        extensions = ET.SubElement(data, "extensions")
        extensions.text = ""
        
        cmdline = ET.SubElement(data, "cmdline")
        cmdline.text = ""
        
        build_sequence = ET.SubElement(data, "buildSequence")
        build_sequence.text = "inputOutputBased"

    # ИСПРАВЛЕНО: Добавлен параметр config_name и исправлены пути к .icf
    def _add_ilink_settings(self, config_elem, config_name, linker_scripts):
        """Добавление настроек линкера ILINK"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "ILINK"
        ET.SubElement(settings, "archiveVersion").text = "0"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "28"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Базовые опции (все возможные опции из примера)
        regular_options = [
            ("IlinkLibIOConfig", "1"),
            ("IlinkInputFileSlave", "0"),
            ("IlinkKeepSymbols", ""),
            ("IlinkRawBinaryFile", ""),
            ("IlinkRawBinarySymbol", ""),
            ("IlinkRawBinarySegment", ""),
            ("IlinkRawBinaryAlign", ""),
            ("IlinkDefines", ""),
            ("IlinkConfigDefines", ""),
            ("IlinkLogFile", "0"),
            ("IlinkLogInitialization", "0"),
            ("IlinkLogModule", "0"),
            ("IlinkLogSection", "0"),
            ("IlinkLogVeneer", "0"),
            ("IlinkIcfFileSlave", ""),
            ("IlinkEnableRemarks", "0"),
            ("IlinkSuppressDiags", ""),
            ("IlinkTreatAsRem", ""),
            ("IlinkTreatAsWarn", ""),
            ("IlinkTreatAsErr", ""),
            ("IlinkWarningsAreErrors", "0"),
            ("IlinkUseExtraOptions", "0"),
            ("IlinkExtraOptions", ""),
            ("IlinkLowLevelInterfaceSlave", "1"),
            ("IlinkAdditionalLibs", ""),
            ("IlinkProgramEntryLabelSelect", "0"),
            ("DoFill", "0"),
            ("FillerByte", "0xFF"),
            ("FillerStart", "0x0"),
            ("FillerEnd", "0x0"),
            ("CrcAlign", "1"),
            ("CrcPoly", "0x11021"),
            ("CrcInitialValue", "0x0"),
            ("DoCrc", "0"),
            ("IlinkBE8Slave", "1"),
            ("IlinkBufferedTerminalOutput", "1"),
            ("IlinkStdoutInterfaceSlave", "1"),
            ("CrcFullSize", "0"),
            ("IlinkIElfToolPostProcess", "0"),
            ("IlinkLogAutoLibSelect", "0"),
            ("IlinkLogRedirSymbols", "0"),
            ("IlinkLogUnusedFragments", "0"),
            ("IlinkCrcReverseByteOrder", "0"),
            ("IlinkCrcUseAsInput", "1"),
            ("IlinkOptInline", "0" if config_name != "Release" else "1"),
            ("IlinkOptExceptionsAllow", "1"),
            ("IlinkOptExceptionsForce", "0"),
            ("IlinkCmsis", "1"),
            ("IlinkOptMergeDuplSections", "0"),
            ("IlinkOptUseVfe", "1"),
            ("IlinkOptForceVfe", "0"),
            ("IlinkStackAnalysisEnable", "0"),
            ("IlinkStackControlFile", ""),
            ("IlinkStackCallGraphFile", ""),
            ("IlinkThreadsSlave", "1"),
            ("IlinkLogCallGraph", "0"),
            ("IlinkIcfFile_AltDefault", ""),
            ("IlinkEncInput", "1"),
            ("IlinkEncOutput", "1"),
            ("IlinkEncOutputBom", "1"),
            ("IlinkHeapSelect", "1"),
            ("IlinkLocaleSelect", "1"),
            ("IlinkTrustzoneImportLibraryOut", f"{self.project_name}_import_lib.o"),
            ("OILinkExtraOption", "1"),
            ("IlinkRawBinaryFile2", ""),
            ("IlinkRawBinarySymbol2", ""),
            ("IlinkRawBinarySegment2", ""),
            ("IlinkRawBinaryAlign2", ""),
            ("IlinkLogCrtRoutineSelection", "0"),
            ("IlinkLogFragmentInfo", "0"),
            ("IlinkLogInlining", "0"),
            ("IlinkLogMerging", "0"),
            ("IlinkDemangle", "0"),
            ("IlinkWrapperFileEnable", "0"),
            ("IlinkWrapperFile", ""),
            ("IlinkProcessor", "1"),
            ("IlinkFpuProcessor", "1"),
            ("IlinkSharedSlave", "0"),
            ("IlinkOutputFile", "$PROJ_FNAME$.out"),
            ("IlinkMapFile", "1"),
            ("IlinkDebugInfoEnable", "1" if config_name != "Release" else "0"),
            ("IlinkAutoLibEnable", "1"),
            ("IlinkOverrideProgramEntryLabel", "0"),
            ("IlinkProgramEntryLabel", "__iar_program_start"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CrcSize", "1", "0"),
            ("CrcCompl", "0", "0"),
            ("CrcBitOrder", "0", "0"),
            ("CrcAlgorithm", "1", "1"),
            ("CrcUnitSize", "0", "0"),
        ]
        
        # Добавляем обычные опции
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        # Добавляем опции с version
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        # Выбор linker script
        if config_name == "Debug":
            # Для Debug используем конкретный .icf файл из примера
            icf_file = "$PROJ_DIR$\\stm32l412xx_flash.icf"
            
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = "IlinkIcfFile"
            ET.SubElement(option, "state").text = icf_file
            
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = "IlinkIcfOverride"
            ET.SubElement(option, "state").text = "1"
        elif config_name == "Release":
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = "IlinkIcfFile"
            ET.SubElement(option, "state").text = "$TOOLKIT_DIR$\\config\\linker\\ST\\stm32l412xB.icf"
            
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = "IlinkIcfOverride"
            ET.SubElement(option, "state").text = "0"
        else:  # Flash_ST-Link
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = "IlinkIcfOverride"
            ET.SubElement(option, "state").text = "0"
            
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = "IlinkIcfFile"
            ET.SubElement(option, "state").text = "lnk0t.icf"

    def _add_iarchive_settings(self, config_elem, config_name):
        """Добавление настроек IARCHIVE"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "IARCHIVE"
        ET.SubElement(settings, "archiveVersion").text = "0"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "0"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        options = [
            ("IarchiveInputs", ""),
            ("IarchiveOverride", "0"),
            ("IarchiveOutput", "###Unitialized###"),
        ]
        
        for name, value in options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_buildaction_settings(self, config_elem):
        """Добавление настроек BUILDACTION"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "BUILDACTION"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        # Пустые данные, как в примере
    
    # Остальные методы (generate_ewd_file, generate_eww_file, generate_ewt_file, generate_readme) остаются без изменений,
    # так как они уже были хорошо написаны и соответствуют эталону. Для краткости они здесь не перепечатываются,
    # но должны быть включены в итоговый скрипт.

    def generate_ewd_file(self):
        """
        Генерация .ewd файла (настройки отладчика) с полным набором драйверов
        """
        print(f"\n📝 Генерация {self.ewd_file.name}...")
        
        root = ET.Element("project")
        ET.SubElement(root, "fileVersion").text = "4"
        
        # Генерируем конфигурации для каждого типа (Debug, Release, Flash_ST-Link)
        for config_name in self.configurations:
            config_elem = ET.SubElement(root, "configuration")
            ET.SubElement(config_elem, "name").text = config_name
            
            toolchain = ET.SubElement(config_elem, "toolchain")
            ET.SubElement(toolchain, "name").text = "ARM"
            
            debug = "1" if config_name != "Release" else "0"
            ET.SubElement(config_elem, "debug").text = debug
            
            # Добавляем настройки для всех драйверов отладки
            self._add_cspy_settings_ewd(config_elem, config_name)
            self._add_armsim_settings(config_elem, config_name)
            self._add_cadi_settings(config_elem, config_name)
            self._add_cmsisdap_settings(config_elem, config_name)
            self._add_e2_settings(config_elem, config_name)
            self._add_gdbserver_settings(config_elem, config_name)
            self._add_gplink_settings(config_elem, config_name)
            self._add_ijet_settings(config_elem, config_name)
            self._add_jlink_settings(config_elem, config_name)
            self._add_lmiftdi_settings(config_elem, config_name)
            self._add_nulink_settings(config_elem, config_name)
            self._add_pemicro_settings(config_elem, config_name)
            self._add_stlink_settings(config_elem, config_name)
            self._add_thirdparty_settings(config_elem, config_name)
            self._add_tifet_settings(config_elem, config_name)
            self._add_xds100_settings(config_elem, config_name)
            
            # Добавляем плагины отладчика
            self._add_debugger_plugins(config_elem)
        
        # Форматируем XML
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ", encoding='UTF-8')
        
        with open(self.ewd_file, 'wb') as f:
            f.write(xml_str)
        
        print(f"✅ Сгенерирован {self.ewd_file.name}")

    def _add_cspy_settings_ewd(self, config_elem, config_name):
        """Добавление настроек C-SPY для EWD файла"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "C-SPY"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "33"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Базовые опции C-SPY
        cspy_options = [
            ("OCVariant", "0"),
            ("MacOverride", "0"),
            ("MacFile", ""),
            ("MemOverride", "0"),
            ("CExtraOptionsCheck", "0"),
            ("CExtraOptions", ""),
            ("OCDDFArgumentProducer", ""),
            ("OCDownloadSuppressDownload", "0"),
            ("OCDownloadVerifyAll", "1"),
            ("OCProductVersion", "9.60.3.7274"),
            ("OCLastSavedByProductVersion", "9.60.3.7274"),
            ("UseFlashLoader", "1"),
            ("CLowLevel", "1"),
            ("OCBE8Slave", "1"),
            ("MacFile2", ""),
            ("CDevice", "1"),
            ("FlashLoadersV3", "$TOOLKIT_DIR$/config/flashloader/ST/FlashSTM32L41xxB.board"),
            ("OCImagesSuppressCheck1", "0"),
            ("OCImagesPath1", ""),
            ("OCImagesSuppressCheck2", "0"),
            ("OCImagesPath2", ""),
            ("OCImagesSuppressCheck3", "0"),
            ("OCImagesPath3", ""),
            ("OverrideDefFlashBoard", "0"),
            ("OCImagesOffset1", ""),
            ("OCImagesOffset2", ""),
            ("OCImagesOffset3", ""),
            ("OCImagesUse1", "0"),
            ("OCImagesUse2", "0"),
            ("OCImagesUse3", "0"),
            ("OCDeviceConfigMacroFile", "1"),
            ("OCDebuggerExtraOption", "1"),
            ("OCAllMTBOptions", "1"),
            ("OCMulticoreNrOfCores", "1"),
            ("OCMulticoreWorkspace", ""),
            ("OCMulticoreSlaveProject", ""),
            ("OCMulticoreSlaveConfiguration", ""),
            ("OCDownloadExtraImage", "1"),
            ("OCAttachSlave", "0"),
            ("MassEraseBeforeFlashing", "0"),
            ("OCMulticoreNrOfCoresSlave", "1"),
            ("OCMulticoreAMPConfigType", "0"),
            ("OCMulticoreSessionFile", ""),
            ("OCTpiuBaseOption", "1"),
            ("OCOverrideSlave", "0"),
            ("OCOverrideSlavePath", ""),
            ("C_32_64Device", "1"),
            ("AuthEnable", "0"),
            ("AuthSdmSelection", "1"),
            ("AuthSdmManifest", ""),
            ("AuthSdmExplicitLib", ""),
            ("AuthEnforce", "0"),
            ("CInput", "1"),
            ("CEndian", "1"),
            ("CProcessor", "1"),
            ("CFpuProcessor", "1"),
            ("RunToEnable", "1"),
            ("RunToName", "main"),
            ("MemFile", f"$TOOLKIT_DIR$\\config\\debugger\\ST\\{self.project_info['chip']}.ddf"),
            ("OCDynDriverList", "STLINK_ID"),
        ]
        
        for name, value in cspy_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_armsim_settings(self, config_elem, config_name):
        """Добавление настроек ARMSIM"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "ARMSIM_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "1"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        armsim_options = [
            ("OCSimDriverInfo", "1"),
            ("OCSimEnablePSP", "0"),
            ("OCSimPspOverrideConfig", "0"),
            ("OCSimPspConfigFile", ""),
        ]
        
        for name, value in armsim_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_cadi_settings(self, config_elem, config_name):
        """Добавление настроек CADI"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "CADI_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "0"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        cadi_options = [
            ("CCadiMemory", "1"),
            ("Fast Model", ""),
            ("CCADILogFileCheck", "0"),
            ("CCADILogFileEditB", "$PROJ_DIR$\\cspycomm.log"),
            ("OCDriverInfo", "1"),
        ]
        
        for name, value in cadi_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_cmsisdap_settings(self, config_elem, config_name):
        """Добавление настроек CMSIS-DAP"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "CMSISDAP_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "4"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Обычные опции
        regular_options = [
            ("OCDriverInfo", "1"),
            ("OCIarProbeScriptFile", "1"),
            ("CMSISDAPHWResetDuration", "300"),
            ("CMSISDAPHWResetDelay", "200"),
            ("CMSISDAPDoLogfile", "0"),
            ("CMSISDAPLogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("CMSISDAPInterfaceRadio", "1"),
            ("CMSISDAPInterfaceCmdLine", "0"),
            ("CMSISDAPMultiTargetEnable", "0"),
            ("CMSISDAPMultiTarget", "0"),
            ("CMSISDAPBreakpointRadio", "0"),
            ("CMSISDAPRestoreBreakpointsCheck", "0"),
            ("CMSISDAPUpdateBreakpointsEdit", "_call_main"),
            ("RDICatchReset", "0"),
            ("RDICatchUndef", "1"),
            ("RDICatchSWI", "0"),
            ("RDICatchData", "1"),
            ("RDICatchPrefetch", "1"),
            ("RDICatchIRQ", "0"),
            ("RDICatchFIQ", "0"),
            ("CatchCORERESET", "0"),
            ("CatchMMERR", "1"),
            ("CatchNOCPERR", "1"),
            ("CatchCHKERR", "1"),
            ("CatchSTATERR", "1"),
            ("CatchBUSERR", "1"),
            ("CatchINTERR", "1"),
            ("CatchSFERR", "1"),
            ("CatchHARDERR", "1"),
            ("CatchDummy", "0"),
            ("CMSISDAPMultiCPUEnable", "0"),
            ("CMSISDAPMultiCPUNumber", "0"),
            ("OCProbeCfgOverride", "0"),
            ("OCProbeConfig", ""),
            ("CMSISDAPProbeConfigRadio", "0"),
            ("CMSISDAPSelectedCPUBehaviour", "0"),
            ("ICpuName", ""),
            ("OCJetEmuParams", "1"),
            ("CCCMSISDAPUsbSerialNo", ""),
            ("CCCMSISDAPUsbSerialNoSelect", "0"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CMSISDAPResetList", "10", "1"),
            ("CMSISDAPJtagSpeedList", "0", "0"),
        ]
        
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_e2_settings(self, config_elem, config_name):
        """Добавление настроек E2"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "E2_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "0"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        e2_options = [
            ("E2PowerFromProbe", "1"),
            ("CE2UsbSerialNo", ""),
            ("CE2IdCodeEditB", "0xFFFF'FFFF'FFFF'FFFF'FFFF'FFFF'FFFF'FFFF"),
            ("CE2LogFileCheck", "0"),
            ("CE2LogFileEditB", "$PROJ_DIR$\\cspycomm.log"),
            ("OCDriverInfo", "1"),
        ]
        
        for name, value in e2_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_gdbserver_settings(self, config_elem, config_name):
        """Добавление настроек GDB Server"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "GDBSERVER_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "0"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        gdbserver_options = [
            ("OCDriverInfo", "1"),
            ("TCPIP", "aaa.bbb.ccc.ddd"),
            ("DoLogfile", "0"),
            ("LogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("CCJTagBreakpointRadio", "0"),
            ("CCJTagDoUpdateBreakpoints", "0"),
            ("CCJTagUpdateBreakpoints", "_call_main"),
        ]
        
        for name, value in gdbserver_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_gplink_settings(self, config_elem, config_name):
        """Добавление настроек GPLINK"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "GPLINK_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "0"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        gplink_options = [
            ("OCDriverInfo", "1"),
            ("DoLogfile", "0"),
            ("LogFile", "$PROJ_DIR$\\cspycomm.log"),
        ]
        
        for name, value in gplink_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_ijet_settings(self, config_elem, config_name):
        """Добавление настроек I-JET"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "IJET_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "10"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Обычные опции
        regular_options = [
            ("OCDriverInfo", "1"),
            ("OCIarProbeScriptFile", "1"),
            ("IjetHWResetDuration", ""),
            ("IjetHWResetDelay", ""),
            ("IjetPowerFromProbe", "1"),
            ("IjetPowerRadio", "0"),
            ("IjetDoLogfile", "0"),
            ("IjetLogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("IjetInterfaceRadio", "1"),
            ("IjetInterfaceCmdLine", "0"),
            ("IjetMultiTargetEnable", "0"),
            ("IjetMultiTarget", "0"),
            ("IjetScanChainNonARMDevices", "0"),
            ("IjetIRLength", "0"),
            ("IjetProtocolRadio", "0"),
            ("IjetSwoPin", "0"),
            ("IjetCpuClockEdit", ""),
            ("IjetBreakpointRadio", "0"),
            ("IjetRestoreBreakpointsCheck", "0"),
            ("IjetUpdateBreakpointsEdit", "_call_main"),
            ("RDICatchReset", "0"),
            ("RDICatchUndef", "1"),
            ("RDICatchSWI", "0"),
            ("RDICatchData", "1"),
            ("RDICatchPrefetch", "1"),
            ("RDICatchIRQ", "0"),
            ("RDICatchFIQ", "0"),
            ("CatchCORERESET", "0"),
            ("CatchMMERR", "1"),
            ("CatchNOCPERR", "1"),
            ("CatchCHKERR", "1"),
            ("CatchSTATERR", "1"),
            ("CatchBUSERR", "1"),
            ("CatchINTERR", "1"),
            ("CatchSFERR", "1"),
            ("CatchHARDERR", "1"),
            ("CatchDummy", "0"),
            ("OCProbeCfgOverride", "0"),
            ("OCProbeConfig", ""),
            ("IjetProbeConfigRadio", "0"),
            ("IjetMultiCPUEnable", "0"),
            ("IjetMultiCPUNumber", "0"),
            ("IjetSelectedCPUBehaviour", "0"),
            ("ICpuName", ""),
            ("OCJetEmuParams", "1"),
            ("IjetPreferETB", "1"),
            ("FlashBoardPathSlave", "0"),
            ("CCIjetUsbSerialNo", ""),
            ("CCIjetUsbSerialNoSelect", "0"),
            ("CatchV8ARReset", "0"),
            ("CatchV8AREREL1NS", "0"),
            ("CatchV8AREREL1S", "0"),
            ("CatchV8AREREL2NS", "0"),
            ("CatchV8AREREL3S", "0"),
            ("CatchV8AREEL1NS", "0"),
            ("CatchV8ARREL1NS", "0"),
            ("CatchV8AREEL1S", "0"),
            ("CatchV8ARREL1S", "0"),
            ("CatchV8AREEL2NS", "0"),
            ("CatchV8ARREL2NS", "0"),
            ("CatchV8AREEL3S", "0"),
            ("CatchV8ARREL3S", "0"),
            ("IjetHWResetTimingOverride", "0"),
        ]
        
        # Опции с version
        versioned_options = [
            ("IjetResetList", "10", "1"),
            ("IjetJtagSpeedList", "0", "0"),
            ("IjetSwoPrescalerList", "0", "1"),
            ("IjetTraceSettingsList", "0", "0"),
            ("IjetTraceSizeList", "4", "0"),
        ]
        
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_jlink_settings(self, config_elem, config_name):
        """Добавление настроек J-LINK"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "JLINK_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "16"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Обычные опции
        regular_options = [
            ("JLinkSpeed", "1000"),
            ("CCJLinkDoLogfile", "0"),
            ("CCJLinkLogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("CCJLinkHWResetDelay", "0"),
            ("OCDriverInfo", "1"),
            ("JLinkInitialSpeed", "1000"),
            ("CCDoJlinkMultiTarget", "0"),
            ("CCScanChainNonARMDevices", "0"),
            ("CCJLinkMultiTarget", "0"),
            ("CCJLinkIRLength", "0"),
            ("CCJLinkCommRadio", "0"),
            ("CCJLinkTCPIP", "aaa.bbb.ccc.ddd"),
            ("CCJLinkSpeedRadioV2", "0"),
            ("CCRDICatchReset", "0"),
            ("CCRDICatchUndef", "0"),
            ("CCRDICatchSWI", "0"),
            ("CCRDICatchData", "0"),
            ("CCRDICatchPrefetch", "0"),
            ("CCRDICatchIRQ", "0"),
            ("CCRDICatchFIQ", "0"),
            ("CCJLinkBreakpointRadio", "0"),
            ("CCJLinkDoUpdateBreakpoints", "0"),
            ("CCJLinkUpdateBreakpoints", "_call_main"),
            ("CCJLinkInterfaceRadio", "1"),
            ("CCJLinkInterfaceCmdLine", "0"),
            ("CCCatchCORERESET", "0"),
            ("CCCatchMMERR", "0"),
            ("CCCatchNOCPERR", "0"),
            ("CCCatchCHRERR", "0"),
            ("CCCatchSTATERR", "0"),
            ("CCCatchBUSERR", "0"),
            ("CCCatchINTERR", "0"),
            ("CCCatchSFERR", "0"),
            ("CCCatchHARDERR", "0"),
            ("CCCatchDummy", "0"),
            ("OCJLinkScriptFile", "1"),
            ("CCJLinkUsbSerialNo", ""),
            ("CCTcpIpAlt", "0"),
            ("CCJLinkTcpIpSerialNo", ""),
            ("CCCpuClockEdit", ""),
            ("CCSwoClockAuto", "0"),
            ("CCSwoClockEdit", "2000"),
            ("OCJLinkTraceSource", "0"),
            ("OCJLinkTraceSourceDummy", "0"),
            ("OCJLinkDeviceName", "1"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CCUSBDevice", "1", "1"),
            ("CCJLinkResetList", "5", "6"),
        ]
        
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_lmiftdi_settings(self, config_elem, config_name):
        """Добавление настроек LMIFTDI"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "LMIFTDI_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "3"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Обычные опции
        regular_options = [
            ("OCDriverInfo", "1"),
            ("LmiftdiSpeed", "500"),
            ("CCLmiftdiDoLogfile", "0"),
            ("CCLmiftdiLogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("CCLmiFtdiInterfaceRadio", "1"),
            ("CCLmiFtdiInterfaceCmdLine", "0"),
            ("CCLmiftdiUsbSerialNo", ""),
            ("CCLmiftdiUsbSerialNoSelect", "0"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CCLmiftdiResetList", "0", "0"),
        ]
        
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_nulink_settings(self, config_elem, config_name):
        """Добавление настроек NULINK"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "NULINK_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "0"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        nulink_options = [
            ("OCDriverInfo", "1"),
            ("DoLogfile", "0"),
            ("LogFile", "$PROJ_DIR$\\cspycomm.log"),
        ]
        
        for name, value in nulink_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_pemicro_settings(self, config_elem, config_name):
        """Добавление настроек PEMICRO"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "PEMICRO_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "3"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        pemicro_options = [
            ("OCDriverInfo", "1"),
            ("CCJPEMicroShowSettings", "0"),
            ("DoLogfile", "0"),
            ("LogFile", "$PROJ_DIR$\\cspycomm.log"),
        ]
        
        for name, value in pemicro_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_stlink_settings(self, config_elem, config_name):
        """Добавление настроек ST-LINK"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "STLINK_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "8"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        # Базовые опции
        regular_options = [
            ("OCDriverInfo", "1"),
            ("CCSTLinkInterfaceCmdLine", "0"),
            ("CCSwoClockEdit", "2000"),
            ("DoLogfile", "0"),
            ("LogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("CCSTLinkDoUpdateBreakpoints", "0"),
            ("CCSTLinkCatchCORERESET", "0"),
            ("CCSTLinkCatchMMERR", "0"),
            ("CCSTLinkCatchNOCPERR", "0"),
            ("CCSTLinkCatchCHRERR", "0"),
            ("CCSTLinkCatchSTATERR", "0"),
            ("CCSTLinkCatchBUSERR", "0"),
            ("CCSTLinkCatchINTERR", "0"),
            ("CCSTLinkCatchSFERR", "0"),
            ("CCSTLinkCatchHARDERR", "0"),
            ("CCSTLinkCatchDummy", "0"),
            ("CCSTLinkUsbSerialNo", ""),
            ("CCSTLinkUsbSerialNoSelect", "0"),
            ("CCSTLinkDAPNumber", ""),
            ("CCSTLinkDebugAccessPortRadio", "0"),
            ("CCSTLinkUseServerSelect", "0"),
            ("CCSTLinkInterfaceRadio", "1"),
            ("CCSTLinkTargetVccEnable", "1"),
            ("CCSTLinkTargetVoltage", "3.3"),
            ("CCSwoClockAuto", "0"),
            ("CCCpuClockEdit", "80.0"),
            ("CCSTLinkUpdateBreakpoints", "_call_main"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CCSTLinkProbeList", "2", "2"),
            ("CCSTLinkResetList", "0", "3"),
            ("CCSTLinkJtagSpeedList", "0", "2"),
        ]
        
        for name, value in regular_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_thirdparty_settings(self, config_elem, config_name):
        """Добавление настроек THIRDPARTY"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "THIRDPARTY_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "0"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        thirdparty_options = [
            ("CThirdPartyDriverDll", "Browse to your third-party driver"),
            ("CThirdPartyLogFileCheck", "0"),
            ("CThirdPartyLogFileEditB", "$PROJ_DIR$\\cspycomm.log"),
            ("OCDriverInfo", "1"),
        ]
        
        for name, value in thirdparty_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_tifet_settings(self, config_elem, config_name):
        """Добавление настроек TIFET"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "TIFET_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "1"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        tifet_options = [
            ("OCDriverInfo", "1"),
            ("CCMSPFetInterfaceRadio", "0"),
            ("CCMSPFetInterfaceCmdLine", "0"),
            ("CCMSPFetTargetVccTypeDefault", "0"),
            ("CCMSPFetTargetVoltage", "3.0"),
            ("CCMSPFetVCCDefault", "1"),
            ("CCMSPFetTargetSettlingtime", "0"),
            ("CCMSPFetRadioJtagSpeedType", "1"),
            ("CCMSPFetUsbComPort", "Automatic"),
            ("CCMSPFetAllowAccessToBSL", "0"),
            ("CCMSPFetDoLogfile", "0"),
            ("CCMSPFetLogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("CCMSPFetRadioEraseFlash", "1"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CCMSPFetResetList", "0", "0"),
            ("CCMSPFetConnection", "0", "0"),
        ]
        
        for name, value in tifet_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_xds100_settings(self, config_elem, config_name):
        """Добавление настроек XDS100"""
        settings = ET.SubElement(config_elem, "settings")
        ET.SubElement(settings, "name").text = "XDS100_ID"
        ET.SubElement(settings, "archiveVersion").text = "2"
        
        data = ET.SubElement(settings, "data")
        ET.SubElement(data, "version").text = "9"
        ET.SubElement(data, "wantNonLocal").text = "1"
        ET.SubElement(data, "debug").text = "1" if config_name != "Release" else "0"
        
        xds100_options = [
            ("OCDriverInfo", "1"),
            ("TIPackageOverride", "0"),
            ("TIPackage", "C:\\ti\\iar\\ccs_base"),
            ("BoardFile", "$TOOLKIT_DIR$\\config\\debugger\\TexasInstruments\\xds\\UNKNOWN_XDS110_CJTAG.dat"),
            ("DoLogfile", "0"),
            ("LogFile", "$PROJ_DIR$\\cspycomm.log"),
            ("CCXds100BreakpointRadio", "0"),
            ("CCXds100DoUpdateBreakpoints", "0"),
            ("CCXds100UpdateBreakpoints", "_call_main"),
            ("CCXds100CatchReset", "0"),
            ("CCXds100CatchUndef", "0"),
            ("CCXds100CatchSWI", "0"),
            ("CCXds100CatchData", "0"),
            ("CCXds100CatchPrefetch", "0"),
            ("CCXds100CatchIRQ", "0"),
            ("CCXds100CatchFIQ", "0"),
            ("CCXds100CatchCORERESET", "0"),
            ("CCXds100CatchMMERR", "0"),
            ("CCXds100CatchNOCPERR", "0"),
            ("CCXds100CatchCHRERR", "0"),
            ("CCXds100CatchSTATERR", "0"),
            ("CCXds100CatchBUSERR", "0"),
            ("CCXds100CatchINTERR", "0"),
            ("CCXds100CatchSFERR", "0"),
            ("CCXds100CatchHARDERR", "0"),
            ("CCXds100CatchDummy", "0"),
            ("CCXds100CpuClockEdit", ""),
            ("CCXds100SwoClockAuto", "0"),
            ("CCXds100SwoClockEdit", "1000"),
            ("CCXds100HWResetDelay", "0"),
            ("CCXds100UsbSerialNo", ""),
            ("CCXds100UsbSerialNoSelect", "0"),
            ("CCXds100InterfaceRadio", "2"),
            ("CCXds100InterfaceCmdLine", "0"),
            ("CCXds100SWOPortRadio", "0"),
            ("CCXds100SWOPort", "1"),
            ("CCXDSTargetVccEnable", "0"),
            ("CCXDSTargetVoltage", "3.3"),
            ("OCXDSDigitalStatesConfigFile", "1"),
            ("OCSelectedCoreName", "1"),
        ]
        
        # Опции с version
        versioned_options = [
            ("CCXds100ResetList", "0", "1"),
            ("CCXds100JtagSpeedList", "0", "0"),
            ("CCXds100ProbeList", "3", "0"),
        ]
        
        for name, value in xds100_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value
        
        for name, value, version in versioned_options:
            option = ET.SubElement(data, "option")
            ET.SubElement(option, "name").text = name
            ET.SubElement(option, "version").text = version
            state_elem = ET.SubElement(option, "state")
            if value:
                state_elem.text = value

    def _add_debugger_plugins(self, config_elem):
        """Добавление плагинов отладчика"""
        debugger_plugins = ET.SubElement(config_elem, "debuggerPlugins")
        
        # Список плагинов RTOS
        rtos_plugins = [
            "Azure\\AzureArmPlugin.ENU.ewplugin",
            "CMX\\CmxArmPlugin.ENU.ewplugin",
            "CMX\\CmxTinyArmPlugin.ENU.ewplugin",
            "embOS\\embOSPlugin.ewplugin",
            "FreeRtos\\FreeRtosArmPlugin.ENU.ewplugin",
            "Mbed\\MbedArmPlugin.ENU.ewplugin",
            "Mbed\\MbedArmPlugin2.ENU.ewplugin",
            "OpenRTOS\\OpenRTOSPlugin.ewplugin",
            "SafeRTOS\\SafeRTOSPlugin.ewplugin",
            "SMX\\smxAwareIarArm9a.ewplugin",
            "ThreadX\\ThreadXArmPlugin.ENU.ewplugin",
            "uCOS-II\\uCOS-II-286-KA-CSpy.ewplugin",
            "uCOS-II\\uCOS-II-KA-CSpy.ewplugin",
            "uCOS-III\\uCOS-III-KA-CSpy.ewplugin",
        ]
        
        # Общие плагины
        common_plugins = [
            "Orti\\Orti.ENU.ewplugin",
            "TargetAccessServer\\TargetAccessServer.ENU.ewplugin",
            "uCProbe\\uCProbePlugin.ENU.ewplugin",
        ]
        
        # Добавляем RTOS плагины
        for plugin_path in rtos_plugins:
            plugin = ET.SubElement(debugger_plugins, "plugin")
            ET.SubElement(plugin, "file").text = f"$TOOLKIT_DIR$\\plugins\\rtos\\{plugin_path}"
            ET.SubElement(plugin, "loadFlag").text = "0"
        
        # Добавляем общие плагины
        for plugin_path in common_plugins:
            plugin = ET.SubElement(debugger_plugins, "plugin")
            ET.SubElement(plugin, "file").text = f"$EW_DIR$\\common\\plugins\\{plugin_path}"
            ET.SubElement(plugin, "loadFlag").text = "0"
            
    def generate_eww_file(self):
        """
        Генерация .eww файла (workspace)
        """
        print(f"\n📝 Генерация {self.eww_file.name}...")
        
        # Создаём корневой элемент workspace
        root = ET.Element("workspace")
        
        # Добавляем версию файла (важно для IAR)
        ET.SubElement(root, "fileVersion").text = "1"
        
        # Добавляем проект
        project_elem = ET.SubElement(root, "project")
        path_elem = ET.SubElement(project_elem, "path")
        
        # Используем правильный относительный путь
        path_elem.text = f"$WS_DIR$\\{self.project_name}.ewp"
        
        # Добавляем пустой элемент batchBuild (как в оригинале)
        batch_build = ET.SubElement(root, "batchBuild")
        
        # Форматируем XML с правильным объявлением
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(
            indent="    ", 
            encoding='UTF-8'
        )
        
        # Убираем лишние пустые строки
        xml_str = '\n'.join([line for line in xml_str.decode('utf-8').split('\n') if line.strip()])
        
        with open(self.eww_file, 'w', encoding='UTF-8') as f:
            f.write(xml_str)
        
        print(f"✅ Сгенерирован {self.eww_file.name}")
    
    def generate_ewt_file(self):
        """
        Генерация .ewt файла (настройки C-STAT)
        """
        print(f"\n📝 Генерация {self.ewt_file.name}...")
        
        root = ET.Element("project")
        ET.SubElement(root, "fileVersion").text = "4"
        
        for config_name in self.configurations:
            config_elem = ET.SubElement(root, "configuration")
            ET.SubElement(config_elem, "name").text = config_name
            
            toolchain = ET.SubElement(config_elem, "toolchain")
            ET.SubElement(toolchain, "name").text = "ARM"
            
            debug = "1" if config_name != "Release" else "0"
            ET.SubElement(config_elem, "debug").text = debug
            
            # Настройки C-STAT
            settings = ET.SubElement(config_elem, "settings")
            ET.SubElement(settings, "name").text = "C-STAT"
            ET.SubElement(settings, "archiveVersion").text = "519"
            
            data = ET.SubElement(settings, "data")
            ET.SubElement(data, "version").text = "519"
            
            # cstatargs
            cstatargs = ET.SubElement(data, "cstatargs")
            
            use_extra_args = ET.SubElement(cstatargs, "useExtraArgs")
            use_extra_args.text = "0"
            
            extra_args = ET.SubElement(cstatargs, "extraArgs")
            
            timeout_enabled = ET.SubElement(cstatargs, "analyzeTimeoutEnabled")
            timeout_enabled.text = "1"
            
            timeout = ET.SubElement(cstatargs, "analyzeTimeout")
            timeout.text = "600"
            
            parallel = ET.SubElement(cstatargs, "enableParallel")
            parallel.text = "1"
            
            threads = ET.SubElement(cstatargs, "parallelThreads")
            threads.text = "11"
            
            false_positives = ET.SubElement(cstatargs, "enableFalsePositives")
            false_positives.text = "0"
            
            limit_enabled = ET.SubElement(cstatargs, "messagesLimitEnabled")
            limit_enabled.text = "1"
            
            limit = ET.SubElement(cstatargs, "messagesLimit")
            limit.text = "100"
            
            output_dir = ET.SubElement(cstatargs, "outputDir")
            output_dir.text = f"{config_name}/C-STAT"
            
            # cstat_settings
            cstat_settings = ET.SubElement(data, "cstat_settings")
            
            cstat_version = ET.SubElement(cstat_settings, "cstat_version")
            cstat_version.text = "2.7.2"
            
            checks_tree = ET.SubElement(cstat_settings, "checks_tree")
            
            # STDCHECKS package
            stdchecks = ET.SubElement(checks_tree, "package", name="STDCHECKS", enabled="true")
            
            # Основные группы проверок
            groups = ["ARR", "ATH", "MEM", "PTR", "RED", "SPC"]
            for group_name in groups:
                group = ET.SubElement(stdchecks, "group", enabled="true", name=group_name)
                check = ET.SubElement(group, "check", name=f"{group_name}-default", enabled="true")
        
        # Форматируем XML
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ", encoding='UTF-8')
        
        # Дополнительная обработка для самозакрывающихся тегов
        xml_str = xml_str.decode('utf-8')
        xml_str = xml_str.replace('> <', '><')
        xml_str = xml_str.replace('></extraArgs>', '/>')
        
        # Исправляем форматирование для consistency
        lines = []
        for line in xml_str.split('\n'):
            # Убираем лишние пробелы в пустых строках
            if line.strip() or not line:
                lines.append(line.rstrip())
        
        xml_str = '\n'.join(lines)
        
        with open(self.ewt_file, 'w', encoding='UTF-8') as f:
            f.write(xml_str)
        
        print(f"✅ Сгенерирован {self.ewt_file.name}")
    
    def generate_readme(self):
        """
        Генерация README файла с описанием сгенерированных файлов
        """
        readme_file = self.output_dir / "README_IAR_FILES.txt"
        
        content = f"""# IAR Project Files for {self.project_name}

Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Сгенерированные файлы

1. **{self.project_name}.ewp** - основной файл проекта
   - Конфигурации: Debug, Release, Flash_ST-Link
   - Настройки компилятора, ассемблера, линкера
   - ✅ ВСЕ заголовочные файлы (.h) добавлены в проект
   - ✅ Правильные include paths для поиска .h файлов

2. **{self.project_name}.ewd** - настройки отладчика
   - Поддержка ST-LINK
   - Настройки SWD интерфейса
   - Точки останова при старте (main)

3. **{self.project_name}.eww** - рабочее пространство
   - Ссылка на проект

4. **{self.project_name}.ewt** - настройки C-STAT
   - Базовые проверки кода
   - Настройки параллельного анализа

## Пути для поиска заголовочных файлов (include paths)

Следующие пути автоматически добавлены в проект:
{chr(10).join(self.get_detailed_include_paths())}

## Структура проекта
{self.project_name_lower}/
├── .gitignore
├── README.md
├── CHANGELOG.md
├── iar/
│ ├── {self.project_name}.ewp
│ ├── {self.project_name}.ewd
│ ├── {self.project_name}.eww
│ └── {self.project_name}.ewt
└── project/
├── main.c
├── config.c
├── config.h
├── app/
│ ├── *_app.c
│ └── *_app.h
├── build_variant/
│ ├── defs.h
│ └── version.h
├── firmware/
├── mcu_platforms/
│ └── stm32l412/
│ ├── *.icf
│ └── [module folders]/
├── modules/
│ ├── button/
│ ├── led/
│ └── uart/
└── modules_configs/
└── *.h

## Использование

1. Откройте IAR Embedded Workbench
2. Выберите File -> Open -> Workspace...
3. Откройте файл: `{self.eww_file}`
4. Выберите нужную конфигурацию в выпадающем списке
5. Стройте проект (F7) или отлаживайте (Ctrl+D)

## Важно для работы с .h файлами

✅ **ВСЕ ЗАГОЛОВОЧНЫЕ ФАЙЛЫ** добавлены в проект и будут видны компилятору
✅ **INCLUDE PATHS** настроены для всех папок проекта
✅ **СТРУКТУРА ПАПОК** полностью сохранена

Если заголовочные файлы всё ещё не видны, проверьте:
1. Что пути в include paths используют обратную косую черту (`\\`)
2. Что в исходных .c файлах используются правильные #include директивы
3. Что все необходимые папки существуют в проекте

## Конфигурации

- **Debug** - отладочная версия с полной информацией для отладки
- **Release** - оптимизированная версия для релиза
- **Flash_ST-Link** - специальная конфигурация для прошивки через ST-LINK

## Примечания

- Все пути используют переменные `$PROJ_DIR$` и `$TOOLKIT_DIR$`
- Linker script (.icf) для Debug находится в `project/stm32l412xx_flash.icf`
- Для корректной работы убедитесь, что структура папок соответствует требованиям
"""
        
        with open(readme_file, 'w', encoding='UTF-8') as f:
            f.write(content)
        
        print(f"✅ Сгенерирован README: {readme_file}")
    
    def generate_all(self):
        """
        Генерация всех файлов IAR проекта
        """
        print("=" * 70)
        print(f"🚀 Генерация IAR файлов для проекта {self.project_name}")
        print("=" * 70)
        
        # Поиск исходных файлов
        source_files, header_files = self.find_source_files()
        
        # Поиск linker scripts
        linker_scripts = self.find_linker_scripts()
        
        if not source_files and not header_files:
            print("⚠️  Внимание: файлы не найдены!")
            return
        
        print(f"\n📊 Статистика:")
        print(f"   - Исходных файлов (.c, .cpp, .s): {len(source_files)}")
        print(f"   - Заголовочных файлов (.h, .hpp): {len(header_files)}")
        print(f"   - Linker scripts: {len(linker_scripts)}")
        
        # Генерация файлов
        self.generate_ewp_file(source_files, header_files, linker_scripts)
        self.generate_ewd_file()
        self.generate_eww_file()
        self.generate_ewt_file()
        self.generate_readme()
        
        print("\n" + "=" * 70)
        print("✅ Генерация IAR файлов завершена успешно!")
        print("=" * 70)
        print(f"\n📁 Сгенерированные файлы находятся в:")
        print(f"   {self.output_dir}")
        print("\n📋 Файлы:")
        print(f"   📄 {self.ewp_file.name}")
        print(f"   📄 {self.ewd_file.name}")
        print(f"   📄 {self.eww_file.name}")
        print(f"   📄 {self.ewt_file.name}")
        print(f"   📄 README_IAR_FILES.txt")
        print("\n👉 Для использования:")
        print(f"   1. Откройте IAR Embedded Workbench")
        print(f"   2. File -> Open -> Workspace...")
        print(f"   3. Выберите {self.eww_file.name}")
        print("\n✅ Все заголовочные файлы (.h) добавлены в проект")
        print("✅ Include paths настроены для всех папок")
        print("=" * 70)


def main():
    """
    Основная функция
    """
    parser = argparse.ArgumentParser(
        description='Генератор IAR файлов проекта (ewp, ewd, eww, ewt)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  %(prog)s C:\\Projects\\MyProject MyProject
  %(prog)s C:\\Projects\\Gyro Gyro -o C:\\Output
        """
    )
    
    parser.add_argument(
        'project_path',
        help='Путь к корневой директории проекта'
    )
    
    parser.add_argument(
        'project_name',
        help='Имя проекта (например: Gyro, MyProject)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Выходная директория для IAR файлов (по умолчанию: {project_path})'
    )
    
    args = parser.parse_args()
    
    try:
        # Проверка существования директории
        if not os.path.exists(args.project_path):
            print(f"❌ Ошибка: Директория {args.project_path} не найдена")
            return 1
        
        # Создание генератора
        generator = IARProjectFilesGenerator(
            project_path=args.project_path,
            project_name=args.project_name,
            output_dir=args.output
        )
        
        # Генерация файлов
        generator.generate_all()
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())