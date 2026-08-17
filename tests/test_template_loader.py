"""Тесты TemplateLoader: загрузка эталонных файлов IAR."""

import pytest

from config import IARConfig
from template_loader import TemplateLoader


@pytest.fixture
def loader(iar_generator_dir):
    return TemplateLoader(iar_generator_dir / "ewarm", IARConfig())


class TestTemplateLoader:
    def test_missing_templates_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            TemplateLoader(tmp_path / "no_ewarm", IARConfig())

    def test_load_ewp_template_returns_tree_and_root(self, loader):
        tree, root = loader.load_ewp_template()
        assert tree is not None
        assert root.tag is not None

    def test_load_eww_template_returns_content(self, loader):
        content = loader.load_eww_template()
        assert "project.ewp" in content

    def test_extract_configurations_from_ewp(self, loader):
        configs = loader.extract_configurations()
        assert isinstance(configs, list)
        assert len(configs) > 0

    def test_get_template_info(self, loader):
        info = loader.get_template_info()
        assert set(info.keys()) == {"ewp", "ewd", "eww", "ewt"}
        for entry in info.values():
            assert "path" in entry
            assert "size" in entry

    def test_extract_configurations_falls_back_on_missing_ewp(
        self, tmp_path, iar_generator_dir
    ):
        config = IARConfig()
        loader = TemplateLoader(iar_generator_dir / "ewarm", config)
        # Подменяем путь к эталону, чтобы спровоцировать ошибку чтения
        loader.template_files["ewp"] = tmp_path / "missing.ewp"
        assert loader.extract_configurations() == config.default_configs
