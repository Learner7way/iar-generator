"""Тесты IARProjectTemplateGenerator: создание устанавливаемого шаблона IAR."""

import xml.etree.ElementTree as ET

import pytest

from template_generator import IARProjectTemplateGenerator


@pytest.fixture
def source_project(tmp_path):
    """Исходный проект с исходниками и .ewp файлом."""
    project = tmp_path / "src_proj"
    project.mkdir()
    (project / "main.c").write_text("int main(void) {}\n", encoding="utf-8")
    (project / "app.h").write_text("#pragma once\n", encoding="utf-8")
    (project / "board.icf").write_text("/* linker */", encoding="utf-8")
    (project / "proj.ewp").write_text(
        "<project><file><name>main.c</name></file></project>", encoding="utf-8"
    )
    # артефакты сборки не должны копироваться
    (project / "app.o").write_bytes(b"\x00\x01")
    (project / "app.hex").write_text(":0000000000", encoding="utf-8")
    # исключаемая директория
    (project / "Debug").mkdir()
    (project / "Debug" / "debug.c").write_text("// debug\n", encoding="utf-8")
    return project


@pytest.fixture
def generator(source_project, tmp_path):
    return IARProjectTemplateGenerator(str(source_project), str(tmp_path / "out"))


class TestInit:
    def test_missing_source_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            IARProjectTemplateGenerator(str(tmp_path / "nope"))


class TestGetAllSourceFiles:
    def test_finds_sources_and_excludes_build_dirs(self, generator):
        files = generator.get_all_source_files()
        assert "main.c" in files
        assert "app.h" in files
        assert "board.icf" in files
        assert not any("Debug" in f for f in files)
        assert files == sorted(files)


class TestCopyProjectFiles:
    def test_copies_sources_but_not_build_artifacts(self, generator):
        generator.copy_project_files()
        template_dir = generator.template_dir
        assert (template_dir / "main.c").exists()
        assert (template_dir / "app.h").exists()
        assert not (template_dir / "app.o").exists()
        assert not (template_dir / "app.hex").exists()
        assert not (template_dir / "Debug").exists()


class TestCreateTemplprojFiles:
    def test_uses_existing_ewp(self, generator):
        generator.create_templproj_files()
        ewp = generator.template_dir / "templproj.ewp"
        assert ewp.exists()
        root = ET.parse(ewp).getroot()
        # пути файлов приведены к $PROJ_DIR$
        names = [n.text for n in root.findall(".//file/name")]
        assert all("$PROJ_DIR$" in (n or "") for n in names)

    def test_default_templproj_without_ewp(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        (empty / "main.c").write_text("int main(void) {}\n", encoding="utf-8")
        gen = IARProjectTemplateGenerator(str(empty), str(tmp_path / "out2"))
        gen.create_templproj_files()
        ewp = gen.template_dir / "templproj.ewp"
        assert ewp.exists()
        root = ET.parse(ewp).getroot()
        names = [c.find("name").text for c in root.findall("configuration")]
        assert "Debug" in names
        assert "Flash_ST-Link" in names


class TestGenerate:
    def test_full_template_generation(self, generator):
        generator.generate()
        out = generator.output_dir
        assert (out / "GyroProject.ENU.projtempl").exists()
        assert (generator.template_dir / "GyroTemplate.projtempl").exists()
        assert (generator.template_dir / "templproj.ewp").exists()
        assert (generator.template_dir / "main.c").exists()
        assert (generator.template_dir / "board.icf").exists()
        assert (generator.template_dir / "shared.icf").exists()
        assert (out / "README.txt").exists()
        assert (generator.template_dir / "project" / "app").is_dir()

    def test_template_file_uses_proj_dir(self, generator):
        generator.generate()
        templ = generator.template_dir / "GyroTemplate.projtempl"
        content = templ.read_text(encoding="utf-8")
        assert "$PROJ_DIR$\\main.c" in content
