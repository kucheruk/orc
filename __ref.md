# Отчёт по зонам рефакторинга (`ORC-SMOKE-001`)

## Контекст и источники правды

- Использованы: `AGENTS.md`, `techspec.md`, код (`orc.py`, `orc_core/*`, `tests/*`).
- Цель: выявить фактические зоны рефакторинга, приоритизировать риски и предложить безопасный порядок работ.
- Подход: анализ кода + обязательный verifier + shrink-проверка.

## Фактический срез проекта

- Основные модули:
  - `orc_core/supervisor.py` — 1053 строки.
  - `orc_core/hooks.py` — 576 строк.
  - `orc_core/stream_monitor.py` — 489 строк.
  - `orc_core/supervisor_lifecycle.py` — 224 строки.
  - `orc_core/supervisor_fallback.py` — 228 строк.
- Тесты в репозитории есть: `tests/test_task_contract.py`, `tests/test_stream_monitor.py` (всего 5 unit-тестов).

## Приоритетные зоны рефакторинга

### P0 - Дублирование логики между `supervisor.py` и новыми модулями lifecycle/fallback

- Где: `orc_core/supervisor.py`, `orc_core/supervisor_lifecycle.py`, `orc_core/supervisor_fallback.py`.
- Симптом:
  - Вынесенные функции уже существуют в новых модулях, но старые версии остаются в `supervisor.py`.
  - Дублируются `wait_for_completion`, `wait_for_process_exit`, парсинг `agent ls`, fallback stop-hook, cleanup task-файла.
- Риск:
  - изменение в одной версии логики легко забыть перенести во вторую;
  - высокий риск расхождения поведения на restart/fallback-путях.
- Рекомендация:
  - перевести `supervisor.py` на импорт и использование функций из `supervisor_lifecycle.py` и `supervisor_fallback.py`;
  - удалить дубли из `supervisor.py` после зелёных тестов.

### P0 - Контракт запуска неочевиден: `python3` падает, `uv run` работает

- Где: runtime/документация запуска.
- Симптом:
  - `python3 orc.py --help` -> `ModuleNotFoundError: No module named 'rich'`;
  - `uv run python orc.py --help` -> успешно.
- Риск:
  - ложные инциденты "проект не запускается";
  - нестабильная эксплуатация при запуске вне `uv`.
- Рекомендация:
  - зафиксировать в документации обязательный запуск через `uv run`;
  - дополнительно рассмотреть bootstrap-проверку зависимостей с явным текстом ошибки.

### P1 - Встроенные hook-скрипты строками в `hooks.py`

- Где: `orc_core/hooks.py` (`ensure_repo_hooks`).
- Симптом:
  - `orc_before_submit.py`, `orc_stop.py`, `orc_hook_lib.py` генерируются через длинные Python-строки.
- Риск:
  - сложно тестировать и ревьюить hook-код отдельно;
  - высокая цена сопровождения и риск регрессий при мелких правках.
- Рекомендация:
  - вынести шаблоны hooks в отдельные файлы/модули;
  - добавить smoke-тест генерации hook-файлов.

### P1 - Дублирование Telegram-логики между runtime и hook runtime

- Где: `orc_core/notify.py` и embedded `send_telegram_message` в `orc_hook_lib` (внутри `hooks.py`).
- Симптом:
  - дублируются credential-resolution, truncate и отправка сообщений.
- Риск:
  - diverging behavior при изменении Telegram API/валидации.
- Рекомендация:
  - вынести общую реализацию в переиспользуемый helper с одинаковым контрактом ошибок и логирования.

### P1 - Несоответствие follow-up контракта stop-hook и `techspec.md`

- Где: embedded stop hook в `orc_core/hooks.py`.
- Симптом:
  - сейчас emit: `commit EVERYTHING+push with task ID and task description as commit message`;
  - в `techspec.md` зафиксировано: `commit+push with task ID and task description as commit message`.
- Риск:
  - автоматизации, завязанные на контракт, могут разъехаться.
- Рекомендация:
  - синхронизировать код и spec одним решением (либо код к spec, либо spec к фактическому контракту).

### P2 - Безопасная очистка shim-слоёв

- Где: `orc_core/monitor.py` (compatibility shim).
- Симптом:
  - внутреннего использования почти нет, но это публичный import-path.
- Риск:
  - удаление без проверки downstream может сломать внешние интеграции.
- Рекомендация:
  - удалять только в отдельной задаче после проверки внешних потребителей.

## Verifier

### Что проверено и прошло

- Выполнена именно карточка `ORC-SMOKE-001`.
- Проект компилируется: `python3 -m compileall orc.py orc_core tests`.
- CLI smoke прошёл: `uv run python orc.py --help`.
- Прогон всех текущих тестов прошёл: `uv run python -m unittest discover -s tests -p "test_*.py"` -> `OK (5 tests)`.

### Что проверено и выявило проблему

- `python3 orc.py --help` падает с `ModuleNotFoundError: rich` при запуске вне `uv`.
- `python3 -m unittest discover ...` аналогично падает на `test_stream_monitor.py` по той же причине.

### Вывод verifier

- Кодовая база функциональна в проектном режиме запуска (`uv run`).
- Требование "абсолютно все тесты проходят" выполнено в ожидаемом окружении проекта.
- Есть эксплуатационный риск запуска "не тем интерпретатором" — вынесен в follow-up.

## Shrink

- Проверен мусор локального прогона в `tests/__pycache__`: на момент проверки `*.pyc` отсутствуют, дополнительная очистка не потребовалась.
- Потенциальные удаления (например, `orc_core/monitor.py`) не выполнялись без доказательства безопасности для внешних импортов.

## Рекомендованный порядок рефакторинга

1. Убрать дублирование `supervisor.py` vs `supervisor_lifecycle.py`/`supervisor_fallback.py`.
2. Зафиксировать контракт запуска через `uv run` и добавить guardrail-проверку зависимостей.
3. Вынести hook scripts из строк в шаблоны/файлы.
4. Унифицировать Telegram helper между runtime и hook runtime.
5. Синхронизировать follow-up контракт stop-hook с `techspec.md`.

## Follow-up задачи (добавлены в backlog)

- `ORC-REF-007` — завершить миграцию `supervisor.py` на `supervisor_lifecycle.py` и `supervisor_fallback.py`, удалить дубли.
- `ORC-REF-008` — вынести hook scripts из embedded-строк в версионируемые шаблоны/модули.
- `ORC-REF-009` — унифицировать Telegram notifier между runtime и hook runtime.
- `ORC-REF-010` — синхронизировать follow-up контракт stop-hook и `techspec.md`.
- `ORC-REF-011` — документировать обязательный запуск через `uv run` и добавить проверку зависимостей.
