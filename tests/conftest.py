"""Общие фикстуры и настройка путей для тестов py_generator."""

import sys
from pathlib import Path

# iar_generator/ использует плоские импорты (from config import ...),
# поэтому директория пакета добавляется в sys.path.
IAR_GENERATOR_DIR = Path(__file__).resolve().parents[1] / "iar_generator"
sys.path.insert(0, str(IAR_GENERATOR_DIR))

import pytest  # noqa: E402


@pytest.fixture
def iar_generator_dir() -> Path:
    """Путь к директории пакета iar_generator."""
    return IAR_GENERATOR_DIR


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """Минимальная структура embedded-проекта для тестов поиска файлов."""
    project = tmp_path / "sample_project"
    project.mkdir()

    (project / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    (project / "app.h").write_text("#pragma once\n", encoding="utf-8")

    src = project / "src"
    src.mkdir()
    (src / "uart.c").write_text("void uart_init(void) {}\n", encoding="utf-8")
    (src / "uart.h").write_text("#pragma once\n", encoding="utf-8")

    startup = project / "startup"
    startup.mkdir()
    (startup / "startup.s").write_text("AREA RESET, CODE\n", encoding="utf-8")

    config_dir = project / "project" / "mcu_platforms" / "STM32L4" / "inc"
    config_dir.mkdir(parents=True)
    (config_dir / "FreeRTOSConfig.h").write_text("#pragma once\n", encoding="utf-8")

    icf_dir = project / "project" / "mcu_platforms" / "STM32L4"
    (icf_dir / "stm32l412rb_flash.icf").write_text("/* linker */\n", encoding="utf-8")

    # Исключаемые директории не должны попадать в результаты
    excluded = project / "iar"
    excluded.mkdir()
    (excluded / "generated.c").write_text("// excluded\n", encoding="utf-8")

    return project
