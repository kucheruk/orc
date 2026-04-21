# ORC — канбан-оркестратор для AI-агентов

Виртуальная команда из 7 AI-ролей на канбан-доске: продакт, архитектор, кодер, ревьюер, тестер, интегратор, тимлид. Pull-система, WIP-лимиты, зависимости, автоматическая эскалация. До 4 агентов параллельно, merge expert разрешает коллизии при интеграции в main.

## Быстрый старт

```bash
# Установка
git clone <repository-url> && cd orc
uv tool install --editable .

# В целевом проекте
cd /path/to/your/project
orc --init-kanban          # создать доску (tasks/)
orc                        # запустить с 1 воркером
orcs                       # запустить с 4 воркерами (= orc --max-sessions 4)
```

Требования: Python 3.12+, [uv](https://docs.astral.sh/uv/), один из AI-агентов (Cursor CLI, Claude Code, Codex).

> **Claude Code skill**: `/orc-repo-init` подготовит проект за один шаг (git-проверка → чтение PRD → нарезка на карточки → создание доски → инструкции по запуску).
> Установить: `claude skills add --path <orc-repo>/skills/orc-repo-init`. Затем скажите "подготовь проект под orc".
> Есть также общий `/orc` для формата карточек, WIP-лимитов, pull-системы и slicing specs: `claude skills add --path <orc-repo>/skills/orc`.

## Как это работает

### Доска

```
Inbox → Estimate → Todo → Coding → Review → Testing → Handoff → Done
```

Каждая стадия — папка в `tasks/`. Карточки — markdown-файлы с YAML-frontmatter. WIP-лимиты: Todo=5, Coding=3, Review=3, Testing=3, Handoff=2.

### Роли

| Роль | Стадия | Что делает |
|------|--------|------------|
| **Product** | Inbox | Оценивает ценность, определяет класс сервиса, пишет требования |
| **Architect** | Estimate | Проектирует решение, оценивает трудоёмкость, указывает зависимости |
| **Coder** | Coding | Пишет тесты и код в изолированном worktree |
| **Reviewer** | Review | Ревьюит код, возвращает кодеру или пропускает дальше |
| **Tester** | Testing | Запускает тесты, возвращает кодеру или пропускает |
| **Integrator** | Handoff | Squash-merge ветки в main; детерминированный gate не даёт `Done` без кода в main |
| **Teamlead** | Любая | Арбитраж при зацикливании, инцидент-менеджмент |

### Pull-система

Воркеры ищут работу **справа налево** (от Handoff к Inbox) — приоритет у карточек ближе к Done. Карточка перемещается автоматически при смене `action` в YAML-frontmatter.

**Зависимости**: `dependencies: [TASK-001]` — карточка не попадёт в Todo, пока зависимости не в Done.

### Обратная связь и эскалация

- Ревьюер/тестер возвращает карточку кодеру → `loop_count++`
- `loop_count ≥ 2` → арбитраж тимлида
- `loop_count ≥ 4` → принудительная блокировка + Telegram-уведомление

### Инцидент-менеджмент

При краше воркера открывается инцидент (`incident_detected`): воркеры остаются scaled down, ORC пробует triage через teamlead, при невозможности автоматической починки — уведомляет оператора через Telegram и ждёт человека. Инциденты фиксируются в `docs/orc-autonomy-ledger.md` с root cause + fix.

### Human-in-the-loop

ORC работает автономно. Человек вмешивается при:
- **Блокировке** (`loop_count ≥ 4`) — `/unblock TASK-001 директива` в TUI или подправить card и дать `kill -USR1` + restart
- **Expedite** — Telegram-уведомление при срочной карточке
- **ORC-инциденте** — `notify_human` в incident FSM шлёт traceback в Telegram

## Формат карточки

```yaml
id: TASK-001
title: Добавить страницу логина
stage: 4_Coding
action: Coding
class_of_service: standard    # expedite | fixed-date | standard | intangible
value_score: 80               # 0-100, от продакта
effort_score: 30              # 0-100, от архитектора
roi: 2.67                     # auto: value / effort
dependencies: [TASK-000]
loop_count: 1
assigned_agent: s2
```

Тело: `# 1. Product Requirements`, `# 2. Technical Design & DoD`, `# 3. Implementation Notes`, `# 4. Feedback & Checklist`.

**Приоритизация**: expedite > fixed-date (по дедлайну) > standard (по ROI) > intangible.

## TUI

- **8 колонок** с карточками: ID, action, агент, таймер, ROI
- **Метрики**: Lead Time, Throughput, Total/Done/Blocked
- **Decision Journal**: лента событий
- **Чат-ввод**: название → новая карточка в Inbox, `/unblock TASK-ID директива`
- **Цвет заголовка колонки**: зелёный/жёлтый/красный по WIP-загрузке

## Параметры командной строки

| Флаг | По умолчанию | Описание |
|------|-------------|----------|
| `--workspace PATH` | `.` | Путь к целевому репозиторию |
| `--max-sessions N` | 4 | Параллельных воркеров (2-4) |
| `--model MODEL` | `gpt-5.3-codex` | Модель агента |
| `--backend` | `cursor` | `cursor` / `claude` / `codex` |
| `--init-kanban` | — | Создать доску и выйти |
| `--stall-timeout` | 600с | Таймаут без вывода |
| `--task-ttl` | 6ч | Макс. время на задачу |
| `--max-restarts` | 2 | Рестартов при зависании |
| `--commit-phase` / `--no-commit-phase` | вкл | Отдельная фаза коммита |
| `--commit-model` | `--model` | Модель для commit phase |
| `--debug` | — | Debug-логирование |
| `--drop` | — | Сбросить состояние задачи |
| `--reinit-hooks` | — | Пересоздать хуки |

## Надёжность

**Интеграция в main** — squash-merge рабочей ветки `orc/<ID>` в main, чтобы все коммиты карточки попали одним изменением. Перед переходом в `Done` срабатывает integration gate: `_is_branch_integrated()` проверяет, что код реально есть в main (через merge-base + two-dot diff), иначе карточка не сдвигается. При конфликте в `tasks/*` (частый случай, когда master двигает card по стадиям) работает auto-resolve в пользу HEAD. Каждая интеграция пишет JSON-отчёт в `integration-reports/`.

**Worktree-изоляция** — каждая задача в своём git worktree `~/Library/Application Support/orc/worktrees/<hash>/<ID>`, переиспользуется между стадиями (Coding → Review → Testing → Handoff loop-back) и сохраняется до `Done`. Worktree получает per-worktree атрибут `tasks/** merge=ours`, поэтому агентский `git merge master --no-edit` не оставляет rename-modify конфликт-маркеры в card-файлах. Canonical card копируется из master в worktree перед каждой сессией агента, стейл-дубликаты удаляются.

**Token budget per card** — `tokens_spent` и `token_budget` в frontmatter; при exhaustion card авто-блокируется (`is_budget_exhausted`). Budget может быть авто-увеличен на основании исторических burn-метрик, чтобы не терять активную работу.

**Graceful shutdown** — `kill -USR1 <pid>` (не SIGTERM) переводит ORC в quit-after-task: воркеры доделывают текущие сессии, затем ORC выходит с кодом 0. SIGTERM не триггерит graceful-путь и ведёт к потере in-flight работы.

**Rate limits** — staggered start (5с между сессиями), детекция по `network_problem`, backoff 30→60→120→240с.

## Telegram-уведомления

```bash
# Конфиг
echo '{"bot_token": "TOKEN", "chat_id": "CHAT_ID"}' > .orc/telegram.json

# Или переменные
export ORC_TELEGRAM_TOKEN="..." ORC_TELEGRAM_CHAT_ID="..."

# Отключить
export ORC_TELEGRAM_DISABLE=1
```

## Диагностика

| Что | Где |
|-----|-----|
| ORC лог (подробный) | `~/Library/Application Support/orc/repos/<hash>/logs/orc.log` |
| Operator signals (курируемые события) | `~/Library/Application Support/orc/repos/<hash>/analytics/signals.jsonl` |
| Stats per-task / total | `~/Library/Application Support/orc/repos/<hash>/analytics/stats.json` |
| Raw-stream агентских сессий | `~/Library/Application Support/orc/repos/<hash>/runs/kanban-sN/raw-stream/*.log` |
| Structured agent results | `~/Library/Application Support/orc/repos/<hash>/runs/kanban-sN/results/*.json` |
| Worktrees | `~/Library/Application Support/orc/worktrees/<hash>/<TASK_ID>/` |
| Parallel slot state | `~/Library/Application Support/orc/repos/<hash>/parallel/sN/active-task.json` |
| Integration reports | `~/Library/Application Support/orc/repos/<hash>/integration-reports/` |
| Lockfile (pid+pgid) | `~/Library/Application Support/orc/runtime/locks/<hash>.lock` |
| Autonomy ledger (инциденты, фиксы) | `docs/orc-autonomy-ledger.md` |
| Signals digest (rolling) | `orc --workspace PATH --signals-digest 20m` |
| Debug лог | `--debug` → системный temp |

---

## Архитектура (для контрибьюторов)

```
orc_core/
├── cli/                                — CLI entrypoint (orc, orcs), lock, templates
├── agents/
│   ├── session/manager.py              — KanbanSessionManager: teamlead + N воркер-потоков
│   ├── session/pool.py                 — worker slot pool, WIP-арбитр
│   ├── runners/                        — worker/teamlead loops, assignment, support
│   ├── results/                        — структурированный card_update JSON, валидация, apply
│   ├── monitoring/                     — stream-json монитор, token tracker
│   └── infra/                          — build_orchestrator composition, notifications
├── board/
│   ├── kanban_board.py                 — in-memory доска, refresh, reconcile
│   ├── kanban_card.py                  — модель карточки (YAML + markdown)
│   ├── kanban_distributor.py           — потокобезопасная раздача карточек
│   ├── kanban_pull.py                  — pull справа налево, dep-gate, budget-reset
│   ├── kanban_role_registry.py         — profiling ролей (worktree/delivery/prompt)
│   ├── state_machine.py                — единый источник переходов (TRANSITIONS, FORWARD_MOVES)
│   └── movement_rules.py               — resolve_deferred_target (обёртка над FORWARD_MOVES)
├── git/
│   ├── worktree_lifecycle.py           — create/reuse/cleanup worktree + tasks/** merge=ours
│   ├── worktree_card_sync.py           — canonical card sync, stale-duplicate cleanup
│   └── use_cases/finalize_task_worktree.py — integrator-side squash-merge в main
├── incident/
│   ├── manager.py                      — инцидент-FSM
│   └── phases.py                       — triage → notify_human → resolve
├── signals/                            — курируемые события, digest, jsonl-журнал
├── tasks/                              — lifecycle, integration, stages, outcomes
├── errors/                             — crash_handler (SIGUSR1 quit-after-task)
├── infra/io/state_paths.py             — все платформенные пути (~/Library/Application Support/orc/...)
├── tui/                                — Textual UI
└── notifications/                      — Telegram/severity
prompts/kanban_*.txt                    — промпты 7 ролей + commit
```

### Границы ответственности

| Граница | ORC (Python) | AI-агент |
|---------|-------------|----------|
| **Выбор работы** | `board/kanban_pull.py::find_next_work` — WIP, deps, CoS | — |
| **Контекст** | роль собирает промпт: board summary + card body + worktree | Читает TECHSPEC/AGENTS.md |
| **Исполнение** | subprocess + stream monitor + agent result file | Пишет код, тесты, commit, записывает JSON результат |
| **Валидация** | `agents/results/worker_result_processor.py` — fingerprint, run_id, payload | Промпт описывает контракт, enforce в коде |
| **Перемещение** | `board/state_machine.py::FORWARD_MOVES` + `has_wip_room()` | Выставляет `action` в JSON payload, код двигает карточку |
| **Эскалация** | `loop_count ≥ 2` → teamlead arbitration, `≥ 4` → соft-escalation | Teamlead решает через YAML decision файл |
| **Интеграция** | `git/use_cases/finalize_task_worktree.py` — squash-merge, integration gate | Integrator ставит `next_action: ""` (auto-default = Done) |

### Цикл обработки карточки

```
 PULL              find_next_work() → WorkAssignment {card, role}
   ↓
 PROMPT            build_prompt(role, card, board) + worktree context
   ↓
 LAUNCH            create_task_worktree() (или reuse) → backend.build_agent_cmd → subprocess
   │                • пишет tasks/** merge=ours в worktree/info/attributes
   │                • sync canonical card из master
   ↓
 ═══════════════   AI-АГЕНТ: читает код, пишет код + commit
   │                • в конце cat > $ORC_AGENT_RESULT_FILE <<JSON ... JSON
   ↓
 STREAM            StreamJsonMonitor → MonitorSnapshot → TUI + токен-учёт
   ↓
 VALIDATE          process_worker_card_result(): fingerprint (stage/action/file_path),
                   run_id, payload_kind, role; нормализует literal $ORC_AGENT_RUN_ID
                   из поломанного heredoc
   ↓
 APPLY             apply_card_update_result(): field_updates, section_updates,
                   feedback_append, next_action → stage transition через state_machine
   ↓
 INTEGRATE         (Handoff) squash_merge_task_branch() + is_branch_integrated gate →
                   card двигается в Done, emit signal card.done
   ↓
 MOVE              board.refresh() → goto PULL
```

Контракт между кодом и агентом — **JSON result-файл по пути `$ORC_AGENT_RESULT_FILE`** с `launch_fingerprint`. Card `.md` — единственный источник правды для board state, но агенты не редактируют его напрямую; только через `section_updates`/`feedback_append` в JSON.
