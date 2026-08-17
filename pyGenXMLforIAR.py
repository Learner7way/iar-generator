#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from pathlib import Path
import shutil
from datetime import datetime
import re

class IARProjectTemplateGenerator:
    def __init__(self, source_dir, output_dir=None):
        """
        Инициализация генератора шаблонов IAR
        
        :param source_dir: Исходная директория с проектом
        :param output_dir: Директория для выходных файлов
        """
        self.source_dir = Path(source_dir)
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Директория {source_dir} не найдена")
            
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path.cwd() / "iar_template_output"
            
        # Создаем структуру для шаблона
        self.template_group_dir = self.output_dir / "GyroProject"
        self.template_dir = self.template_group_dir / "GyroTemplate"
        
        # Конфигурации из оригинального проекта
        self.configurations = ['Debug', 'Release', 'Flash_ST-Link']
        
    def get_all_source_files(self):
        """
        Получение всех исходных файлов из проекта с сохранением структуры
        """
        source_files = []
        source_extensions = {'.c', '.cpp', '.h', '.hpp', '.s', '.asm', '.icf', '.mac'}
        
        print("\n🔍 Поиск исходных файлов...")
        for root, dirs, files in os.walk(self.source_dir):
            # Пропускаем бинарные и временные директории
            dirs[:] = [d for d in dirs if d not in ['bin', 'iar', 'Debug', 'Release', 'Flash_ST-Link', 
                                                    '.git', '__pycache__', 'settings']]
            
            for file in files:
                file_ext = Path(file).suffix.lower()
                if file_ext in source_extensions:
                    full_path = Path(root) / file
                    # Относительный путь относительно исходной директории
                    rel_path = full_path.relative_to(self.source_dir)
                    source_files.append(str(rel_path))
                    print(f"  📄 Найден: {rel_path}")
                    
        return sorted(source_files)
    
    def parse_ewp_file(self):
        """
        Парсинг существующего .ewp файла для извлечения структуры проекта
        """
        ewp_files = list(self.source_dir.glob("**/*.ewp"))
        if not ewp_files:
            print("⚠️  Файл .ewp не найден, будет создан новый")
            return None
            
        ewp_file = ewp_files[0]
        print(f"\n📁 Анализ файла проекта: {ewp_file.name}")
        
        try:
            tree = ET.parse(ewp_file)
            root = tree.getroot()
            
            # Извлекаем информацию о конфигурациях и файлах
            project_files = []
            for file_elem in root.findall('file'):
                name_elem = file_elem.find('name')
                if name_elem is not None and name_elem.text:
                    project_files.append(name_elem.text)
                    print(f"  📄 Файл в проекте: {name_elem.text}")
                    
            return {
                'tree': tree,
                'root': root,
                'files': project_files
            }
        except Exception as e:
            print(f"⚠️  Ошибка при парсинге .ewp: {e}")
            return None
    
    def parse_ewd_file(self):
        """
        Парсинг существующего .ewd файла для извлечения настроек отладчика
        """
        ewd_files = list(self.source_dir.glob("**/*.ewd"))
        if not ewd_files:
            print("⚠️  Файл .ewd не найден")
            return None
            
        ewd_file = ewd_files[0]
        print(f"\n🔧 Анализ файла отладчика: {ewd_file.name}")
        
        try:
            tree = ET.parse(ewd_file)
            return tree
        except Exception as e:
            print(f"⚠️  Ошибка при парсинге .ewd: {e}")
            return None
    
    def create_template_group_file(self):
        """
        Создание файла описания группы шаблонов
        """
        group_file = self.output_dir / "GyroProject.ENU.projtempl"
        
        root = ET.Element("templategroup")
        
        description = ET.SubElement(root, "description")
        description.text = "Шаблоны проектов на основе гироскопа"
        
        displayname = ET.SubElement(root, "displayname")
        displayname.text = "GyroProject"
        
        # Форматируем XML
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ", encoding='utf-8')
        
        with open(group_file, 'wb') as f:
            f.write(xml_str)
            
        print(f"\n✅ Создан файл группы шаблонов: {group_file}")
        
    def create_template_file(self, source_files):
        """
        Создание файла описания шаблона проекта
        """
        template_file = self.template_dir / "GyroTemplate.projtempl"
        
        root = ET.Element("template")
        
        description = ET.SubElement(root, "description")
        description.text = "Шаблон проекта гироскопа с поддержкой STM32L412"
        
        displayname = ET.SubElement(root, "displayname")
        displayname.text = "GyroTemplate"
        
        files_elem = ET.SubElement(root, "files")
        
        # Добавляем все исходные файлы с переменной $PROJ_DIR$
        for source_file in source_files:
            file_elem = ET.SubElement(files_elem, "file")
            # Используем обратные слеши для Windows
            file_elem.text = f"$PROJ_DIR$\\{source_file.replace('/', '\\')}"
        
        # Форматируем XML
        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="   ", encoding='utf-8')
        
        with open(template_file, 'wb') as f:
            f.write(xml_str)
            
        print(f"✅ Создан файл описания шаблона: {template_file}")
        
    def copy_project_files(self):
        """
        Копирование файлов проекта в директорию шаблона с сохранением структуры
        """
        print("\n📁 Копирование файлов проекта...")
        
        # Расширения для копирования
        include_extensions = {'.c', '.cpp', '.h', '.hpp', '.s', '.asm', '.icf', '.mac', '.ewp', '.ewd', '.eww'}
        exclude_extensions = {'.o', '.out', '.hex', '.bin', '.elf', '.map', '.log', '.lst', '.dep'}
        exclude_dirs = {'Debug', 'Release', 'Flash_ST-Link', 'settings', '.git', '__pycache__'}
        
        files_copied = 0
        for root, dirs, files in os.walk(self.source_dir):
            # Исключаем директории
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            for file in files:
                file_ext = Path(file).suffix.lower()
                if file_ext in exclude_extensions:
                    continue
                    
                src_path = Path(root) / file
                rel_path = src_path.relative_to(self.source_dir)
                dst_path = self.template_dir / rel_path
                
                # Создаем директорию назначения
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Копируем файл
                shutil.copy2(src_path, dst_path)
                files_copied += 1
                if files_copied % 50 == 0:
                    print(f"  ... скопировано {files_copied} файлов")
                    
        print(f"✅ Скопировано файлов: {files_copied}")
        
    def create_templproj_files(self):
        """
        Создание templproj.ewp и templproj.ewd файлов на основе существующих
        """
        print("\n📝 Создание templproj файлов...")
        
        # Обработка .ewp файла
        ewp_data = self.parse_ewp_file()
        if ewp_data and ewp_data['tree']:
            # Модифицируем пути в файле проекта
            root = ewp_data['root']
            
            # Обновляем пути к файлам
            for file_elem in root.findall('file'):
                name_elem = file_elem.find('name')
                if name_elem is not None and name_elem.text:
                    # Убеждаемся что используем $PROJ_DIR$
                    if not '$PROJ_DIR$' in name_elem.text:
                        # Извлекаем имя файла из пути
                        file_name = Path(name_elem.text).name
                        name_elem.text = f"$PROJ_DIR$\\{file_name}"
            
            # Сохраняем как templproj.ewp
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(indent="    ", encoding='utf-8')
            with open(self.template_dir / "templproj.ewp", 'wb') as f:
                f.write(xml_str)
            print("✅ Создан templproj.ewp на основе существующего проекта")
        else:
            # Создаем новый templproj.ewp из примера
            self._create_default_templproj()
        
        # Обработка .ewd файла
        ewd_tree = self.parse_ewd_file()
        if ewd_tree:
            xml_str = minidom.parseString(ET.tostring(ewd_tree.getroot())).toprettyxml(indent="    ", encoding='utf-8')
            with open(self.template_dir / "templproj.ewd", 'wb') as f:
                f.write(xml_str)
            print("✅ Создан templproj.ewd на основе существующего проекта")
            
        # Копируем .icf файлы
        icf_files = list(self.source_dir.glob("**/*.icf"))
        for icf_file in icf_files:
            rel_path = icf_file.relative_to(self.source_dir)
            dst_path = self.template_dir / rel_path
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(icf_file, dst_path)
            print(f"✅ Скопирован linker script: {rel_path}")
            
        # Копируем .eww файл если есть
        eww_files = list(self.source_dir.glob("*.eww"))
        for eww_file in eww_files:
            shutil.copy2(eww_file, self.template_dir / "templproj.eww")
            print(f"✅ Создан templproj.eww")
    
    def _create_default_templproj(self):
        """
        Создание шаблонного templproj.ewp на основе предоставленного примера
        """
        # Используем предоставленный templproj.ewp.txt как основу
        template_content = """<?xml version="1.0" encoding="UTF-8"?>
<project>
    <fileVersion>4</fileVersion>
    <configuration>
        <name>Debug</name>
        <toolchain>
            <name>ARM</name>
        </toolchain>
        <debug>1</debug>
        <settings>
            <name>General</name>
            <archiveVersion>3</archiveVersion>
            <data>
                <version>37</version>
                <wantNonLocal>1</wantNonLocal>
                <debug>1</debug>
                <option>
                    <name>ExePath</name>
                    <state>Debug\\Exe</state>
                </option>
                <option>
                    <name>ObjPath</name>
                    <state>Debug\\Obj</state>
                </option>
                <option>
                    <name>ListPath</name>
                    <state>Debug\\List</state>
                </option>
                <option>
                    <name>BrowseInfoPath</name>
                    <state>Debug\\BrowseInfo</state>
                </option>
                <option>
                    <name>OGChipSelectEditMenu</name>
                    <state>STM32L412RB	ST STM32L412RB</state>
                </option>
                <option>
                    <name>CoreVariant</name>
                    <version>34</version>
                    <state>39</state>
                </option>
                <option>
                    <name>FPU2</name>
                    <version>0</version>
                    <state>4</state>
                </option>
                <option>
                    <name>DSPExtension</name>
                    <state>1</state>
                </option>
            </data>
        </settings>
        <settings>
            <name>ICCARM</name>
            <archiveVersion>2</archiveVersion>
            <data>
                <version>39</version>
                <wantNonLocal>1</wantNonLocal>
                <debug>1</debug>
                <option>
                    <name>CCDebugInfo</name>
                    <state>1</state>
                </option>
                <option>
                    <name>IProcessor</name>
                    <state>1</state>
                </option>
                <option>
                    <name>IFpuProcessor</name>
                    <state>1</state>
                </option>
                <option>
                    <name>CCOptLevel</name>
                    <state>1</state>
                </option>
            </data>
        </settings>
        <settings>
            <name>ILINK</name>
            <archiveVersion>0</archiveVersion>
            <data>
                <version>28</version>
                <wantNonLocal>1</wantNonLocal>
                <debug>1</debug>
                <option>
                    <name>IlinkIcfOverride</name>
                    <state>0</state>
                </option>
                <option>
                    <name>IlinkIcfFile</name>
                    <state>$TOOLKIT_DIR$/config/linker/ST/stm32l412xB.icf</state>
                </option>
                <option>
                    <name>IlinkMapFile</name>
                    <state>1</state>
                </option>
            </data>
        </settings>
    </configuration>
    <configuration>
        <name>Flash_ST-Link</name>
        <toolchain>
            <name>ARM</name>
        </toolchain>
        <debug>1</debug>
        <settings>
            <name>General</name>
            <archiveVersion>3</archiveVersion>
            <data>
                <version>37</version>
                <wantNonLocal>1</wantNonLocal>
                <debug>1</debug>
                <option>
                    <name>ExePath</name>
                    <state>Flash_ST-Link\\Exe</state>
                </option>
                <option>
                    <name>ObjPath</name>
                    <state>Flash_ST-Link\\Obj</state>
                </option>
                <option>
                    <name>OGChipSelectEditMenu</name>
                    <state>STM32L412RB	ST STM32L412RB</state>
                </option>
            </data>
        </settings>
        <settings>
            <name>ILINK</name>
            <archiveVersion>0</archiveVersion>
            <data>
                <version>28</version>
                <wantNonLocal>1</wantNonLocal>
                <debug>1</debug>
                <option>
                    <name>IlinkIcfOverride</name>
                    <state>1</state>
                </option>
                <option>
                    <name>IlinkIcfFile</name>
                    <state>$PROJ_DIR$\\iar\\stm32l412rb_flash.icf</state>
                </option>
            </data>
        </settings>
    </configuration>
</project>"""
        
        with open(self.template_dir / "templproj.ewp", 'w', encoding='utf-8') as f:
            f.write(template_content)
        print("✅ Создан новый templproj.ewp на основе шаблона")
    
    def copy_shared_files(self):
        """
        Копирование shared.icf и других важных файлов
        """
        print("\n📄 Копирование shared файлов...")
        
        # Копируем shared.icf если есть
        shared_icf_src = self.source_dir / "shared.icf"
        if shared_icf_src.exists():
            shutil.copy2(shared_icf_src, self.template_dir / "shared.icf")
            print("✅ Скопирован shared.icf")
        else:
            # Создаем shared.icf из предоставленного примера
            shared_content = """// This is the difference between the ROM and the RAM parts of the
// shared object. The last ROM byte is placed at address X (which
// is offset X in the file), the next byte (offset X+1) is RAM
// and has the address X+1+so_alignment. The alignment must be
// a power of two. 0x1000 is the default.

so_alignment 0x1000;

// This names the shared object, it sets the member DT_SONAME
// in the .dynamic section of the shared object to be myName.

so_name "myName";

// This exports the symbols sym1 and sym2 from the shared object.
// Exported symbols are kept by the linker, not exported symbols
// are eliminated unless references from an export symbol.

so_export globalData;
so_export GetLocalData;
so_export GetGlobalData;

// These four blocks can be used to control the layout of content in
// the shared object.

define block so_code  with alignment=4 { ro code };
define block so_const with alignment=4 { ro data };
define block so_data  with alignment=4 { rw data };
define block so_bss   with alignment=4 { zi };"""
            
            with open(self.template_dir / "shared.icf", 'w', encoding='utf-8') as f:
                f.write(shared_content)
            print("✅ Создан shared.icf из шаблона")
    
    def create_readme(self):
        """
        Создание README файла с инструкциями
        """
        readme_content = f"""# IAR Project Template - GyroProject

Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Инструкция по установке шаблона

1. **Найдите директорию шаблонов IAR:**
   - Для IAR 9.60: `C:\\Program Files\\IAR Systems\\Embedded Workbench 9.6\\arm\\config\\template\\project\\`
   - Запустите файловый менеджер с правами администратора!

2. **Скопируйте папку шаблона:**
   - Скопируйте папку `GyroProject` из:
     `{self.output_dir}`
   - В директорию:
     `C:\\Program Files\\IAR Systems\\Embedded Workbench 9.6\\arm\\config\\template\\project\\`

3. **Проверка структуры:**
   - После копирования должны быть файлы:
     - `$TOOLKIT_DIR$\\config\\template\\project\\GyroProject.ENU.projtempl`
     - `$TOOLKIT_DIR$\\config\\template\\project\\GyroProject\\GyroTemplate\\templproj.ewp`
     - `$TOOLKIT_DIR$\\config\\template\\project\\GyroProject\\GyroTemplate\\templproj.ewd` (если есть)

4. **Использование шаблона:**
   - В IAR Workbench выберите `Project -> Create New Project...`
   - Найдите группу "GyroProject"
   - Выберите шаблон "GyroTemplate"
   - Укажите папку для нового проекта

## Конфигурации проекта

- **Debug** - отладочная конфигурация
- **Release** - релизная конфигурация
- **Flash_ST-Link** - конфигурация для прошивки через ST-Link

## Важные файлы

- `templproj.ewp` - основной файл проекта
- `templproj.ewd` - настройки отладчика
- `shared.icf` - linker script для shared объектов
- `iar/stm32l412rb_flash.icf` - linker script для Flash_ST-Link конфигурации

## Примечания

- Все пути используют переменную `$PROJ_DIR$`
- Сохранена оригинальная структура папок
- Добавлена поддержка STM32L412RB
- Включены настройки для ST-Link отладчика
"""
        
        readme_file = self.output_dir / "README.txt"
        with open(readme_file, 'w', encoding='utf-8') as f:
            f.write(readme_content)
            
        print(f"\n✅ Создан README файл: {readme_file}")
        
    def create_directory_structure(self):
        """
        Создание необходимой структуры директорий
        """
        # Создаем структуру папок как в исходном проекте
        dirs_to_create = [
            self.template_dir / "project" / "app",
            self.template_dir / "project" / "build_variant",
            self.template_dir / "project" / "firmware",
            self.template_dir / "project" / "libs",
            self.template_dir / "project" / "mcu_platforms" / "stm32" / "errors",
            self.template_dir / "project" / "mcu_platforms" / "stm32" / "gui",
            self.template_dir / "project" / "mcu_platforms" / "stm32" / "storage",
            self.template_dir / "project" / "mcu_platforms" / "stm32" / "uart",
            self.template_dir / "project" / "middleware",
            self.template_dir / "project" / "modules" / "errors",
            self.template_dir / "project" / "modules" / "gui" / "button pins",
            self.template_dir / "project" / "modules" / "gui" / "led pins",
            self.template_dir / "project" / "modules" / "storage",
            self.template_dir / "project" / "modules" / "uart",
            self.template_dir / "project" / "modules_configs" / "gui",
            self.template_dir / "iar",
            self.template_dir / "docs",
            self.template_dir / "resources",
            self.template_dir / "utils",
            self.template_dir / "bin",
        ]
        
        for dir_path in dirs_to_create:
            dir_path.mkdir(parents=True, exist_ok=True)
            
        print("\n📂 Создана структура директорий")
        
    def generate(self):
        """
        Основной метод генерации шаблона
        """
        print("=" * 70)
        print("🚀 Генерация IAR Project Template для GyroProject")
        print("=" * 70)
        
        print(f"\n📂 Исходная директория: {self.source_dir}")
        print(f"📂 Выходная директория: {self.output_dir}")
        
        # Создаем выходные директории
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_group_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаем структуру папок
        self.create_directory_structure()
        
        # Получаем список исходных файлов
        source_files = self.get_all_source_files()
        print(f"\n✅ Найдено исходных файлов: {len(source_files)}")
        
        # Создаем XML файлы
        self.create_template_group_file()
        self.create_template_file(source_files)
        
        # Копируем файлы проекта
        self.copy_project_files()
        
        # Создаем templproj файлы
        self.create_templproj_files()
        
        # Копируем shared файлы
        self.copy_shared_files()
        
        # Создаем README
        self.create_readme()
        
        print("\n" + "=" * 70)
        print("✅ Генерация шаблона завершена успешно!")
        print("=" * 70)
        print(f"\n📁 Шаблон создан в: {self.template_group_dir}")
        print("\n📋 Следующие шаги:")
        print("   1. Запустите файловый менеджер от имени администратора")
        print("   2. Скопируйте папку 'GyroProject' в:")
        print("      C:\\Program Files\\IAR Systems\\Embedded Workbench 9.6\\arm\\config\\template\\project\\")
        print("   3. Перезапустите IAR Embedded Workbench")
        print("   4. Создайте новый проект через Project -> Create New Project...")
        print("   5. Выберите группу 'GyroProject' и шаблон 'GyroTemplate'")
        print("=" * 70)


def main():
    """
    Основная функция
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Генератор IAR Project Template из существующего проекта')
    parser.add_argument('source_dir', help='Путь к исходной директории проекта (например: C:\\Projects\\my_project)')
    parser.add_argument('-o', '--output', help='Выходная директория для шаблона (по умолчанию: ./iar_template_output)')
    
    args = parser.parse_args()
    
    try:
        # Проверяем существование исходной директории
        if not os.path.exists(args.source_dir):
            print(f"❌ Ошибка: Директория {args.source_dir} не найдена")
            return 1
            
        generator = IARProjectTemplateGenerator(args.source_dir, args.output)
        generator.generate()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    return 0


if __name__ == "__main__":
    exit(main())