# ORC / ORCS — оркестратор задач для AI-агентов

> **Claude Code skill**: `/orc-repo-init` — подготовит любой проект для ORC за один шаг.
> Установка скилла: `claude skills add --path <orc-repo>/skills/orc-repo-init`
> После установки — откройте терминал в папке своего проекта и скажите Claude Code: "подготовь проект под orc" или "/orc-repo-init".

ORC автоматизирует последовательное выполнение задач из `BACKLOG.md` с помощью AI-агентов (Cursor, Claude Code, Codex).
**ORCS** — параллельная версия: до 4 агентов работают одновременно, AI распределяет задачи по очередям чтобы минимизировать конфликты, merge expert автоматически разрешает коллизии при интеграции в main.
**Kanban** — режим виртуальной команды: 7 специализированных ролей (продакт, архитектор, кодер, ревьюер, тестер, интегратор, тимлид) работают на канбан-доске с pull-системой, WIP-лимитами, управлением зависимостями и автоматической эскалацией.

## Три режима

| Команда | Сессий | Когда использовать |
|---------|--------|-------------------|
| `orc` | 1 | Последовательная работа, как раньше |
| `orcs` | до 4 | Параллельная работа, ускорение в 3-4 раза |
| `orc --mode kanban` | до 4 | Виртуальная команда с ролями и канбан-доской |

`orcs` = `orc --max-sessions 4`. Kanban = `orc --mode kanban`.

## Бэкенды

ORC поддерживает три агентных бэкенда:

| Бэкенд | CLI | Флаг |
|--------|-----|------|
| **Cursor** | `agent` | `--backend cursor` (по умолчанию) |
| **Claude Code** | `claude` | `--backend claude` |
| **Codex** | `codex` | `--backend codex` |

Бэкенд определяет, какой AI-агент выполняет задачи. Модель задаётся через `--model` (по умолчанию `gpt-5.3-codex`).

## Быстрый старт

### Требования

