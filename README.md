# ORC — оркестратор задач для Cursor Agent

ORC нужен для репозитория с корректно оформленным `BACKLOG.md`: он последовательно запускает coding agent для каждой задачи, подставляя заранее заданные промпты. То есть это оркестратор, который ведёт агента по задачам одну за другой.

Промпты спроектированы так, чтобы в начале агент читал информацию из доков, а по завершению — возвращал результаты обратно в документы. В итоге знания остаются консистентными по мере разработки, и каждый агент более‑менее в курсе контекста всей кодовой базы.

## Быстрый старт

### Требования

- Python 3.12+
- Установлен `uv` (https://docs.astral.sh/uv/)
- Установлен Cursor CLI (`agent`) и выполнен логин
- Репозиторий с `BACKLOG.md` и задачами с ID

Если `uv` не в PATH, установите через официальный инсталлер:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Первичная настройка

1. **Склонировать этот репозиторий:**
   ```bash
   git clone <repository-url>
   cd orc
   ```

2. **Создать/обновить окружение через uv:**
   ```bash
   uv sync
   ```

3. **Настроить Telegram‑уведомления (опционально):**
   ```bash
   mkdir -p .orc
   cp .orc/telegram.json.example .orc/telegram.json
   # Отредактируйте .orc/telegram.json и добавьте bot token и chat ID
   ```

   Или через переменные окружения:
   ```bash
   export ORC_TELEGRAM_TOKEN="your_bot_token"
   export ORC_TELEGRAM_CHAT_ID="your_chat_id"
   ```

4. **Подготовить целевой репозиторий:**
   - Создайте `BACKLOG.md` в формате:
     ```
     - [ ] TASK-01 Описание первой задачи
     - [ ] TASK-02 Описание второй задачи
     ```
   - Каждый task ID должен быть уникальным (заглавные буквы, цифры, дефисы, подчёркивания)

5. **Проверить Cursor CLI:**
   ```bash
   agent --version
   ```

6. **Запустить оркестратор:**
   ```bash
   uv run python orc.py --workspace /path/to/your/repo
   ```

   ORC сделает следующее:
   - Прочитает `BACKLOG.md` и найдёт первую невыполненную задачу
   - Создаст нужные hook‑файлы в `.cursor/` (и лог хуков в `.orc/`)
   - Запустит Cursor Agent для текущей задачи
   - Дождётся завершения и автоматически отметит задачу как выполненную
   - Запустит отдельную commit phase (если включена), чтобы сделать git commit

## Файлы, которые создаются в репозитории

Когда `orc.py` запускается для репозитория, он создаёт:

- `.cursor/orc-task.json` — состояние текущей задачи для хуков
- `.cursor/hooks/orc_before_submit.py` — hook для сохранения `conversation_id`
- `.cursor/hooks/orc_stop.py` — hook, который завершает задачу и отправляет follow‑up
- `.cursor/hooks.json` — конфигурация хуков Cursor
- `.orc/orc-hook.log` — лог работы хуков

Если `.cursor/orc-task.json` отсутствует, хуки ничего не делают.

## Алгоритм orc.py (в общих чертах)

1. Разобрать `BACKLOG.md` и найти первую открытую задачу с ID.
2. Если `.cursor/orc-task.json` уже существует:
   - Прочитать задачу из файла.
   - Если задача уже отмечена `[x]` в `BACKLOG.md`, удалить файл задачи и продолжить.
   - Иначе запустить агента в режиме “continue” для сохранённой задачи.
3. Если активной задачи нет:
   - Создать `.cursor/orc-task.json` с `task_id`, `task_text`, `backlog_path`, `workspace_root`.
   - Убедиться, что хуки созданы, а `.cursor/hooks.json` содержит нужные записи.
   - Запустить агента с дефолтным промптом для этой задачи.
4. Подождать, пока stop‑hook удалит `.cursor/orc-task.json`.
5. (Опционально) Запустить commit phase и дождаться её завершения.
6. Повторить цикл с шага 1.

## Поведение хуков

### beforeSubmitPrompt

Читает JSON из stdin и, если в репозитории есть `.cursor/orc-task.json`, то:

- забирает `conversation_id` из payload
- сохраняет его в `.cursor/orc-task.json` (если ещё не был сохранён)
- пишет лог в `.orc/orc-hook.log`

### stop

Читает JSON из stdin. Если `status = completed` и файл задачи существует, то:

- проверяет соответствие `conversation_id` (если он задан)
- отмечает строку с task ID в `BACKLOG.md` как `[x]`
- удаляет `.cursor/orc-task.json`
- пишет follow‑up JSON:
  ```
  {"followup_message":"commit+push with task ID and task description as commit message"}
  ```
- логирует детали в `.orc/orc-hook.log`

## Диагностика проблем

Если задача завершилась, но follow‑up не произошёл или файл задачи не удалён:

1. Проверьте `.orc/orc-hook.log` — там причина выхода хуков.
2. Убедитесь, что в `.cursor/orc-task.json` корректные `task_id` и `backlog_path`.
3. Проверьте, что строка в `BACKLOG.md` содержит тот же `task_id` в формате `- [ ]`.
4. Убедитесь, что `.cursor/hooks.json` ссылается на repo‑hooks.

## Использование

### Базовый запуск

```bash
uv run python orc.py --workspace /path/to/repo
```

Или с абсолютным путём:

```bash
uv run python /path/to/orc/orc.py --workspace /path/to/repo
```

### Параметры командной строки

#### Обязательные параметры
- `--workspace PATH` — путь к целевому репозиторию (по умолчанию: `.`)

#### One-off запуск без BACKLOG
- `--task TEXT` — создать временный backlog с одной задачей и выполнить её как smoke-сценарий

#### Backlog
- `--backlog PATH` — путь к файлу backlog (по умолчанию: `BACKLOG.md`)

#### Агент
- `--model MODEL` — модель Cursor agent (по умолчанию: `gpt-5.2-codex`)
- `--prompt-template PATH` — путь к кастомному prompt‑шаблону (по умолчанию: `prompts/default.txt`)
- `--continue-template PATH` — путь к prompt‑шаблону для continue (по умолчанию: `prompts/continue.txt`)

#### Тайминги и таймауты
- `--poll SECONDS` — интервал проверки статуса (по умолчанию: `1.0`)
- `--stall-timeout SECONDS` — сколько секунд без вывода считать за зависание (по умолчанию: `600.0` = 10 минут)
- `--task-ttl SECONDS` — максимальная длительность задачи (по умолчанию: `21600` = 6 часов)
- `--report-interval SECONDS` — интервал статистики (по умолчанию: `2.0`)

#### Рестарты и восстановление
- `--max-restarts COUNT` — максимум рестартов (по умолчанию: `2`)
- `--nudge-after COUNT` — отправлять continue после N одинаковых статистик (по умолчанию: `10`)
- `--nudge-cooldown SECONDS` — интервал между auto‑nudge (по умолчанию: `300.0` = 5 минут)
- `--nudge-text TEXT` — текст, отправляемый перед Enter (по умолчанию: `continue`)

#### Уведомления
- `--summary-lines COUNT` — количество строк для Telegram‑сводки (по умолчанию: `25`)
- `--telegram-test [MESSAGE]` — отправить тестовое сообщение и выйти (по умолчанию: `"orc telegram test"`)

#### Обслуживание
- `--reinit-hooks` — пересоздать хуки при старте (полезно при поломанных конфигурациях)
- `--drop` — удалить `.cursor/orc-task.json` (если есть) и перезапустить текущую задачу “с нуля” (без resume)

#### Commit phase
- `--commit-phase` / `--no-commit-phase` — включить/выключить отдельную фазу коммита после каждой завершённой задачи (по умолчанию: включено)
- `--commit-template PATH` — путь к prompt‑шаблону для commit phase (по умолчанию: `prompts/commit.txt`)
- `--commit-model MODEL` — модель для commit phase (по умолчанию: как `--model`)
- `--commit-stall-timeout SECONDS` — сколько секунд без вывода считать commit phase зависшей (по умолчанию: `300`)
- `--commit-ttl SECONDS` — максимальная длительность commit phase (по умолчанию: `1800`)

### Примеры

```bash
# Базовый запуск
uv run python orc.py --workspace /path/to/myproject

# Кастомная модель и другой backlog
uv run python orc.py --workspace /path/to/myproject --model gpt-4 --backlog TODO.md

# Проверка Telegram
uv run python orc.py --telegram-test "Hello from orc!"

# Smoke-запуск без BACKLOG.md
uv run python orc.py --workspace /path/to/myproject --model gpt-5.3-codex --task "Проанализируй текущий проект на предмет зон для рефакторинга"

# Переинициализация хуков
uv run python orc.py --workspace /path/to/myproject --reinit-hooks

# Длинные задачи
uv run python orc.py --workspace /path/to/myproject --task-ttl 43200 --stall-timeout 1200
```

## Как теперь запускается агент

ORC использует headless Cursor CLI в event-driven режиме:

```bash
agent -p --force --output-format stream-json --stream-partial-output ...
```

Это дает структурированные события (`system`, `assistant`, `tool_call`, `result`) и убирает зависимость от terminal-scraping.
Терминальный интерфейс использует Rich Live TUI: фиксированный экран, статус, последние команды и edited files.
