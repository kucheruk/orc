# PROPOSALS: Next Iteration for ORC

## P0 (High ROI / Near-Term)

### 1) Cloud Agents API mode
- Добавить отдельный execution mode через Cloud Agents API для долгих задач и асинхронной оркестрации.
- Сохранить общий backlog/hook контракт, но вынести transport abstraction.

### 2) Webhook event pipeline
- При запуске задач включать webhook notifications.
- Отправлять события в единый ingest endpoint: started, tool_call, success, failure, stopped.

### 3) Permission governance profile
- Добавить `.cursor/cli.json` с явным allow/deny policy.
- Базово закрыть чувствительные чтения (`.env*`, ключи), ограничить shell в CI.

### 4) Structured telemetry
- Писать NDJSON/JSONL журнал событий в `.orc/events.log`.
- Добавить агрегаты: runtime per task, retries, tool-call latency, failure reasons.

## P1 (Important)

### 5) Telegram 2.0 reporting
- Ввести уровни уведомлений: start, stalled, completed, failed.
- Добавить retry/backoff и idempotency-key, чтобы избежать дублей.

### 6) Reliability hardening for state files
- Атомарные записи `BACKLOG.md` и `.cursor/orc-task.json` (temp-file + rename).
- Добавить lock-политику для hook операций и валидацию состояния перед update.

### 7) Diagnostics command
- Добавить `python3 orc.py --diagnose`:
  - проверка lock state,
  - проверка hook wiring,
  - проверка CLI availability/auth,
  - проверка backlog/task-file consistency.

## P2 (Strategic)

### 8) External triggers (GitHub/Slack/Linear)
- Добавить режим trigger-source metadata в отчеты.
- Поддержать сценарии запуска задач из PR comment / Slack mention / Linear issue.

### 9) Multi-repo orchestration
- Оркестрация пула репозиториев с ограничением concurrency и fairness queue.
- Общий status dashboard по портфелю репозиториев.

### 10) Capability matrix and policy engine
- Явная матрица возможностей: local CLI vs cloud agent vs CI job.
- Policy engine для выбора транспорта по типу задачи (risk/cost/time).

## Suggested Order

1. Cloud Agents API mode
2. Webhook event pipeline
3. Permission governance profile
4. Structured telemetry
5. Telegram 2.0 + reliability hardening
