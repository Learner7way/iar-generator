"""Тесты PathNormalizer: нормализация путей для IAR."""

import xml.etree.ElementTree as ET

from path_normalizer import PathNormalizer


class TestNormalizePath:
    def test_multiple_parent_dirs_collapsed_to_one(self):
        path = r"$PROJ_DIR$\..\..\..\..\Drivers\CMSIS\Include"
        expected = r"$PROJ_DIR$\..\Drivers\CMSIS\Include"
        assert PathNormalizer.normalize_path(path) == expected

    def test_single_parent_dir_unchanged(self):
        path = r"$PROJ_DIR$\..\src"
        assert PathNormalizer.normalize_path(path) == path

    def test_no_proj_dir_unchanged(self):
        path = r"C:\work\project\src"
        assert PathNormalizer.normalize_path(path) == path

    def test_empty_path_unchanged(self):
        assert PathNormalizer.normalize_path("") == ""

    def test_path_without_parent_dirs_unchanged(self):
        path = r"$PROJ_DIR$\src\main.c"
        assert PathNormalizer.normalize_path(path) == path


class TestNormalizeEwwContent:
    def test_multiple_ws_dir_parents_collapsed(self):
        content = r"$WS_DIR$\..\..\..\project.ewp"
        expected = r"$WS_DIR$\project.ewp"
        assert PathNormalizer.normalize_eww_content(content) == expected

    def test_single_parent_unchanged(self):
        content = r"$WS_DIR$\..\project.ewp"
        assert PathNormalizer.normalize_eww_content(content) == content


class TestMakePathRelativeToProject:
    def test_absolute_under_project_uses_proj_dir(self, sample_project):
        path = str(sample_project / "src" / "uart.c")
        result = PathNormalizer.make_path_relative_to_project(path, str(sample_project))
        assert result == r"$PROJ_DIR$\src\uart.c"

    def test_relative_without_proj_dir(self, sample_project):
        path = str(sample_project / "src" / "uart.c")
        result = PathNormalizer.make_path_relative_to_project(
            path, str(sample_project), use_proj_dir=False
        )
        assert result == r"src\uart.c"

    def test_absolute_outside_project_returns_original(self, sample_project, tmp_path):
        outside = str(tmp_path / "elsewhere.c")
        result = PathNormalizer.make_path_relative_to_project(
            outside, str(sample_project)
        )
        assert result == outside


class TestNormalizeForWindows:
    def test_forward_slashes_to_backslashes(self):
        assert PathNormalizer.normalize_for_windows("src/uart.c") == r"src\uart.c"

    def test_none_returns_none(self):
        assert PathNormalizer.normalize_for_windows(None) is None


class TestNormalizeAllPathsInXml:
    def test_normalizes_name_and_state_elements(self):
        root = ET.fromstring(
            "<root>"
            "<name>$PROJ_DIR$\\..\\..\\..\\Drivers</name>"
            "<state>$PROJ_DIR$\\..\\..\\inc</state>"
            "<name>plain</name>"
            "</root>"
        )
        PathNormalizer.normalize_all_paths_in_xml(root)
        names = [n.text for n in root.findall("name")]
        states = [s.text for s in root.findall("state")]
        assert names[0] == r"$PROJ_DIR$\..\Drivers"
        assert names[1] == "plain"
        assert states[0] == r"$PROJ_DIR$\..\inc"