- Python 3.12+
- `uv` ([установка](https://docs.astral.sh/uv/))
- Один из AI-агентов: Cursor CLI (`agent`), Claude Code (`claude`), или Codex CLI (`codex`)
- Репозиторий с `BACKLOG.md` (для backlog-режима) или `tasks/` (для kanban)

### Установка

```bash
git clone <repository-url>
cd orc
uv tool install --editable .
```

После этого `orc` и `orcs` доступны из любой директории.

### Формат BACKLOG.md

```markdown
- [ ] TASK-01 Описание первой задачи
- [ ] TASK-02 Описание второй задачи
- [x] TASK-03 Уже выполненная задача
```

Task ID: заглавные буквы, цифры, дефисы (например `AUTH-01`, `SECOPS-07`).

### Запуск

```bash
cd /path/to/your/project

# Однопоточный (по одной задаче)
orc

# Параллельный (до 4 агентов)
orcs

# Или с явным числом сессий
orc --max-sessions 3
```

ORC покажет TUI с прогрессом, reasoning агента и статусом интеграции.

## Как это работает

### Однопоточный режим (`orc`)

1. Читает `BACKLOG.md`, находит первую незавершённую задачу
2. Создаёт git worktree для изоляции
3. Запускает Cursor Agent с промптом из `prompts/default.txt`
4. Агент работает: читает код, пишет код, запускает тесты
5. По завершении — commit phase (отдельный агент коммитит и пушит)
6. Cherry-pick коммита в main branch
7. Переходит к следующей задаче

### Параллельный режим (`orcs`)

1. AI анализирует все открытые задачи и строит граф конфликтов (какие задачи могут затронуть одни и те же файлы)
2. Задачи распределяются по очередям: конфликтующие — в одну (последовательно), неконфликтующие — в разные (параллельно)
3. Запускается до 4 сессий, каждая в своём git worktree
4. Интеграция в main — последовательная (через lock): cherry-pick по одному
5. При конфликте автоматически запускается merge expert agent
6. Если очередь опустела — повторный AI-анализ оставшихся задач

### TUI (терминальный интерфейс)

Экран адаптируется под количество сессий:

| Сессий | Layout | Детализация |
|--------|--------|-------------|
| 1 | Полный экран | Всё: stats, recent files/commands, reasoning, events |
| 2 | 2 колонки | Stats, recent files/commands, reasoning, events |
| 3 | 3 колонки | Stats, recent, reasoning, events (flexible height) |
| 4 | 2x2 grid | Stats, reasoning, events |

Горячие клавиши:
- `+` / `-` — добавить / убрать сессию
- `Escape` — остановить (подтверждение)
- `q` — завершить после текущих задач
- `t` — переключить тему

## Что отображается на панели

- **Task ID и стадия**: `SECOPS-07 [implementation]`
- **Прогресс**: `180+3/183 98%` (завершено + в работе / всего)
- **Текст задачи**: полное описание из BACKLOG.md
- **Активность агента**: BOOT → THINK → EXEC → OUTPUT → WAIT
- **I/O**: объём данных к модели и от модели в реальном времени
- **Reasoning**: последние мысли агента
- **Events**: последние действия

## Архитектура (для разработчиков)

```
SessionManager          — оркестрация 1..4 параллельных сессий
├── TaskDistributor     — AI-анализ конфликтов, очереди задач
├── IntegrationManager  — cherry-pick в main, merge expert, recovery
├── TaskAnalyzer        — LLM-вызов для графа конфликтов
├── Backend             — абстракция бэкенда (Cursor / Claude / Codex)
└── TaskExecutionEngine — выполнение одной задачи через выбранный бэкенд
```

Ключевые файлы:
- `orc_core/session_manager.py` — главный оркестратор
- `orc_core/integration_manager.py` — интеграция с отказоустойчивостью
- `orc_core/task_distributor.py` — распределение задач
- `orc_core/task_analyzer.py` — AI-анализ конфликтов
- `orc_core/backend.py` — интерфейс бэкенда
- `orc_core/backends/` — реализации (cursor, claude, codex)
- `orc_core/session_types.py` — типы, enum, константы
- `orc_core/tui/screens/session_panel.py` — панель одной сессии
- `orc_core/tui/screens/execution.py` — Grid-контейнер панелей
- `prompts/default.txt` — промпт для агента
- `prompts/merge_expert.txt` — промпт для разрешения конфликтов
- `prompts/conflict_analysis.txt` — промпт для AI-анализа конфликтов

### Kanban-режим (`orc --mode kanban`)

Kanban — это pull-система с виртуальной командой из 7 AI-ролей. В отличие от backlog/orcs-режимов, где агенты выполняют задачи целиком, здесь каждая карточка проходит через конвейер специализированных ролей.

#### Запуск

```bash
# Инициализировать доску (создать папку tasks/ с колонками)
orc --init-kanban --workspace /path/to/project

# Запустить канбан-режим
orc --mode kanban --workspace /path/to/project
```

#### Доска: 8 стадий

```
Inbox → Estimate → Todo → Coding → Review → Testing → Handoff → Done
```

Каждая стадия — папка в `tasks/` (например `tasks/1_Inbox/`, `tasks/4_Coding/`). Карточки — markdown-файлы с YAML-frontmatter внутри папок.

WIP-лимиты ограничивают количество карточек в стадии (Todo=5, Coding=3, Review=3, Testing=3, Handoff=2). Inbox и Done — без лимитов.

#### 7 ролей

| Роль | Стадия | Что делает |
|------|--------|------------|
| **Product** | Inbox | Оценивает ценность (0-100), определяет класс сервиса, пишет требования |
| **Architect** | Estimate | Проектирует решение, оценивает трудоёмкость (0-100), указывает зависимости |
| **Coder** | Coding | Пишет тесты и код в изолированном worktree, исправляет замечания |
| **Reviewer** | Review | Ревьюит код (SOLID, DRY, KISS), возвращает кодеру или пропускает дальше |
| **Tester** | Testing | Запускает тесты, пишет дополнительные, возвращает кодеру или пропускает |
| **Integrator** | Handoff | Cherry-pick/merge в main, запускает тесты на main |
| **Teamlead** | Любая | Арбитраж при зацикливании, инцидент-менеджмент (crash triage, scale-down/fix/scale-up) |

#### Pull-система

Воркеры ищут работу **справа налево** (от Handoff к Inbox) — приоритет у карточек ближе к Done. Это минимизирует WIP и ускоряет завершение начатых задач.

Карточка перемещается между стадиями автоматически при смене `action` в YAML-frontmatter. Например, кодер ставит `action: Reviewing` → карточка переезжает из `4_Coding` в `5_Review`.

#### Зависимости между карточками

Карточки могут указывать зависимости в поле `dependencies: [TASK-001, TASK-002]`. Карточка с неразрешёнными зависимостями остаётся в `2_Estimate` и не попадает в `3_Todo`. Когда все зависимости завершены (карточки в `8_Done`), карточка автоматически продвигается в Todo.

#### Петли обратной связи и эскалация

- Ревьюер/тестер возвращает карточку кодеру → `loop_count` увеличивается
- `loop_count ≥ 2` → подключается Teamlead для арбитража (loop_count не сбрасывается — накапливается)
- `loop_count ≥ 4` → принудительная блокировка карточки + уведомление в Telegram (даже если тимлид пытается "решить" — force-block)

#### Инцидент-менеджмент (Teamlead)

При крэше воркера тимлид запускает цикл реагирования:

1. **Scale-down** — останавливает все воркеры, ждёт завершения текущих задач
2. **Triage** — анализирует крэш-лог, определяет причину и план исправления
3. **Fix** — создаёт FIX-карточку, запускает кодера для исправления в изолированном worktree
4. **Scale-up** — перезапускает воркеры после успешного исправления

#### Human-in-the-loop

Канбан-режим работает автономно, включая интеграцию в main. Человек вмешивается только в двух случаях:

**1. Заблокированные карточки**
Когда карточка зацикливается (`loop_count ≥ 4`), она блокируется и приходит уведомление в Telegram. Разблокировать можно через чат-поле TUI:

```
/unblock TASK-001 директива — сбросить loop_count, добавить директиву, вернуть в работу
```

**2. Expedite-уведомления**
Когда AI помечает карточку как `expedite`, в Telegram приходит уведомление с причиной. Человек может проверить и при необходимости вмешаться.

#### Карточка (формат)

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

Тело карточки содержит секции: `# 1. Product Requirements`, `# 2. Technical Design & DoD`, `# 3. Implementation Notes`, `# 4. Feedback & Checklist`.

#### TUI канбан-доски

- **Метрики**: Lead Time, Throughput, Total Cards, Done, Blocked
- **8 колонок**: каждая показывает карточки с ID, action, назначенным агентом, таймером и ROI
- **Цветовая индикация**: зелёный/жёлтый/красный заголовок колонки по WIP-загрузке; голубая рамка — активная; красная — заблокированная/expedite
- **Decision Journal**: лента событий (перемещения, завершения, эскалации)
- **Чат-ввод**: добавление карточек + команда `/unblock`

#### Worktree-изоляция

Каждая задача получает один git worktree (`orc/{task-id}`), который переиспользуется между стадиями (Coding → Review → Coding loop-back). Worktree создаётся при первом назначении кодеру и очищается только когда карточка достигает `8_Done`.

#### Архитектура kanban

```
KanbanSessionManager         — 1 teamlead-поток + N worker-потоков
├── KanbanDistributor        — потокобезопасная раздача карточек
│   └── find_next_work()     — pull справа налево с учётом WIP и зависимостей
├── KanbanBoard              — in-memory доска, чтение/запись с диска
├── KanbanCard               — модель карточки (YAML + markdown)
├── process_agent_result()   — валидация изменений агента, loop-count, перемещение
├── build_prompt()           — инъекция контекста доски в промпты ролей
├── TeamleadIncident         — инцидент-менеджмент (triage → fix → scale-up)
├── TeamleadActions          — исполнение решений тимлида (set_action, move, skip, notify)
├── WorktreeFlow             — создание/reuse/cleanup worktree по задачам
└── KanbanPublisher          — снапшоты доски и журнал для TUI
```

#### Цикл выполнения: код → промпт → агент → код

Диаграмма показывает один цикл обработки карточки — от выбора работы до валидации результата. Границы между Python-кодом ORC и AI-агентом отмечены явно.

```
                          ┌─────────────────────────────────────────────────┐
                          │              ORC Python (код)                   │
                          │                                                 │
  ┌───────────────────────┤  1. PULL: выбор работы                         │
  │                       │                                                 │
  │  KanbanBoard          │  find_next_work()           kanban_pull.py      │
  │  ┌──────────┐         │  ┌───────────────────────────────────────┐      │
  │  │ tasks/   │────────►│  │ scan R→L: Handoff→...→Inbox          │      │
  │  │ */*.md   │  read   │  │ check WIP limits, deps, CoS priority │      │
  │  └──────────┘         │  │ auto-promote Estimate→Todo           │      │
  │       ▲               │  └───────────────┬───────────────────────┘      │
  │       │               │                  │                              │
  │       │               │                  ▼                              │
  │       │               │  WorkAssignment { card, role, needs_worktree }  │
  │       │               │                  │                              │
  │       │               ├──────────────────┼──────────────────────────────┤
  │       │               │  2. PROMPT: сборка промпта                     │
  │       │               │                  │                              │
  │       │               │                  ▼                              │
  │       │               │  build_prompt(role, card, board)                │
  │       │               │  ┌───────────────────────────────────────┐      │
  │       │               │  │ _load_template(role)                  │      │
  │       │               │  │   → prompts/kanban_{role}.txt         │      │
  │       │               │  │ format_board_summary(board)           │      │
  │       │               │  │   → markdown table: stage/WIP/free    │      │
  │       │               │  │ card.to_markdown()                    │      │
  │       │               │  │   → YAML frontmatter + body           │      │
  │       │               │  │ template.format_map(SafeDict(...))    │      │
  │       │               │  │   → {board_summary}, {card_content},  │      │
  │       │               │  │     {card_path}, {card_id}, ...       │      │
  │       │               │  └───────────────┬───────────────────────┘      │
  │       │               │                  │ rendered prompt (str)        │
  │       │               │                  │                              │
  │       │               ├──────────────────┼──────────────────────────────┤
  │       │               │  3. LAUNCH: запуск агента                      │
  │       │               │                  │                              │
  │       │               │                  ▼                              │
  │       │               │  create_task_worktree()  (if needs_worktree)    │
  │       │               │  backend.build_agent_cmd(model, prompt)         │
  │       │               │  ┌───────────────────────────────────────┐      │
  │       │               │  │ claude -p --output-format stream-json │      │
  │       │               │  │   --model {model}                     │      │
  │       │               │  │   --dangerously-skip-permissions      │      │
  │       │               │  │   "{rendered_prompt}"                  │      │
  │       │               │  └───────────────┬───────────────────────┘      │
  │       │               │                  │ subprocess.Popen             │
  │       │               └──────────────────┼──────────────────────────────┘
  │       │                                  │
  │       │               ╔══════════════════╧══════════════════════════════╗
  │       │               ║           AI-АГЕНТ (чёрный ящик)               ║
  │       │               ║                                                ║
  │       │               ║  Агент получает:                               ║
  │       │               ║  • роль и обязанности                          ║
  │       │               ║  • состояние доски (таблица WIP)               ║
  │       │               ║  • содержимое карточки (YAML + body)           ║
  │       │               ║  • правила: valid actions, protected fields    ║
  │       │               ║                                                ║
  │       │               ║  Агент делает:                                 ║
  │       │               ║  • читает TECHSPEC.md, AGENTS.md, код          ║
  │       │               ║  • пишет код, запускает тесты (coder)          ║
  │       │               ║  • перезаписывает card .md файл                ║
  │       │               ║    (меняет YAML frontmatter: action, scores)   ║
  │       │               ║    (заполняет секции 1-4 в body)               ║
  │       │               ║  • делает git commit (coder, если commit_phase)║
  │       │               ║                                                ║
  │       │               ║  stream-json → stdout                          ║
  │       │               ╚══════════════════╤══════════════════════════════╝
  │       │                                  │
  │       │               ┌──────────────────┼──────────────────────────────┐
  │       │               │  ORC Python (код)│                              │
  │       │               │                  ▼                              │
  │       │               │  StreamJsonMonitor                              │
  │       │               │  ┌───────────────────────────────────────┐      │
  │       │               │  │ парсит stream-json: tokens, files,    │      │
  │       │               │  │ commands, reasoning, progress         │      │
  │       │               │  │ → MonitorSnapshot → TUI               │      │
  │       │               │  └───────────────┬───────────────────────┘      │
  │       │               │                  │ agent finished               │
  │       │               │                  │                              │
  │       │               ├──────────────────┼──────────────────────────────┤
  │       │               │  4. VALIDATE: валидация результата              │
  │       │               │                  │                              │
  │       │               │                  ▼                              │
  │       │               │  process_agent_result(board, card, role)        │
  │       │               │  ┌───────────────────────────────────────┐      │
  │       │               │  │ a) re-read card from disk             │      │
  │       │               │  │ b) check protected fields unchanged   │      │
  │       │               │  │    PROTECTED = {id, stage, roi,       │      │
  │       │               │  │      assigned_agent, created_at}      │      │
  │       │               │  │ c) revert role-readonly fields        │      │
  │       │               │  │    architect: ✗ value_score, CoS      │      │
  │       │               │  │    coder:     ✗ value/effort_score    │      │
  │       │               │  │ d) validate action transition         │      │
  │       │               │  │    product:    Product → {Architect,  │      │
  │       │               │  │                          Coding}      │      │
  │       │               │  │    architect:  Architect → {Product}  │      │
  │       │               │  │    coder:      Coding → {Reviewing,   │      │
  │       │               │  │                         Testing}      │      │
  │       │               │  │    reviewer:   Reviewing → {Coding,   │      │
  │       │               │  │                            Testing}   │      │
  │       │               │  │    tester:     Testing → {Coding,     │      │
  │       │               │  │                          Integrating} │      │
  │       │               │  │    integrator: Integrating → {Done}   │      │
  │       │               │  │ e) auto-default if action unchanged:  │      │
  │       │               │  │    coder→Reviewing, reviewer→Testing, │      │
  │       │               │  │    tester→Integrating                 │      │
  │       │               │  │ f) increment loop_count if → Coding   │      │
  │       │               │  │ g) restore protected, recompute ROI   │      │
  │       │               │  │ h) save card, move to new stage       │      │
  │       │               │  │    if FORWARD_MOVES[stage,action]     │      │
  │       │               │  │    and WIP room available             │      │
  │       │               │  └───────────────┬───────────────────────┘      │
  │       │               │                  │                              │
  │       │               ├──────────────────┼──────────────────────────────┤
  │       │               │  5. NEXT: цикл повторяется                     │
  │       │               │                  │                              │
  │       │               │                  ▼                              │
  │       │               │  board.refresh() → goto step 1                  │
  │       │               │                                                 │
  │       │               │  Если loop_count ≥ 2:                           │
  │       │               │    → teamlead arbitration (отдельный поток)     │
  │       │               │    → build_teamlead_prompt() → decision YAML    │
  │       │               │    → execute_teamlead_actions()                 │
  │       │               │                                                 │
  │       │               │  Если agent crash:                              │
  │       │               │    → teamlead incident response                 │
  │       │               │    → build_incident_prompt() → triage decision  │
  │       │               │    → create FIX card, scale-down/up             │
  └───────┼───────────────│                                                 │
          │               └─────────────────────────────────────────────────┘
          │
          │  card .md file = единственный контракт между кодом и агентом
          │  агент пишет в файл, код читает из файла
          │
          ▼
```

**Границы ответственности:**

| Граница | Код (ORC) | Промпт/Агент |
|---------|-----------|--------------|
| **Выбор работы** | `find_next_work()` — WIP, deps, CoS | — |
| **Контекст** | `build_prompt()` — board state, card content | Агент читает TECHSPEC/AGENTS.md |
| **Исполнение** | subprocess + stream monitor | Агент пишет код, тесты, модифицирует card .md |
| **Валидация** | `process_agent_result()` — protected fields, transitions, loop_count | Промпт описывает правила, но enforce в коде |
| **Перемещение** | `FORWARD_MOVES` + `has_wip_room()` | Агент выставляет `action`, код двигает карточку |
| **Эскалация** | `loop_count ≥ 2` → teamlead, `≥ 4` → force-block | Teamlead принимает решение через YAML decision file |
| **Интеграция** | `IntegrationManager` — cherry-pick, merge expert | Integrator агент пишет summary, ставит `action: Done` |

Ключевые файлы:
- `orc_core/kanban_session_manager.py` — оркестратор потоков
- `orc_core/kanban_board.py` — доска и WIP-лимиты
- `orc_core/kanban_card.py` — модель карточки
- `orc_core/kanban_pull.py` — pull-система (правило «справа налево»)
- `orc_core/kanban_agent_output.py` — валидация и переходы
- `orc_core/kanban_distributor.py` — раздача работы воркерам
- `orc_core/kanban_constants.py` — стадии, действия, классы сервиса
- `orc_core/kanban_roles.py` — построение промптов по ролям
- `orc_core/teamlead_incident.py` — инцидент-менеджмент тимлида
- `orc_core/teamlead_actions.py` — исполнение решений тимлида
- `orc_core/worktree_flow.py` — управление worktree
- `orc_core/role_config.py` — конфигурация моделей по ролям
- `orc_core/tui/screens/kanban_screen.py` — TUI канбан-доски
- `prompts/kanban_*.txt` — промпты для каждой из 8 ролей (включая 2 промпта тимлида)

## Параметры командной строки

### Основные

| Флаг | По умолчанию | Описание |
|------|-------------|----------|
| `--workspace PATH` | `.` | Путь к целевому репозиторию |
| `--backlog PATH` | `BACKLOG.md` | Файл с задачами |
| `--max-sessions N` | 1 (orc) / 4 (orcs) | Количество параллельных сессий |
| `--model MODEL` | `gpt-5.3-codex` | Модель агента |
| `--backend cursor\|claude\|codex` | `cursor` | Агентный бэкенд |
| `--mode backlog\|single\|prompt\|kanban` | интерактивно | Режим выполнения |
| `--task-id ID` | — | Выполнить одну задачу (single mode) |
| `--prompt TEXT` | — | Выполнить произвольный промпт |
| `--init-kanban` | — | Инициализировать канбан-доску (папка `tasks/`) и выйти |

### Тайминги

| Флаг | По умолчанию | Описание |
|------|-------------|----------|
| `--stall-timeout` | 600с | Таймаут без вывода (зависание) |
| `--task-ttl` | 21600с (6ч) | Макс. время на задачу |
| `--max-restarts` | 2 | Макс. рестартов при зависании |

### Commit phase

| Флаг | По умолчанию | Описание |
|------|-------------|----------|
| `--commit-phase` / `--no-commit-phase` | включено | Отдельная фаза коммита |
| `--commit-model` | как `--model` | Модель для commit phase |
| `--allow-fallback-commits` | выключено | Авто-коммит при остаточных изменениях |

### Отладка

| Флаг | Описание |
|------|----------|
| `--debug` | Debug-логирование в temp |
| `--drop` | Удалить состояние и перезапустить задачу |
| `--reinit-hooks` | Пересоздать хуки |

## Отказоустойчивость интеграции

При параллельной работе конфликты при cherry-pick неизбежны. ORC обрабатывает их:

1. **Preflight** — проверка что base repo чистый
2. **Cherry-pick** — перенос коммита задачи в main
3. **Конфликт?** → запуск merge expert agent (разрешает, делает `cherry-pick --continue`)
4. **Верификация** — проверка что cherry-pick завершён
5. **При любой ошибке** — `cherry-pick --abort`, base repo возвращается в чистое состояние
6. **Integration report** — JSON-файл с каждым шагом для диагностики

BACKLOG.md и changelog.md конфликтуют практически всегда — merge expert знает об этом и принимает обе стороны.

## Защита от rate limit

При 4 параллельных агентах возможны API rate limits:

- **Staggered start**: 5 секунд между запусками сессий
- **Rate limit detection**: по `network_problem` в stream output
- **Backoff**: 30 → 60 → 120 → 240 секунд при повторных rate limits

## Telegram-уведомления (опционально)

```bash
# Через конфиг
mkdir -p .orc
echo '{"bot_token": "YOUR_TOKEN", "chat_id": "YOUR_CHAT_ID"}' > .orc/telegram.json

# Или через переменные
export ORC_TELEGRAM_TOKEN="your_bot_token"
export ORC_TELEGRAM_CHAT_ID="your_chat_id"

# Отключить
export ORC_TELEGRAM_DISABLE=1
```

## Диагностика

- **ORC лог**: `~/Library/Application Support/orc/repos/<hash>/logs/orc.log`
- **Hook лог**: `~/Library/Application Support/orc/repos/<hash>/logs/orc-hook.log`
- **Integration reports**: `~/Library/Application Support/orc/repos/<hash>/integration-reports/`
- **Debug лог**: `--debug` → файл в системном temp
