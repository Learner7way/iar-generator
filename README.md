# py_generator — AI-конвейер генерации IAR-проектов

Инструмент для автоматизации работы с embedded-проектами (IAR Embedded Workbench):

1. **Собирает** информацию о проекте (`.ewp`, include-пути, дефайны, линкер-скрипты, исходники).
2. **Формирует** «вопрос к AI» (`py_out.md`) по стандарту `resources/promt.md` (C) / `resources/promt_py.md` (Python).
3. **Отправляет** вопрос в LLM через подключаемые бэкенды (мок / OpenAI-compatible API) — шаг `ai/ask.py`.
4. **Применяет** ответ (create/update/delete) к файлам проекта с Git-версионированием (`py_in_updater.py`).
5. **Генерирует** файлы IAR (`.ewp/.ewd/.eww/.ewt`) из эталонов (`iar_generator/`).

Развитие ведётся по плану `docs/ROADMAP.md` (TDD, по одному этапу за раз).

---

## Установка

```powershell
# Python 3.14+; создать виртуальное окружение (опционально)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Зависимости (runtime + dev: pytest, ruff, black, isort, mypy)
pip install -r requirements.txt
```

## Запуск полного конвейера

```powershell
python py_master.py C:\Projects\example [--pause]
```

Шаги конвейера (нумерованные):
- **Шаг 0** — очистка `py_out.md`/`py_in.txt` (с бэкапами `*.backup_<timestamp>`).
- **Шаг 1** — `add_prompt_to_py_out.py`: вставка стандарта `resources/promt.md` в `py_out.md`.
- **Шаг 2** — ввод текста задачи → `task.txt` → `py_out.md`.
- **Шаг 3** — `pyIAR_xmlValue.py`: сбор include/defines/linker из `.ewp`.
- **Шаг 4** — `pyAIData.py`: генерация Markdown с содержимым исходников.
- **Шаг 5** — `ai/ask.py`: отправка `py_out.md` в LLM → ответ в `py_in.txt`.
- **Шаг 6** — `py_in_formatter.py`: приведение ответа к строгому формату (create/update/delete).
- **Шаг 7** — `py_in_updater.py`: применение изменений к проекту (Git-коммиты до/после, `.version.json`).
- **Шаг 8** — `iar_generator/master.py generate`: перегенерация файлов IAR из эталонов.

## Генерация IAR-файлов (без AI-этапов)

```powershell
python iar_generator\master.py generate C:\Projects\example my_project
python iar_generator\master.py template C:\Projects\example -o C:\tmp\template  # устанавливаемый шаблон GyroProject
python iar_generator\master.py info C:\Projects\example
python iar_generator\master.py check C:\Projects\example
python iar_generator\master.py clean C:\Projects\example
```

## Запрос к LLM отдельно

```powershell
# Mock-бэкенд (по умолчанию, для тестов/демо)
python -m ai.ask

# OpenAI-compatible API (llama.cpp / Ollama / DeepSeek) через переменные окружения
$env:AI_BACKEND="openai-compatible"
$env:AI_BASE_URL="http://127.0.0.1:8080/v1"
$env:AI_MODEL="local-model"
$env:AI_API_KEY="not-needed"   # или ключ провайдера
python -m ai.ask
```

Либо отредактируйте `ai_config.ini` (секция `[backend]`). См. `ai/ask.py`.

## Конфигурация

- **`pipeline.ini`** — пути файлов конвейера (секция `[paths]`, поддержка `%ENV_VAR%`). Читается `core/config.py`.
- **`ai_config.ini`** — настройки AI-бэкенда.
- **`project_config.ini`** — входное ТЗ целевого embedded-проекта «MaX» (для AI/справки, кодом не читается).

## Тесты и качество

```powershell
python -m pytest                      # запуск тестов (pytest.ini: тесты + coverage)
python -m pytest --cov-report=html    # HTML-отчёт покрытия
ruff check .                          # линтер
black --check .                       # формат
mypy .                                # статический анализ
```

## Структура

```
py_generator/
├── py_master.py           # оркестратор конвейера
├── ai/                    # AI-бэкенды (LLMBackend: mock / OpenAI-compatible)
├── core/config.py         # конфигурация путей (pipeline.ini)
├── iar_generator/         # генератор IAR (эталоны в ewarm/, команды generate/template/info/check/clean)
├── utils/file_reader.py   # чтение файлов с автоопределением кодировки и детекцией бинарных
├── resources/             # стандарты кода для AI (promt.md / promt_py.md)
├── docs/ROADMAP.md        # план развития (TDD)
├── tests/                 # автотесты (pytest)
├── pipeline.ini           # пути конвейера
├── ai_config.ini          # настройки AI-бэкенда
└── project_config.ini     # ТЗ embedded-проекта
```

> Примечание: файлы-артефакты конвейера (`py_out.md`, `py_in.txt`, `buffer_py_in.txt`, `task.txt`, `history/`) исключены из git (см. `.gitignore`).
