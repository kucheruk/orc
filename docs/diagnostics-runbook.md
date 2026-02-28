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
- в окне `Дополнительные опции` включите пункт `Включить debug logging в /tmp/orc`.

При включенном debug ORC пишет отдельный JSONL-файл в `/tmp/orc`.

## Где лежат логи

- Основной лог ORC: `.orc/orc.log`
- Лог хуков Cursor: `.orc/orc-hook.log`
- Debug-лог запуска ORC: `/tmp/orc/orc-debug-<YYYYMMDD-HHMMSS>-<pid>.jsonl`

## Как найти актуальный debug-файл

```bash
ls -1t /tmp/orc/orc-debug-*.jsonl | head -n 5
```

Берите самый верхний файл как самый свежий запуск.

## Как читать debug-лог

Быстрый просмотр конца файла:
```bash
tail -n 50 /tmp/orc/orc-debug-<...>.jsonl
```

Фильтрация по этапу/локации:
```bash
rg "task_execution.py|supervisor_lifecycle.py|runner.py" /tmp/orc/orc-debug-<...>.jsonl
```

Читаемый JSON через jq:
```bash
jq -c '. | {timestamp, location, message, hypothesisId}' /tmp/orc/orc-debug-<...>.jsonl
```

## Минимальный triage

1. Проверьте, что в debug-файле есть запись `debug_session_started`.
2. Найдите последние записи `completion state` и `wait_for_completion`.
3. Сопоставьте время с `.orc/orc.log` и `.orc/orc-hook.log`.
4. Если агент завершился, но задача не закрыта, проверьте записи про `stop-hook fallback`.
