# ORC / ORCS — оркестратор задач для Cursor Agent

ORC автоматизирует последовательное выполнение задач из `BACKLOG.md` с помощью Cursor Agent CLI.
**ORCS** — параллельная версия: до 4 агентов работают одновременно, AI распределяет задачи по очередям чтобы минимизировать конфликты, merge expert автоматически разрешает коллизии при интеграции в main.

## Два режима

| Команда | Сессий | Когда использовать |
|---------|--------|-------------------|
| `orc` | 1 | Последовательная работа, как раньше |
| `orcs` | до 4 | Параллельная работа, ускорение в 3-4 раза |

Оба используют один и тот же код. `orcs` = `orc --max-sessions 4`.

## Быстрый старт

### Требования

- Python 3.12+
- `uv` ([установка](https://docs.astral.sh/uv/))
- Cursor CLI (`agent`) с выполненным логином
- Репозиторий с `BACKLOG.md`

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
└── TaskExecutionEngine — выполнение одной задачи (существующий код)
```

Ключевые файлы:
- `orc_core/session_manager.py` — главный оркестратор
- `orc_core/integration_manager.py` — интеграция с отказоустойчивостью
- `orc_core/task_distributor.py` — распределение задач
- `orc_core/task_analyzer.py` — AI-анализ конфликтов
- `orc_core/session_types.py` — типы, enum, константы
- `orc_core/tui/screens/session_panel.py` — панель одной сессии
- `orc_core/tui/screens/execution.py` — Grid-контейнер панелей
- `prompts/default.txt` — промпт для агента
- `prompts/merge_expert.txt` — промпт для разрешения конфликтов
- `prompts/conflict_analysis.txt` — промпт для AI-анализа конфликтов

## Параметры командной строки

### Основные

| Флаг | По умолчанию | Описание |
|------|-------------|----------|
| `--workspace PATH` | `.` | Путь к целевому репозиторию |
| `--backlog PATH` | `BACKLOG.md` | Файл с задачами |
| `--max-sessions N` | 1 (orc) / 4 (orcs) | Количество параллельных сессий |
| `--model MODEL` | `gpt-5.2-codex` | Модель агента |
| `--mode backlog\|single\|prompt` | интерактивно | Режим выполнения |
| `--task-id ID` | — | Выполнить одну задачу (single mode) |
| `--prompt TEXT` | — | Выполнить произвольный промпт |

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
