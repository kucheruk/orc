# ORC-REF-001

Централизовать parser-контракт task/backlog в одном модуле и убрать дубли между runtime и hook runtime.

---

## Комментарий исполнителя

- Что сделали: вынесли единый контракт парсинга backlog-задач в `orc_core/task_contract.py` (regex + parse/render helpers), перевели на него runtime (`orc_core/backlog.py`) и hook runtime (генерацию `orc_hook_lib.py` в `orc_core/hooks.py`), убрали дубли regex/парсеров.
- Что проверили (verifier): выполнены `python3 -m compileall orc_core` и `python3 -m unittest discover -s tests -p "test_*.py"` — успешно; добавлены тесты `tests/test_task_contract.py` на ID extraction, parse и mark rendering.
- Этап shrink: безопасно удалён устаревший дублирующий код парсинга из hook runtime (локальные `TASK_RE`, `TASK_ID_RE`, `extract_task_id`), функциональность сохранена через единый контракт.
- Trade-offs: hook runtime теперь зависит от импорта `orc_core.task_contract` через `sys.path` с `ORC_ROOT`; это повышает связность, но устраняет риск расхождения контрактов.
- Вне scope: не меняли поведение commit phase, Telegram policy и остальной pipeline; также не рефакторили другие потенциальные дубли вне parser-контракта.
- Риски и фокус для QA: проверить end-to-end сценарий с реальным пересозданием `.cursor/hooks/orc_hook_lib.py` (`--reinit-hooks`), включая случаи `status=completed`, `status!=completed` и markdown-строки с `**ID:**`.
- Важно следующему разработчику: при изменении формата backlog править только `orc_core/task_contract.py`; runtime и hooks должны оставаться consumers этого модуля.
- Ссылка на backlog: пункт `ORC-REF-001` в [`.orc/tmp/BACKLOG.temp.20260226-235933.md`](../.orc/tmp/BACKLOG.temp.20260226-235933.md).
