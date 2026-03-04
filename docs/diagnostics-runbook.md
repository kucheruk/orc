# ORC Diagnostics Runbook

## Когда использовать

Используйте этот runbook, если ORC:
- зависает без прогресса;
- не закрывает задачу после завершения;
- некорректно проходит commit phase;
- ведет себя нестабильно только в отдельных запусках.

## Как включить debug-логирование

Поддерживаются два способа:

1. Через CLI-флаг:
```bash
uv run python /path/to/orc/orc.py --workspace /path/to/repo --debug
```

2. Через стартовый TUI:
- запустите ORC без явного `--mode`;
- в окне `Дополнительные опции` включите пункт `Включить debug logging в системный temp-каталог`.

При включенном debug ORC пишет отдельный JSONL-файл в системный temp-каталог: `Path(tempfile.gettempdir()) / "orc"`.

## Где лежат логи

- Основной лог ORC: `.orc/orc.log`
- Лог хуков Cursor: `.orc/orc-hook.log`
- Debug-лог запуска ORC: `<system-temp>/orc/orc-debug-<YYYYMMDD-HHMMSS>-<pid>.jsonl`
- Crash-диагностика в stdout: JSON-события с `event="orc_crash_report"` во время фатального падения `orc`

## Как найти актуальный debug-файл

```bash
DEBUG_DIR="$(python -c 'import tempfile; from pathlib import Path; print(Path(tempfile.gettempdir()) / \"orc\")')"
ls -1t "$DEBUG_DIR"/orc-debug-*.jsonl | head -n 5
```

Берите самый верхний файл как самый свежий запуск.

## Как читать debug-лог

Быстрый просмотр конца файла:
```bash
tail -n 50 "$DEBUG_DIR"/orc-debug-<...>.jsonl
```

Фильтрация по этапу/локации:
```bash
rg "task_execution.py|supervisor_lifecycle.py|runner.py" "$DEBUG_DIR"/orc-debug-<...>.jsonl
```

Читаемый JSON через jq:
```bash
jq -c '. | {timestamp, location, message, hypothesisId}' "$DEBUG_DIR"/orc-debug-<...>.jsonl
```

## Crash-диагностика в stdout (для coding agent)

При необработанном падении в основном CLI-пути `orc` ORC печатает в `stdout` одну JSON-строку с `event="orc_crash_report"`.

Минимальные поля отчёта:
- `event`
- `entrypoint`
- `phase`
- `exception_type`
- `error`
- `traceback`
- `workspace`
- `pid`
- `ts`

Быстрый фильтр по событию:
```bash
rg '"event":"orc_crash_report"|"event": "orc_crash_report"' /path/to/orc-output.log
```

Извлечение ключевых полей:
```bash
jq -c 'select(.event=="orc_crash_report") | {ts, exception_type, error, phase, workspace}' /path/to/orc-output.log
```

## Минимальный triage

1. Проверьте, что в debug-файле есть запись `debug_session_started`.
2. Найдите последние записи `completion state` и `wait_for_completion`.
3. Сопоставьте время с `.orc/orc.log` и `.orc/orc-hook.log`.
4. Если агент завершился, но задача не закрыта, проверьте записи про `stop-hook fallback`.

## Диагностика orphan sweep и зависших python3

При срабатывании orphan cleanup смотрите в `.orc/orc.log` событие `orphan sweep: terminate`.
Теперь оно содержит:
- `matches[].matched_by` — причина матча (`token`, `workspace`, `marker`);
- `matches[].cwd` и `matches[].cmdline` (укороченный) для быстрого triage;
- `workspace` и `pids`.

Рекомендуемый порядок:
1. Если `matched_by=token`, это процесс текущего ORC-запуска по `ORC_RUN_TOKEN`.
2. Если `matched_by=workspace/marker`, проверьте что `cwd` действительно в нужном workspace.
3. Если остались подозрительные `python3`, сопоставьте их с `.cursor/hooks/orc_stop.py` / `.cursor/hooks/orc_before_submit.py` в `cmdline`.

## Диагностика commit phase (fallback disabled / enabled)

### Симптом: commit phase завершилась ошибкой при грязном дереве

Проверьте `.orc/orc.log` на одно из сообщений:
- `commit phase failed: tracked changes remain and fallback disabled`
- `commit phase: completed but tracked changes remain (fallback disabled)`

Это ожидаемое fail-fast поведение по умолчанию: ORC не делает авто-коммит и останавливает пайплайн.

### Что делать оператору

1. Посмотреть состояние репозитория:
```bash
git status --porcelain
git diff
```
2. Принять решение вручную (исправить изменения/закоммитить нужное).
3. Если нужен временный автоподбор commit fallback, перезапустить ORC с явным opt-in:
```bash
uv run python /path/to/orc/orc.py --workspace /path/to/repo --allow-fallback-commits
```

### Отличие режимов

- `fallback disabled` (по умолчанию): tracked leftovers => немедленная ошибка и остановка.
- `fallback enabled`: ORC пытается `git add -A` + checkpoint commit; при неуспехе fallback — тоже ошибка.
