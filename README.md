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

> **Claude Code skill**: `/orc-repo-init` подготовит проект за один шаг.
> `claude skills add --path <orc-repo>/skills/orc-repo-init`, затем скажите "подготовь проект под orc".

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
| **Integrator** | Handoff | Cherry-pick/merge в main, запускает тесты на main |
| **Teamlead** | Любая | Арбитраж при зацикливании, инцидент-менеджмент |

### Pull-система

Воркеры ищут работу **справа налево** (от Handoff к Inbox) — приоритет у карточек ближе к Done. Карточка перемещается автоматически при смене `action` в YAML-frontmatter.

**Зависимости**: `dependencies: [TASK-001]` — карточка не попадёт в Todo, пока зависимости не в Done.

### Обратная связь и эскалация

- Ревьюер/тестер возвращает карточку кодеру → `loop_count++`
- `loop_count ≥ 2` → арбитраж тимлида
- `loop_count ≥ 4` → принудительная блокировка + Telegram-уведомление

### Инцидент-менеджмент

При крэше воркера тимлид: scale-down → triage → FIX-карточка → scale-up.

### Human-in-the-loop

ORC работает автономно. Человек вмешивается при:
- **Блокировке** (`loop_count ≥ 4`) — `/unblock TASK-001 директива` в TUI
- **Expedite** — Telegram-уведомление при срочной карточке

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

**Интеграция в main** — при конфликте cherry-pick автоматически запускается merge expert agent. При любой ошибке — `cherry-pick --abort`, base repo чистый. Каждая интеграция пишет JSON-отчёт.

**Rate limits** — staggered start (5с между сессиями), детекция по `network_problem`, backoff 30→60→120→240с.

**Worktree-изоляция** — каждая задача в своём git worktree, переиспользуется между стадиями (Coding → Review → loop-back). Очистка при достижении Done.

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
| ORC лог | `~/Library/Application Support/orc/repos/<hash>/logs/orc.log` |
| Hook лог | `~/Library/Application Support/orc/repos/<hash>/logs/orc-hook.log` |
| Integration reports | `~/Library/Application Support/orc/repos/<hash>/integration-reports/` |
| Debug лог | `--debug` → системный temp |

---

## Архитектура (для контрибьюторов)

```
KanbanSessionManager         — 1 teamlead-поток + N worker-потоков
├── KanbanDistributor        — потокобезопасная раздача карточек
│   └── find_next_work()     — pull справа налево с учётом WIP и зависимостей
├── KanbanBoard              — in-memory доска, чтение/запись с диска
├── KanbanCard               — модель карточки (YAML + markdown)
├── process_agent_result()   — валидация изменений агента, loop-count, перемещение
├── build_prompt()           — инъекция контекста доски в промпты ролей
├── TeamleadIncident         — инцидент-менеджмент (triage → fix → scale-up)
├── TeamleadActions          — исполнение решений тимлида
├── WorktreeFlow             — создание/reuse/cleanup worktree
└── KanbanPublisher          — снапшоты доски и журнал для TUI
```

### Границы ответственности

| Граница | ORC (Python) | AI-агент |
|---------|-------------|----------|
| **Выбор работы** | `find_next_work()` — WIP, deps, CoS | — |
| **Контекст** | `build_prompt()` — board state, card | Читает TECHSPEC/AGENTS.md |
| **Исполнение** | subprocess + stream monitor | Пишет код, тесты, модифицирует card .md |
| **Валидация** | `process_agent_result()` — protected fields, transitions | Промпт описывает правила, enforce в коде |
| **Перемещение** | `FORWARD_MOVES` + `has_wip_room()` | Выставляет `action`, код двигает карточку |
| **Эскалация** | `loop_count ≥ 2` → teamlead, `≥ 4` → block | Teamlead решает через YAML decision |
| **Интеграция** | `IntegrationManager` — cherry-pick, merge expert | Integrator ставит `action: Done` |

### Цикл обработки карточки

```
 PULL              find_next_work() → WorkAssignment {card, role}
   ↓
 PROMPT            build_prompt(role, card, board) → rendered prompt
   ↓
 LAUNCH            create_worktree() → backend.build_agent_cmd() → subprocess
   ↓
 ═══════════════   AI-АГЕНТ: читает код, пишет, перезаписывает card .md
   ↓
 STREAM            StreamJsonMonitor → MonitorSnapshot → TUI
   ↓
 VALIDATE          process_agent_result(): protected fields, transitions, loop_count
   ↓
 MOVE              board.refresh() → move card → goto PULL
```

Контракт между кодом и агентом — card .md файл: агент пишет, код читает и валидирует.

### Ключевые файлы

| Файл | Назначение |
|------|-----------|
| `orc_core/kanban_session_manager.py` | Оркестратор потоков |
| `orc_core/kanban_board.py` | Доска и WIP-лимиты |
| `orc_core/kanban_card.py` | Модель карточки |
| `orc_core/kanban_pull.py` | Pull-система |
| `orc_core/kanban_agent_output.py` | Валидация и переходы |
| `orc_core/kanban_distributor.py` | Раздача работы воркерам |
| `orc_core/kanban_constants.py` | Стадии, действия, классы сервиса |
| `orc_core/kanban_roles.py` | Построение промптов по ролям |
| `orc_core/teamlead_incident.py` | Инцидент-менеджмент |
| `orc_core/teamlead_actions.py` | Исполнение решений тимлида |
| `orc_core/worktree_flow.py` | Управление worktree |
| `orc_core/role_config.py` | Конфигурация моделей по ролям |
| `orc_core/tui/screens/kanban_screen.py` | TUI |
| `prompts/kanban_*.txt` | Промпты ролей (8 файлов) |
