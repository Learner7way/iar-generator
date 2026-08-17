"""Тесты core.config: чтение конфигурации конвейера из INI."""

from core.config import (
    DEFAULT_CONFIG_PATH,
    PipelineConfig,
    default_config,
    expand_env_vars,
)


class TestExpandEnvVars:
    def test_expands_known_var(self, monkeypatch):
        monkeypatch.setenv("TEST_PIPELINE_VAR", "value_123")
        assert expand_env_vars("%TEST_PIPELINE_VAR%/dir") == "value_123/dir"

    def test_unknown_var_left_as_is(self, monkeypatch):
        monkeypatch.delenv("NO_SUCH_PIPELINE_VAR", raising=False)
        assert expand_env_vars("%NO_SUCH_PIPELINE_VAR%") == "%NO_SUCH_PIPELINE_VAR%"

    def test_value_without_vars_unchanged(self):
        assert expand_env_vars("plain/path") == "plain/path"


class TestDefaultConfig:
    def test_defaults_resolve_from_repo_root(self):
        assert default_config.output_file.name == "py_out.md"
        assert default_config.output_file.is_absolute()
        assert default_config.answer_file.name == "py_in.txt"
        assert default_config.history_dir.name == "history"
        assert default_config.ai_config.name == "ai_config.ini"

    def test_default_config_path_exists(self):
        assert DEFAULT_CONFIG_PATH.exists()


class TestFromIni:
    def test_reads_ini_values(self, tmp_path):
        ini = tmp_path / "pipeline.ini"
        ini.write_text("[paths]\noutput_file = custom_out.md\n", encoding="utf-8")
        cfg = PipelineConfig.from_ini(ini, base_dir=tmp_path)
        assert cfg.output_file == tmp_path / "custom_out.md"

    def test_env_expansion_in_ini(self, tmp_path, monkeypatch):
        ini = tmp_path / "pipeline.ini"
        ini.write_text("[paths]\noutput_file = %TEST_OUT%\n", encoding="utf-8")
        monkeypatch.setenv("TEST_OUT", "env_file.md")
        cfg = PipelineConfig.from_ini(ini, base_dir=tmp_path)
        assert cfg.output_file == tmp_path / "env_file.md"

    def test_absolute_path_in_ini(self, tmp_path):
        ini = tmp_path / "pipeline.ini"
        abs_path = tmp_path / "abs_out.md"
        ini.write_text(f"[paths]\noutput_file = {abs_path}\n", encoding="utf-8")
        cfg = PipelineConfig.from_ini(ini, base_dir=tmp_path)
        assert cfg.output_file == abs_path

    def test_missing_ini_uses_defaults(self, tmp_path):
        cfg = PipelineConfig.from_ini(tmp_path / "missing.ini", base_dir=tmp_path)
        assert cfg.output_file == tmp_path / "py_out.md"
