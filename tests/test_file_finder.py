"""Тесты FileFinder: поиск исходных файлов, линкер-скриптов и include-путей."""

from config import IARConfig
from file_finder import FileFinder


def win(p):
    """Приведение к виду с прямыми слешами для платформо-независимых сравнений."""
    return p.replace("\\", "/")


def make_finder(project_path):
    return FileFinder(project_path, IARConfig())


class TestFindSourceFiles:
    def test_finds_sources_and_headers(self, sample_project):
        finder = make_finder(sample_project)
        sources, headers = finder.find_source_files()
        sources = [win(s) for s in sources]
        headers = [win(h) for h in headers]
        assert "main.c" in sources
        assert "src/uart.c" in sources
        assert "startup/startup.s" in sources
        assert "app.h" in headers
        assert "src/uart.h" in headers

    def test_excludes_configured_dirs(self, sample_project):
        finder = make_finder(sample_project)
        sources, headers = finder.find_source_files()
        assert not any("iar" in s for s in sources)
        assert not any("iar" in h for h in headers)

    def test_sorted_output(self, sample_project):
        finder = make_finder(sample_project)
        sources, headers = finder.find_source_files()
        assert sources == sorted(sources)
        assert headers == sorted(headers)

    def test_empty_project_returns_empty(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        finder = make_finder(empty)
        sources, headers = finder.find_source_files()
        assert sources == []
        assert headers == []


class TestFindLinkerScripts:
    def test_finds_icf_in_mcu_platforms(self, sample_project):
        finder = make_finder(sample_project)
        scripts = [win(s) for s in finder.find_linker_scripts()]
        assert "project/mcu_platforms/STM32L4/stm32l412rb_flash.icf" in scripts

    def test_finds_icf_in_project_root(self, tmp_path):
        project = tmp_path / "p"
        project.mkdir()
        (project / "board.icf").write_text("/* */", encoding="utf-8")
        finder = make_finder(project)
        assert "board.icf" in finder.find_linker_scripts()


class TestFindFreeRtosConfig:
    def test_finds_config_in_project(self, sample_project):
        finder = make_finder(sample_project)
        result = win(finder.find_freertos_config())
        assert result == "project/mcu_platforms/STM32L4/inc"

    def test_returns_none_when_missing(self, tmp_path):
        project = tmp_path / "p"
        project.mkdir()
        finder = make_finder(project)
        assert finder.find_freertos_config() is None


class TestFindDirectoriesWithFiles:
    def test_finds_dirs_with_headers_recursively(self, sample_project):
        finder = make_finder(sample_project)
        dirs = [
            win(d)
            for d in finder.find_directories_with_files(
                sample_project, {".h"}, recursive=True
            )
        ]
        assert "src" in dirs
        assert "project/mcu_platforms/STM32L4/inc" in dirs
        assert "startup" not in dirs

    def test_non_recursive_checks_only_direct_subdirs(self, tmp_path):
        project = tmp_path / "p"
        project.mkdir()
        (project / "top.h").write_text("", encoding="utf-8")
        sub = project / "deep" / "nested"
        sub.mkdir(parents=True)
        (sub / "inner.h").write_text("", encoding="utf-8")
        finder = make_finder(project)
        dirs = finder.find_directories_with_files(project, {".h"}, recursive=False)
        assert "deep/nested" not in dirs


class TestIncludePaths:
    def test_include_paths_contains_root_and_src(self, sample_project):
        finder = make_finder(sample_project)
        paths = finder.get_include_paths()
        assert "$PROJ_DIR$\\..\\" in paths
        assert any("src" in p for p in paths)

    def test_include_paths_contains_freertos_dir(self, sample_project):
        finder = make_finder(sample_project)
        paths = finder.get_include_paths()
        assert any("mcu_platforms/STM32L4/inc" in win(p) for p in paths)

    def test_include_paths_sorted_and_unique(self, sample_project):
        finder = make_finder(sample_project)
        paths = finder.get_include_paths()
        assert paths == sorted(paths)
        assert len(paths) == len(set(paths))

    def test_asm_include_paths(self, sample_project):
        finder = make_finder(sample_project)
        paths = finder.get_asm_include_paths()
        assert r"$PROJ_DIR$" in paths
        assert any("startup" in p for p in paths)
