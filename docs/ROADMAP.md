# ROADMAP: план развития py_generator

> Дата: 2026-08-17
> Источник идей: анализ `C:\sandbox\projects\py_project` — более поздняя версия
> этого же инструмента. Из неё извлечены архитектурные решения, принципы TDD
> и цели. После переноса всех решений в py_generator проект py_project удаляется.

---

## 1. Цель проекта (что делаем)

`py_generator` — AI-конвейер генерации IAR-проектов и правки кода:
- анализ существующего IAR-проекта (`.ewp`, исходники, include/defines/linker);
- формирование «вопроса к AI» (`py_out.md`), отправка в DeepSeek (Selenium);
- применение ответа к файлам (`py_in_updater.py`, create/update/delete, git, версии);
- генерация файлов IAR (`.ewp/.ewd/.eww/.ewt`) из эталонов (`iar_generator/`).

Конвейер **работает** и остаётся ядром. Развитие — не переписывание, а укрепление:
добавить тесты, навести порядок в структуре, убрать хрупкие места.

---

## 2. Текущее состояние (точка отсчёта)

| Компонент | Файлы | Статус |
|---|---|---|
| Оркестратор | `py_master.py` (575) | ✅ работает, прозрачные шаги 0–9 |
| Сбор данных о проекте | `pyAIData.py`, `pyIAR_xmlValue.py` | ✅ работает |
| AI-интеграция | `pyAIqesion.py`, `start_chrome_debug.py` | ⚠ хрупкая (Selenium, порт 9222, CSS-селекторы DeepSeek) |
| Применение изменений | `py_in_updater.py` (694) | ✅ git-коммиты, `.version.json`, план с подтверждением |
| Генерация IAR | `iar_generator/` (пакет, 1 533) | ✅ модульная, SRP, DI, type hints; команды `generate`/`template`/`info`/`check`/`clean` |
| Формат ответа AI | `py_in_formatter.py` | ✅ create/update/delete |
| Стандарты кода | `promt.md` (C), `promt_py.md` (Python) | ✅ входные ТЗ для AI |
| Тесты / CI | — | ❌ отсутствуют |

---

## 3. Извлечённые решения из py_project (что переносим)

`py_project` = py_generator + «корпоративный каркас». Переносим **идеи**, а не код
(код py_project полурабочий: красные тесты, битые импорты, дубли).

### 3.1. Целевая структура (архитектура)
```
py_generator/
├── py_master.py            # оркестратор (ядро конвейера)
├── core/                   # НОВОЕ: абстракции по стандарту promt_py.md
│   ├── interfaces/         #   Protocol (PEP 544): Scanner, Collector, OutputWriter
│   ├── models/             #   dataclass-сущности с валидацией (__post_init__)
│   └── config.py           #   единый конфиг (Pydantic Settings) вместо разрозненных констант
├── modules/                # НОВОЕ: реализации по ответственности
│   ├── directory_scanner/  #   обход проекта → список файлов (аналог pyAIData.py)
│   └── file_collector/     #   сбор содержимого → Markdown (аналог pyAIData.py)
├── iar_generator/          # ✅ уже есть — оставить как есть
├── utils/                  # НОВОЕ: logger, file_utils, пути
├── tests/                  # НОВОЕ: pytest, покрытие ≥80%
├── resources/promt.md      # ТЗ-стандарты (перенести из корня)
├── requirements.txt        # НОВОЕ: манифест зависимостей
└── README.md               # НОВОЕ: инструкция запуска
```

### 3.2. Принципы (из `promt_py.md` + реализаций py_project)
- **SOLID:** SRP — модуль = одна ответственность; DIP — зависимость от Protocol/ABC, DI через конструктор.
- **Типизация:** type hints везде, `@final`, `Protocol` с `@runtime_checkable`, dataclass `frozen=True`.
- **Валидация конфигурации:** проверки в `__post_init__`, поддержка `%ENV_VAR%` в путях.
- **Устойчивое чтение файлов:** попытки нескольких кодировок (utf-8, cp1251, cp866, latin-1, koi8-r), детектор бинарных файлов (сигнатуры + UTF-8 проба).
- **TDD:** тесты пишутся до кода, красный → зелёный → рефакторинг, покрытие ≥80%.
- **Инструменты качества:** black, isort, mypy (strict), ruff, coverage, pytest.

