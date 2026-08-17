"""Тесты AI-интеграции: бэкенды, фабрика, конфиг и ask."""

import pytest

from ai import ask
from ai.backend_base import LLMBackend
from ai.backends import MockBackend, OpenAICompatibleBackend, create_backend
from ai.ask import load_backend_config


class TestMockBackend:
    def test_returns_configured_response(self):
        backend = MockBackend(response="фиксированный ответ")
        assert backend.generate("вопрос") == "фиксированный ответ"

    def test_default_response_has_pipeline_format(self):
        backend = MockBackend()
        response = backend.generate("вопрос")
        assert "**Файл:**" in response
        assert "```c" in response

    def test_is_llm_backend(self):
        assert isinstance(MockBackend(), LLMBackend)


class TestOpenAICompatibleBackend:
    def test_generate_returns_content(self, monkeypatch):
        backend = OpenAICompatibleBackend(
            model="test-model", api_key="secret", base_url="http://x/v1", timeout=30
        )

        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"choices": [{"message": {"content": "  ответ модели  "}}]}

        captured = {}

        def fake_post(url, headers=None, json=None, timeout=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            captured["timeout"] = timeout
            return FakeResponse()

        monkeypatch.setattr("ai.backends.requests.post", fake_post)

        result = backend.generate("вопрос", system="система")
        assert result == "ответ модели"
        assert captured["url"] == "http://x/v1/chat/completions"
        assert captured["headers"]["Authorization"] == "Bearer secret"
        assert captured["json"]["model"] == "test-model"
        assert captured["json"]["messages"] == [
            {"role": "system", "content": "система"},
            {"role": "user", "content": "вопрос"},
        ]

    def test_raises_on_http_error(self, monkeypatch):
        backend = OpenAICompatibleBackend(base_url="http://x/v1")

        class FakeErrorResponse:
            def raise_for_status(self):
                raise RuntimeError("401")

        def fake_post(url, headers=None, json=None, timeout=None):
            return FakeErrorResponse()

        monkeypatch.setattr("ai.backends.requests.post", fake_post)
        with pytest.raises(RuntimeError, match="401"):
            backend.generate("вопрос")

    def test_default_env_fallbacks(self, monkeypatch):
        monkeypatch.delenv("AI_API_KEY", raising=False)
        monkeypatch.delenv("AI_BASE_URL", raising=False)
        backend = OpenAICompatibleBackend(model="m")
        assert backend.api_key == "not-needed"
        assert backend.base_url == "http://127.0.0.1:8080/v1"


class TestCreateBackend:
    def test_mock_type(self):
        backend = create_backend({"type": "mock"})
        assert isinstance(backend, MockBackend)

    def test_openai_compatible_type(self):
        backend = create_backend(
            {"type": "openai-compatible", "model": "m", "timeout": 5}
        )
        assert isinstance(backend, OpenAICompatibleBackend)
        assert backend.model == "m"
        assert backend.timeout == 5

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            create_backend({"type": "bogus"})


class TestLoadBackendConfig:
    def test_defaults_without_file(self, tmp_path, monkeypatch):
        monkeypatch.delenv("AI_BACKEND", raising=False)
        monkeypatch.delenv("AI_MODEL", raising=False)
        cfg = load_backend_config(tmp_path / "missing.ini")
        assert cfg["type"] == "mock"
        assert cfg["timeout"] == 120
        assert isinstance(cfg["timeout"], int)

    def test_reads_ini(self, tmp_path):
        ini = tmp_path / "ai_config.ini"
        ini.write_text(
            "[backend]\ntype = openai-compatible\nmodel = deepseek\n", encoding="utf-8"
        )
        cfg = load_backend_config(ini)
        assert cfg["type"] == "openai-compatible"
        assert cfg["model"] == "deepseek"

    def test_env_overrides_ini(self, tmp_path, monkeypatch):
        ini = tmp_path / "ai_config.ini"
        ini.write_text("[backend]\ntype = mock\nmodel = from_ini\n", encoding="utf-8")
        monkeypatch.setenv("AI_MODEL", "from_env")
        cfg = load_backend_config(ini)
        assert cfg["model"] == "from_env"


class TestAsk:
    def test_mock_backend_answer(self, tmp_path):
        question = "собери проект"
        answer = ask.ask(question, {"type": "mock"})
        assert "mock_file.c" in answer
