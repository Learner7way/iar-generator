"""Тесты IARProjectGenerator: обновление XML-структур .ewp файла."""

import xml.etree.ElementTree as ET

from iar_generator import IARProjectGenerator


import pytest


@pytest.fixture
def generator(tmp_path, iar_generator_dir):
    """Генератор на реальных эталонах, вывод в отдельную директорию."""
    project = tmp_path / "proj"
    project.mkdir()
    (project / "main.c").write_text("int main(void) {}\n", encoding="utf-8")
    return IARProjectGenerator(
        project_path=str(project),
        project_name="Demo",
        script_dir=str(iar_generator_dir),
        output_dir=str(tmp_path / "out"),
    )


def _ewp_root():
    """Минимальный .ewp-подобный XML для проверки update-методов."""
    return ET.fromstring(
        "<project>"
        "<configuration>"
        "<name>Debug</name>"
        "<settings><name>General</name><data>"
        "<option><name>ExePath</name><state>Project\\Debug\\Exe</state></option>"
        "</data></settings>"
        "<settings><name>ICCARM</name><data>"
        "<option><name>CCIncludePath2</name><state>$PROJ_DIR$\\..\\old\\inc</state></option>"
        "</data></settings>"
        "<settings><name>AARM</name><data>"
        "<option><name>AUserIncludes</name><state>$PROJ_DIR$\\..\\old\\asm</state></option>"
        "</data></settings>"
        "<settings><name>ILINK</name><data>"
        "<option><name>IlinkIcfFile</name><state>old.icf</state></option>"
        "<option><name>IlinkOutputFile</name><state>Project\\Debug\\Exe\\Demo.out</state></option>"
        "</data></settings>"
        "</configuration>"
        "</project>"
    )


class TestBuildFolderTree:
    def test_builds_nested_tree(self, generator):
        files = ["src/uart.c", "project/drivers/uart.h", "main.c"]
        tree = generator._build_folder_tree(files, set())
        assert any("main.c" in f for f in tree["__files__"])
        assert "src" in tree
        assert any("uart.c" in f for f in tree["src"]["__files__"])
        # префикс project/ отбрасывается
        assert "project" not in tree
        assert any("uart.h" in f for f in tree["drivers"]["__files__"])

    def test_skips_existing_paths(self, generator):
        files = ["src/uart.c"]
        existing = {r"$PROJ_DIR$\..\src\uart.c"}
        tree = generator._build_folder_tree(files, existing)
        assert tree == {}


class TestUpdateXmlWithFileList:
    def test_adds_files_to_existing_project_group(self, generator):
        root = ET.fromstring("<project><group><name>project</name></group></project>")
        generator.update_xml_with_file_list(root, ["src/uart.c"])
        names = [n.text for n in root.findall(".//file/name")]
        assert any("uart.c" in n for n in names)

    def test_creates_project_group_when_missing(self, generator):
        root = ET.fromstring("<project></project>")
        generator.update_xml_with_file_list(root, ["main.c"])
        groups = [g.find("name").text for g in root.findall("group")]
        assert "project" in groups


class TestUpdateIncludePaths:
    def test_replaces_cc_include_path2_states(self, generator):
        root = _ewp_root()
        generator.update_include_paths(root, [r"$PROJ_DIR$\..\inc"])
        states = [
            s.text
            for s in root.findall(
                ".//settings[name='ICCARM']//option[name='CCIncludePath2']/state"
            )
        ]
        assert states == [r"$PROJ_DIR$\..\inc"]

    def test_creates_cc_include_path2_when_missing(self, generator):
        root = ET.fromstring(
            "<project><configuration><settings><name>ICCARM</name><data>"
            "<option><name>Other</name><state>x</state></option>"
            "</data></settings></configuration></project>"
        )
        generator.update_include_paths(root, ["a", "b"])
        option = root.find(".//settings[name='ICCARM']//option[name='CCIncludePath2']")
        assert option is not None
        assert [s.text for s in option.findall("state")] == ["a", "b"]


class TestUpdateAsmIncludePaths:
    def test_replaces_a_user_includes_states(self, generator):
        root = _ewp_root()
        generator.update_asm_include_paths(root, [r"$PROJ_DIR$\..\asm"])
        states = [
            s.text
            for s in root.findall(
                ".//settings[name='AARM']//option[name='AUserIncludes']/state"
            )
        ]
        assert states == [r"$PROJ_DIR$\..\asm"]


class TestUpdateLinkerScripts:
    def test_sets_first_linker_script_path(self, generator):
        root = _ewp_root()
        generator.update_linker_scripts(root, ["project/linker/stm32.icf"])
        state = root.find(
            ".//settings[name='ILINK']//option[name='IlinkIcfFile']/state"
        )
        assert state.text == r"$PROJ_DIR$\..\project\linker\stm32.icf"

    def test_no_linker_scripts_returns_unchanged(self, generator):
        root = _ewp_root()
        result = generator.update_linker_scripts(root, [])
        assert result is root


class TestProjectNameUpdate:
    def test_replaces_project_in_general_paths(self, generator):
        root = _ewp_root()
        generator.update_project_name_in_ewp(root)
        state = root.find(".//settings[name='General']//option[name='ExePath']/state")
        assert state.text == r"Demo\Debug\Exe"

    def test_replaces_project_in_ilink_output(self, generator):
        root = _ewp_root()
        generator.update_project_name_in_ewp(root)
        state = root.find(
            ".//settings[name='ILINK']//option[name='IlinkOutputFile']/state"
        )
        assert state.text == r"Demo\Debug\Exe\Demo.out"


class TestGeneration:
    def test_generate_all_creates_all_files(self, generator):
        generator.generate_all()
        assert generator.ewp_file.exists()
        assert generator.ewd_file.exists()
        assert generator.eww_file.exists()
        assert generator.ewt_file.exists()
        assert (generator.output_dir / "README_IAR_FILES.txt").exists()

    def test_ewp_is_valid_xml_with_configuration(self, generator):
        generator.generate_all()
        content = generator.ewp_file.read_text(encoding="UTF-8")
        root = ET.fromstring(content)
        assert root.tag == "project"
        assert root.find(".//configuration") is not None

    def test_ewp_contains_added_source_file(self, generator):
        generator.generate_all()
        content = generator.ewp_file.read_text(encoding="UTF-8")
        assert "main.c" in content

    def test_eww_contains_workspace_reference(self, generator):
        generator.generate_all()
        content = generator.eww_file.read_text(encoding="UTF-8")
        assert "$WS_DIR$" in content
        assert "project.ewp" in content

    def test_generate_all_without_files_does_not_create_ewp(
        self, tmp_path, iar_generator_dir
    ):
        project = tmp_path / "empty_proj"
        project.mkdir()
        gen = IARProjectGenerator(
            project_path=str(project),
            project_name="Empty",
            script_dir=str(iar_generator_dir),
            output_dir=str(tmp_path / "out_empty"),
        )
        gen.generate_all()
        assert not gen.ewp_file.exists()
