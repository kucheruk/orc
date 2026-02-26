# PLAN: ORC Stream-JSON Refactor

## Goal

Перевести ORC на единый runtime через `agent -p --output-format stream-json` без fallback на `ht`, повысить наблюдаемость и предсказуемость завершения задач.

## Definition of Done

- [ ] В runtime-коде нет запуска `ht`.
- [ ] Основной launcher использует `agent -p --force --output-format stream-json`.
- [ ] Мониторинг построен на NDJSON событиях (`system`, `assistant`, `tool_call`, `result`).
- [ ] Завершение задачи учитывает `result success` и hook-driven cleanup.
- [ ] Обновлены `README.md` и `techspec.md` под stream-json архитектуру.
- [ ] Добавлены roadmap-идеи в `PROPOSALS.md`.
- [ ] Ветка готова к безопасному merge/revert.

## Execution Checklist

### Phase 1: Runtime Core
- [ ] Заменить `launch_agent_with_ht` на `launch_agent_stream_json` в `orc_core/runner.py`.
- [ ] Убрать `--ht-listen` и связанные ветки из `orc_core/supervisor.py`.
- [ ] Удалить runtime-зависимость от PTY/terminal-scraping.

### Phase 2: Event-Driven Monitoring
- [ ] Добавить stream-json монитор (парсинг событий и метрик).
- [ ] Поддержать сбор статистики: токены, tool-call count, git delta, summary lines.
- [ ] Писать `.orc/orc-metrics.json` для hooks/отчетов.

### Phase 3: Completion Robustness
- [ ] Привязать success flow к событию `result`.
- [ ] Сохранить hook-driven marking (`BACKLOG.md` + удаление task-file).
- [ ] Добавить fallback-вызов stop-hook, если `result success` уже пришел, а task-file еще не удален.

### Phase 4: Docs & Rollout
- [ ] Обновить требования в `README.md` (без `ht`, с `agent`).
- [ ] Обновить архитектурный раздел в `techspec.md`.
- [ ] Зафиксировать дополнительные фичи и следующий этап в `PROPOSALS.md`.

## Rollout Notes

- Разработка ведется в отдельной feature-ветке.
- При регрессе откат выполняется Git-операциями на уровне ветки, без сохранения legacy fallback в коде.
