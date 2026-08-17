#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Генератор устанавливаемого шаблона IAR (GyroProject).

Перенесён из корневого pyGenXMLforIAR.py (Этап 4 ROADMAP): создаёт папку
GyroProject/GyroTemplate с templproj.ewp/.ewd, shared.icf, README и копиями
исходников, готовую для установки в
`<IAR>/arm/config/template/project/`.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from xml.dom import minidom
from xml.etree import ElementTree as ET


class IARProjectTemplateGenerator:
    """Создание шаблона проекта IAR из существующего проекта."""

    # Расширения, включаемые в шаблон при копировании
    INCLUDE_EXTENSIONS = frozenset(
        {
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".s",
            ".asm",
            ".icf",
            ".mac",
            ".ewp",
            ".ewd",
            ".eww",
        }
    )
    # Расширения, исключаемые при копировании (артефакты сборки)
    EXCLUDE_EXTENSIONS = frozenset(
        {
            ".o",
            ".out",
            ".hex",
            ".bin",
            ".elf",
            ".map",
            ".log",
            ".lst",
            ".dep",
        }
    )
    EXCLUDE_DIRS = frozenset(
        {
            "Debug",
            "Release",
            "Flash_ST-Link",
            "settings",
            ".git",
            "__pycache__",
        }
    )
    SOURCE_EXTENSIONS = frozenset(
        {
            ".c",
            ".cpp",
            ".h",
            ".hpp",
            ".s",
            ".asm",
            ".icf",
            ".mac",
        }
    )

    def __init__(self, source_dir: str, output_dir: Optional[str] = None) -> None:
        """Инициализация генератора шаблона.

        :param source_dir: Исходная директория проекта.
        :param output_dir: Директория для вывода (по умолчанию ./iar_template_output).
        """
        self.source_dir = Path(source_dir)
        if not self.source_dir.exists():
            raise FileNotFoundError(f"Директория не найдена: {source_dir}")

        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path.cwd() / "iar_template_output"

        self.template_group_dir = self.output_dir / "GyroProject"
        self.template_dir = self.template_group_dir / "GyroTemplate"

        self.configurations = ["Debug", "Release", "Flash_ST-Link"]

    def get_all_source_files(self) -> List[str]:
        """Список исходных файлов проекта (относительные пути, отсортированы)."""
        source_files = []
        print("[*] Поиск исходных файлов...")
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            for file in files:
                if Path(file).suffix.lower() in self.SOURCE_EXTENSIONS:
                    full_path = Path(root) / file
                    rel_path = full_path.relative_to(self.source_dir)
                    source_files.append(str(rel_path))
                    print(f"  [SRC] {rel_path}")
        return sorted(source_files)

    def parse_ewp_file(self) -> Optional[dict]:
        """Парсинг существующего .ewp файла для извлечения структуры проекта."""
        ewp_files = list(self.source_dir.glob("**/*.ewp"))
        if not ewp_files:
            print("[WARN] Файл .ewp не найден, будет создан новый")
            return None

        ewp_file = ewp_files[0]
        print(f"[*] Анализ файла проекта: {ewp_file.name}")
        try:
            tree = ET.parse(ewp_file)
            root = tree.getroot()
            project_files = []
            for file_elem in root.findall("file"):
                name_elem = file_elem.find("name")
                if name_elem is not None and name_elem.text:
                    project_files.append(name_elem.text)
                    print(f"  [FILE] {name_elem.text}")
            return {"tree": tree, "root": root, "files": project_files}
        except Exception as e:
            print(f"[WARN] Ошибка при парсинге .ewp: {e}")
            return None

    def parse_ewd_file(self) -> Optional[ET.ElementTree]:
        """Парсинг существующего .ewd файла для извлечения настроек отладчика."""
        ewd_files = list(self.source_dir.glob("**/*.ewd"))
        if not ewd_files:
            print("[WARN] Файл .ewd не найден")
            return None

        ewd_file = ewd_files[0]
        print(f"[*] Анализ файла отладчика: {ewd_file.name}")
        try:
            return ET.parse(ewd_file)
        except Exception as e:
            print(f"[WARN] Ошибка при парсинге .ewd: {e}")
            return None

    def create_template_group_file(self) -> None:
        """Создание файла описания группы шаблонов (GyroProject.ENU.projtempl)."""
        group_file = self.output_dir / "GyroProject.ENU.projtempl"

        root = ET.Element("templategroup")
        description = ET.SubElement(root, "description")
        description.text = "Шаблоны проектов на основе гироскопа"
        displayname = ET.SubElement(root, "displayname")
        displayname.text = "GyroProject"

        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(
            indent="   ", encoding="utf-8"
        )
        with open(group_file, "wb") as f:
            f.write(xml_str)
        print(f"[OK] Создан файл группы шаблонов: {group_file}")

    def create_template_file(self, source_files: List[str]) -> None:
        """Создание файла описания шаблона (GyroTemplate.projtempl)."""
        self.template_dir.mkdir(parents=True, exist_ok=True)
        template_file = self.template_dir / "GyroTemplate.projtempl"

        root = ET.Element("template")
        description = ET.SubElement(root, "description")
        description.text = "Шаблон проекта гироскопа с поддержкой STM32L412"
        displayname = ET.SubElement(root, "displayname")
        displayname.text = "GyroTemplate"

        files_elem = ET.SubElement(root, "files")
        for source_file in source_files:
            file_elem = ET.SubElement(files_elem, "file")
            file_elem.text = f"$PROJ_DIR$\\{source_file.replace('/', '\\')}"

        xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(
            indent="   ", encoding="utf-8"
        )
        with open(template_file, "wb") as f:
            f.write(xml_str)
        print(f"[OK] Создан файл описания шаблона: {template_file}")

    def copy_project_files(self) -> None:
        """Копирование файлов проекта в директорию шаблона с сохранением структуры."""
        print("[*] Копирование файлов проекта...")
        files_copied = 0
        for root, dirs, files in os.walk(self.source_dir):
            dirs[:] = [d for d in dirs if d not in self.EXCLUDE_DIRS]
            for file in files:
                if Path(file).suffix.lower() in self.EXCLUDE_EXTENSIONS:
                    continue
                if Path(file).suffix.lower() not in self.INCLUDE_EXTENSIONS:
                    continue
                src_path = Path(root) / file
                rel_path = src_path.relative_to(self.source_dir)
                dst_path = self.template_dir / rel_path
                dst_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_path, dst_path)
                files_copied += 1
                if files_copied % 50 == 0:
                    print(f"  ... скопировано {files_copied} файлов")
        print(f"[OK] Скопировано файлов: {files_copied}")

    def create_templproj_files(self) -> None:
        """Создание templproj.ewp и templproj.ewd на основе существующих файлов."""
        self.template_dir.mkdir(parents=True, exist_ok=True)
        print("[*] Создание templproj файлов...")

        ewp_data = self.parse_ewp_file()
        if ewp_data and ewp_data["tree"]:
            root = ewp_data["root"]
            for file_elem in root.findall("file"):
                name_elem = file_elem.find("name")
                if name_elem is not None and name_elem.text:
                    if "$PROJ_DIR$" not in name_elem.text:
                        file_name = Path(name_elem.text).name
                        name_elem.text = f"$PROJ_DIR$\\{file_name}"
            xml_str = minidom.parseString(ET.tostring(root)).toprettyxml(
                indent="    ", encoding="utf-8"
            )
            with open(self.template_dir / "templproj.ewp", "wb") as f:
                f.write(xml_str)
            print("[OK] Создан templproj.ewp на основе существующего проекта")
        else:
            self._create_default_templproj()

        ewd_tree = self.parse_ewd_file()
        if ewd_tree:
            xml_str = minidom.parseString(ET.tostring(ewd_tree.getroot())).toprettyxml(
                indent="    ", encoding="utf-8"
            )
            with open(self.template_dir / "templproj.ewd", "wb") as f:
                f.write(xml_str)
            print("[OK] Создан templproj.ewd на основе существующего проекта")

        for icf_file in self.source_dir.glob("**/*.icf"):
            rel_path = icf_file.relative_to(self.source_dir)
            dst_path = self.template_dir / rel_path
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(icf_file, dst_path)
            print(f"[OK] Скопирован linker script: {rel_path}")

        for eww_file in self.source_dir.glob("*.eww"):
            shutil.copy2(eww_file, self.template_dir / "templproj.eww")
            print("[OK] Создан templproj.eww")

    def _create_default_templproj(self) -> None:
        """Создание шаблонного templproj.ewp при отсутствии исходного .ewp."""
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
                    <state>STM32L412RB\tST STM32L412RB</state>
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
                    <name>OGChipSelectEditMenu</name>
                    <state>STM32L412RB\tST STM32L412RB</state>
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

        with open(self.template_dir / "templproj.ewp", "w", encoding="utf-8") as f:
            f.write(template_content)
        print("[OK] Создан новый templproj.ewp на основе шаблона")

    def copy_shared_files(self) -> None:
        """Копирование или создание shared.icf."""
        self.template_dir.mkdir(parents=True, exist_ok=True)
        print("[*] Копирование shared файлов...")
        shared_icf_src = self.source_dir / "shared.icf"
        if shared_icf_src.exists():
            shutil.copy2(shared_icf_src, self.template_dir / "shared.icf")
            print("[OK] Скопирован shared.icf")
        else:
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

            with open(self.template_dir / "shared.icf", "w", encoding="utf-8") as f:
                f.write(shared_content)
            print("[OK] Создан shared.icf из шаблона")

    def create_readme(self) -> None:
        """Создание README с инструкциями по установке шаблона."""
        readme_content = f"""# IAR Project Template - GyroProject

Создан: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Инструкция по установке шаблона

1. **Найдите директорию шаблонов IAR:**
   - Для IAR 9.60: `C:\\Program Files\\IAR Systems\\Embedded Workbench 9.6\\arm\\config\\template\\project\\`
   - Запустите файловый менеджер с правами администратора!

2. **Скопируйте папку шаблона:**
   - Скопируйте папку `GyroProject` из: {self.output_dir}
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
        with open(readme_file, "w", encoding="utf-8") as f:
            f.write(readme_content)
        print(f"[OK] Создан README файл: {readme_file}")

    def create_directory_structure(self) -> None:
        """Создание структуры директорий шаблона."""
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
        print("[OK] Создана структура директорий")

    def generate(self) -> None:
        """Основной метод генерации шаблона."""
        print("=" * 70)
        print("Генерация IAR Project Template для GyroProject")
        print("=" * 70)
        print(f"Исходная директория: {self.source_dir}")
        print(f"Выходная директория: {self.output_dir}")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_group_dir.mkdir(parents=True, exist_ok=True)
        self.template_dir.mkdir(parents=True, exist_ok=True)

        self.create_directory_structure()

        source_files = self.get_all_source_files()
        print(f"[OK] Найдено исходных файлов: {len(source_files)}")

        self.create_template_group_file()
        self.create_template_file(source_files)
        self.copy_project_files()
        self.create_templproj_files()
        self.copy_shared_files()
        self.create_readme()

        print("=" * 70)
        print("[OK] Генерация шаблона завершена успешно!")
        print(f"Шаблон создан в: {self.template_group_dir}")
        print("=" * 70)


def main() -> int:
    """CLI-вход для генерации шаблона."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Генератор IAR Project Template из существующего проекта"
    )
    parser.add_argument("source_dir", help="Путь к исходной директории проекта")
    parser.add_argument(
        "-o",
        "--output",
        help="Выходная директория для шаблона (по умолчанию: ./iar_template_output)",
    )
    args = parser.parse_args()

    try:
        generator = IARProjectTemplateGenerator(args.source_dir, args.output)
        generator.generate()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback

        traceback.print_exc()
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