### 3.3. Цели (приоритет)
1. **Тесты на работающий код** — зафиксировать текущее поведение конвейера (главное).
2. **Единый генератор IAR** — оставить только `iar_generator/`; убрать дубли (`new.py`, `pyGenXMLforIAR.py`).
3. **Стабильная AI-интеграция** — заменить Selenium-сценарий на HTTP API DeepSeek.
4. **Чистая кодировка** — убрать хак `fix_script_encoding()` и эмодзи из вывода.
5. **Порядок в конфигурации** — `project_config.ini` читается кодом (сейчас только ТЗ для AI).
6. **README** — реальная инструкция запуска для пользователя.

### 3.4. Что НЕ переносим (осознанно отбрасываем)
- Пакет `project/` целиком из py_project (незавершён, битые импорты) — берём только идеи структуры.
- Мёртвый код шаблона (Greeter, Message, пустые `entities.py`).
- Тесты-заглушки на несуществующие модули.
- Дубль конфигов (два `Settings`).

---

## 4. Этапы развития (TDD: по одному за раз)

Каждый этап — отдельный шаг, с тестами до кода. Запуск тестов: `pytest`.

### Этап 1 — Каркас тестирования (TDD-фундамент) ✅
- **Red:** написать тесты на `iar_generator/` (ядро — самый чистый модуль):
  генерация путей, нормализация `..\..\`, поиск файлов, форматирование XML.
- **Green:** починить найденные баги минимальными правками.
- **Refactor:** не трогать интерфейсы, только внутренности.
- **Definition of Done:** `pytest` зелёный, coverage ≥60% на `iar_generator/`.
- Создать `requirements.txt` (selenium, pyperclip, requests + dev: pytest, pytest-cov, pytest-mock, black, isort, mypy, ruff).

**Итог (2026-08-17):** 57 тестов, coverage ядра 70% (config/template_loader/xml_formatter ~100%,
iar_generator 98%, path_normalizer 98%, file_finder 82%). ruff/black чистые. Исправлен баг:
`update_linker_scripts` не приводил путь к Windows-формату (добавлен `normalize_for_windows`).
Созданы `requirements.txt`, `pytest.ini`, `tests/` (5 файлов).

### Этап 2 — Детектор кодировок и бинарных файлов ✅
- Вынести из `pyAIData.py` чтение файлов в модуль `utils/file_reader.py` (несколько кодировок, сигнатуры бинарности).
- **Red:** тесты: cp866/cp1251/utf-8, бинарный файл, ограничение размера.
- **Green:** реализация. **Refactor:** подключить в `pyAIData.py` и `py_in_updater.py`.
- **DoD:** `pyAIData.py` использует `utils/file_reader.py`, старые тесты зелёные.

**Итог (2026-08-17):** создан `utils/file_reader.py` (16 тестов): `read_text` (порядок
кодировок utf-8 → cp1251 → cp866 → koi8-r → windows-1251 → latin-1, лимит размера),
`is_binary_file` (расширение + NUL-байты + сигнатуры JPEG/PNG/GIF/ZIP/PDF + UTF-8-проба).
Подключён в `pyAIData.py` (вместо локальных `is_binary_file`/`read_file_content`)
и в `py_in_updater.py` (сравнение существующего файла теперь читает cp866/cp1251,
а не падает на UnicodeDecodeError). Всего тестов: 73.

### Этап 3 — AI-интеграция через API (вместо Selenium) ✅
- **Red:** тесты на клиент DeepSeek API (мок HTTP): отправка `py_out.md`, получение `py_in.txt`.
- **Green:** `ai_client.py` на `requests` (chat/completions), параметры (URL, ключ, модель) — в конфиг.
- **Refactor:** `start_chrome_debug.py` и `pyAIqesion.py` — в архив/ (или удалить после стабилизации API).
- **DoD:** конвейер работает без Chrome; Selenium исключён из зависимостей.

**Итог (2026-08-17):** создан пакет `ai/` по образцу `rlm_agent`:
`backend_base.py` (ABC `LLMBackend`), `backends.py` (`MockBackend` + `OpenAICompatibleBackend`
на `requests` + фабрика `create_backend`), `ask.py` (CLI `python -m ai.ask`: py_out.md → py_in.txt).
Конфиг — `ai_config.ini` (секция `[backend]`, env-переопределение AI_BACKEND/AI_MODEL/AI_BASE_URL/AI_API_KEY).
`py_master.py`: шаги 5–6 (Chrome + pyAIqesion) заменены одним шагом 5 (`ai/ask.py`).
Selenium/pyperclip убраны из `requirements.txt`. Новых тестов: 13 (мок HTTP, фабрика, конфиг, ask).

### Этап 4 — Убрать дубли генераторов IAR ✅
- **Red:** тесты на `iar_generator/` уже есть (Этап 1) — зафиксировать полный набор функций генерации.
- **Green:** перенести недостающие возможности из `new.py`/`pyGenXMLforIAR.py` в `iar_generator/` (по одной функции).
- **Refactor:** удалить `new.py`, `pyGenXMLforIAR.py` после подтверждения тестами.
- **DoD:** в проекте один генератор IAR — `iar_generator/`.

**Итог (2026-08-17):** `pyGenXMLforIAR.py` перенесён в `iar_generator/template_generator.py`
(класс `IARProjectTemplateGenerator`, чистый вывод без эмодзи, устойчивое создание каталогов)
и подключён как команда `template` в `iar_generator/master.py`. `new.py` (2000 строк,
монолитная генерация с нуля под STM32L412RB) удалён: эталоны `ewarm/` покрывают рабочий
кейс конвейера; при необходимости — вернуть из git-истории. Новых тестов: 7. Итого 93.

### Этап 5 — Конфигурация читается кодом
- **Red:** тесты на парсер `project_config.ini` (секции PROJECT/MCU/MODULES, `%ENV_VAR%`).
- **Green:** `core/config.py` (Pydantic Settings) или лёгкий парсер — читает реальный INI.
- **Refactor:** заменить хардкод (`C:\temp\chrome_debug`, порт 9222, пути к chrome) на значения конфига.
- **DoD:** запуск конвейера не требует правки кода — только INI/`.env`.

### Этап 6 — Порядок в корне и документация
- Перенести `promt.md`/`promt_py.md` в `resources/`, собрать `tests/`, добавить `.gitignore`, `README.md`.
- **Red:** нет (документация) — но тесты на запуск: smoke-тест `py_master.py --help`.
- **Green:** README: установка, запуск, описание шагов 0–9, troubleshooting кодировок.
- **Refactor:** удалить `py_in_formatter.tmp.py`, «Команда для запуска.txt» (или обновить под реальные скрипты).
- **DoD:** новый разработчик запускает конвейер по README за 10 минут.

### Этап 7 — Чистый вывод без эмодзи
- Убрать эмодзи из вывода всех скриптов (заменить на `[OK]/[WARN]/[ERROR]` — они уже есть в большинстве).
- **Red:** тест-фикстура: вывод скрипта не содержит не-ASCII эмодзи.
- **Green:** пройти по файлам, заменить эмодзи.
- **Refactor:** удалить `fix_script_encoding()` из `py_master.py`.
- **DoD:** хак с `.tmp.py` больше не нужен.

---

## 5. Критерии удаления py_project

`py_project` удаляется после выполнения **всех** решений:
1. ✅ Этап 1: тесты зелёные, coverage на ядре.
2. ✅ Этап 4: в py_generator один генератор IAR.
3. ✅ Этап 5: конфиг читается кодом.
4. ✅ Этап 7: нет хака кодировок.
5. ✅ Идеи структуры `core/`+`modules/` перенесены в py_generator (п. 3.1).

До этого py_project остаётся как референс: из него берутся недостающие идеи
(по одной, с тестами). После переноса последней — `C:\sandbox\projects\py_project` удаляется.

---

## 6. Правила работы (ритуал)

- Развитие ведётся через AI-инструменты (opencode): план — в этом файле.
- **TDD-цикл:** Red → Green → Refactor, по одному этапу за раз.
- Тесты: `pytest` из корня, coverage: `pytest --cov=. --cov-report=term-missing`.
- Линт: `ruff check .`, формат: `black . && isort .`, типы: `mypy .`.
- Коммиты — по завершении этапа (конвенция — как в `rlm_agent/docs/GIT_CONVENTIONS.md`).
- Стандарт кода — `resources/promt_py.md` (после переноса) / `promt_py.md`.