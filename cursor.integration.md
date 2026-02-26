# Cursor Integration Guide

Практическая документация по интеграции Cursor в инженерный процесс: локальная разработка, CI/CD, облачные агенты, внешние системы и безопасность. Акцент на `Cursor CLI` и автоматизацию.

---

## 1) Что реально интегрируется

- `Cursor CLI (agent)` для интерактивной работы и headless-автоматизации.
- `Cloud Agents` для асинхронных задач в изолированной VM и API-оркестрации.
- `Rules / Commands / Skills / Subagents / Hooks` для стандартизации поведения агента.
- `MCP` для подключения внешних инструментов (GitHub, Linear, Sentry, Postgres, browser automation и т.д.).
- Каналы запуска: IDE, CLI, GitHub, Slack, Linear, API.
- `Deeplinks` для шаринга prompt/command/rule и автоподключения MCP.

---

## 2) Cursor CLI: базовая модель использования

### Установка и базовые команды

```bash
# macOS/Linux/WSL
curl https://cursor.com/install -fsS | bash

# Windows PowerShell
irm 'https://cursor.com/install?win32=true' | iex

agent --version
agent
```

### Ключевые режимы

- `Agent` (по умолчанию): полный набор инструментов, может изменять файлы.
- `Plan`: планирование с уточнениями перед реализацией.
- `Ask`: read-only исследование.
- В CLI переключение: `/plan`, `/ask`, `--mode=plan`, `--mode=ask`, `--plan`.

### Важные флаги для интеграций

- `-p, --print` — non-interactive/headless режим.
- `--output-format text|json|stream-json` — формат для пайплайнов.
- `--stream-partial-output` — дельты текста в `stream-json`.
- `-f, --force` (`--yolo`) — разрешить применение изменений без интерактива.
- `--api-key` или `CURSOR_API_KEY` — auth для CI/скриптов.
- `--approve-mcps` — auto-approve MCP серверов.
- `--sandbox enabled|disabled` — контроль sandbox-режима.
- `--workspace <path>` — запуск в конкретной рабочей директории.

### Резюмирование сессий

- `agent ls`, `agent resume`, `agent --continue`, `agent --resume <chat-id>`.
- Полезно для длинных automation-loop’ов (fix CI, review cycle).

---

## 3) Headless/CI: как правильно использовать CLI

### Золотое правило

- Для CI и скриптов используйте `agent -p ...` + явный `--output-format`.
- Для записи изменений добавляйте `--force`, иначе правки могут быть только предложены.

### Рекомендуемые форматы вывода

- `text`: только финальный ответ (самый простой для человека).
- `json`: единый итоговый JSON-объект (удобен для “один запуск = один результат”).
- `stream-json`: NDJSON события (система/assistant/tool_call/result), идеален для мониторинга прогресса.

### Что парсить в `stream-json`

- `type=system, subtype=init` — старт, модель, cwd, источник API-ключа.
- `type=assistant` — сообщения агента.
- `type=tool_call, subtype=started|completed` — трассировка инструментов.
- `type=result, subtype=success` — финал выполнения.

### Минимальный шаблон запуска в CI

```bash
agent -p --force \
  --output-format stream-json \
  --stream-partial-output \
  "Analyze failing tests and apply minimal fix"
```

---

## 4) Конфигурация CLI (governance и безопасность)

### Файлы конфигурации

- Глобальный: `~/.cursor/cli-config.json`
- Проектный: `<project>/.cursor/cli.json` (только `permissions`)
- Приоритет: проектный для permission-правил, остальное глобально.

### Permission-модель

Поддерживаются токены:

- `Shell(commandBase)` — shell-команды.
- `Read(pathOrGlob)` — чтение.
- `Write(pathOrGlob)` — запись.
- `WebFetch(domainPattern)` — web fetch домены.
- `Mcp(server:tool)` — MCP инструменты.

Принципы:

- `deny` > `allow` (deny-приоритет).
- Глоб и `command:args`-шаблоны поддерживаются.
- Для production CI ограничивайте `Shell(git)`, `Shell(gh)`, чувствительные `Write(...)`.

### Практичный baseline для restricted CI

```json
{
  "permissions": {
    "allow": [
      "Read(**/*.md)",
      "Read(src/**)",
      "Write(docs/**)",
      "Shell(ls)",
      "Shell(jq)",
      "Shell(node:*)"
    ],
    "deny": [
      "Shell(git)",
      "Shell(gh)",
      "Read(.env*)",
      "Write(.env*)",
      "Write(**/*.key)"
    ]
  }
}
```

---

## 5) Sandbox и auto-run политика

### Что важно

- В editor-agent есть sandbox-механика для команд (macOS/Linux, WSL2 для Windows).
- Поведение настраивается `sandbox.json` + UI-политиками (user/team/enterprise).
- Сетевой режим:
  - только `sandbox.json`,
  - `sandbox.json + defaults`,
  - allow all.

### Практика для команд

- По умолчанию держать `Ask Every Time` или `Run in Sandbox`.
- `Run Everything` не использовать для чувствительных репозиториев.
- Явно задать command allowlist + MCP allowlist.

---

## 6) Hooks: контроль агентного цикла

Hooks — самый мощный способ встроить policy enforcement в runtime агента.

### Файлы

- User-level: `~/.cursor/hooks.json`
- Project-level: `<project>/.cursor/hooks.json`

### Что умеют

- Срабатывать до/после стадий agent-loop.
- Получать JSON через stdin и возвращать JSON через stdout.
- Блокировать действия (exit code `2`).
- Работать как command-hook или prompt-hook.

### Где особенно полезно

- Блок опасных shell-команд.
- Аудит tool-вызовов.
- Политики по секретам/PII.
- Авто-форматирование/валидации после edit.
- Телеметрия и SLO мониторинг агентной работы.

### Важные детали

- Fail-open по умолчанию для нештатных exit code (кроме `2`).
- Есть matcher-и для фильтрации таргетных tool/command.
- Поддерживается team/enterprise распределение hook-политик.

---

## 7) Third-party hooks совместимость

Cursor умеет загружать Claude Code hooks:

- Источники `.claude/settings*.json` поддерживаются.
- Есть маппинг событий (`PreToolUse -> preToolUse`, и т.д.).
- Приоритеты Cursor hooks выше, затем Claude hooks.
- Это упрощает миграцию без переписывания всего governance слоя сразу.

---

## 8) MCP интеграция (ключевой слой расширяемости)

### Что дает MCP

- Подключение внешних API/данных как tool calls.
- Поддержка `Tools`, `Prompts`, `Resources`, `Roots`, `Elicitation`.
- Транспорты: `stdio`, `SSE`, `Streamable HTTP` (в desktop/agent).

### Конфигурация

- Проект: `.cursor/mcp.json`
- Глобально: `~/.cursor/mcp.json`
- Интерполяция переменных:
  - `${env:NAME}`, `${workspaceFolder}`, `${userHome}`, и т.д.

### OAuth для remote MCP

- Поддерживается static OAuth (`CLIENT_ID`, `CLIENT_SECRET`, `scopes`).
- Redirect URI фиксированный:  
  `cursor://anysphere.cursor-mcp/oauth/callback`

### Security best practices

- Секреты только через env/interpolation, не хардкодить.
- Для чувствительных систем предпочитать локальный `stdio` или изолированную среду.
- Проводить аудит server-кода MCP перед подключением.

### CLI управление MCP

```bash
agent mcp list
agent mcp list-tools <identifier>
agent mcp login <identifier>
agent mcp enable <identifier>
agent mcp disable <identifier>
```

### Ограничение Cloud Agents API

- Через Cloud Agents API MCP пока не поддержан (ограничение текущей версии API).

---

## 9) Cloud Agents: когда использовать вместо CLI

### Use-cases

- Долгие задачи, не требующие локальной машины.
- Параллельные workstreams.
- PR-driven автоматизация из GitHub/Slack/Linear.
- Нужна изолированная VM с отдельным runtime.

### Важные особенности

- Работают с GitHub/GitLab репозиториями, пушат в ветку/PR.
- Поддерживаются артефакты проверки (скриншоты, видео, логи).
- Авто-фикс CI (GitHub Actions) возможен для PR, созданных агентом.
- Настраиваемая сеть: allow all / default+allowlist / allowlist only.

### Environment setup

- Через onboarding-снапшоты или `.cursor/environment.json` + Dockerfile.
- `install` должен быть идемпотентным.
- `start`/`terminals` для долгоживущих процессов.
- Секреты хранить через dashboard secrets (редактируемые/редактируемые с redaction).

---

## 10) Cloud Agents API: программная оркестрация

### Основные endpoint’ы

- `GET /v0/agents` — список агентов (cursor pagination, `limit`, `prUrl`).
- `GET /v0/agents/{id}` — статус конкретного запуска.
- `GET /v0/agents/{id}/conversation` — история сообщений.
- `POST /v0/agents` — запуск агента.
- `POST /v0/agents/{id}/followup` — follow-up.
- `POST /v0/agents/{id}/stop` — остановка.
- `DELETE /v0/agents/{id}` — удаление.
- `GET /v0/me` — информация об API ключе.
- `GET /v0/models` — рекомендованные модели.
- `GET /v0/repositories` — доступные GitHub репозитории (очень строгий rate limit).

### Практические нюансы

- Для `launch` доступны:
  - `source.repository/ref` или `source.prUrl`,
  - `target.autoCreatePr`, `target.branchName`, `target.autoBranch`, и т.д.
- Поддержаны follow-up с изображениями.
- Есть webhook-конфиг при запуске (`webhook.url`, `webhook.secret`).
- `GET /v0/repositories` лимит: 1/мин и 30/час на пользователя.

### Про auth

- В документации endpoints указан `Basic` формат (`-u API_KEY:`).
- В документации service accounts показан `Authorization: Bearer ...`.
- Для production-интеграции зафиксировать единый способ после smoke-test на вашем tenant.

---

## 11) GitHub / Slack / Linear интеграции

### GitHub

- `@cursor` в PR/issue запускает cloud agent.
- Для org с IP allow list доступен GitHub proxy сценарий.
- Для Bugbot: `@cursor fix` может запускать исправление предложений bugbot.

### Slack

- `@cursor [prompt]` — запуск/фоллоуап.
- `@cursor settings`, `@cursor list my agents`, `@cursor agent ...`.
- Поддержка channel defaults, routing rules, branch/autopr options.

### Linear

- Делегирование issue на Cursor или `@Cursor` в комментарии.
- Конфиг через `[repo=...] [model=...] [branch=...]`.
- Репозиторий выбирается по приоритетам (комментарий -> labels -> project labels -> default).

---

## 12) Rules / Commands / Skills / Subagents: как внедрять в процесс

### Rules

- Хранить в `.cursor/rules` и в git.
- Короткие, scoped, с явными примерами.
- `AGENTS.md` можно использовать как простой легковесный слой инструкций.
- Team Rules (dashboard) дают org-level управление и приоритет.

### Commands

- `.cursor/commands/*.md` для повторяемых workflow-команд.
- Хорошо подходят для “операционных плейбуков” (`/review`, `/run-tests`, `/create-pr`).

### Skills

- Портируемый стандарт расширения агента.
- Директории: `.cursor/skills`, `.agents/skills`, user-level `~/.cursor/skills`.
- Для slash-like поведения: `disable-model-invocation: true`.

### Subagents

- Использовать для тяжелых/параллельных задач с контекстной изоляцией.
- Built-in: `explore`, `bash`, `browser`.
- Кастомные: `.cursor/agents/*.md` (например `verifier`, `security-auditor`, `test-runner`).

---

## 13) Deeplinks как transport для процессов

Подходят для стандартизации on-demand запусков без копипаста:

- Prompt link:
  - `cursor://anysphere.cursor-deeplink/prompt?text=...`
  - web-форма: `https://cursor.com/link/prompt?text=...`
- Command link: `.../command?name=...&text=...`
- Rule link: `.../rule?name=...&text=...`
- MCP install link:
  - `cursor://anysphere.cursor-deeplink/mcp/install?name=$NAME&config=$BASE64_JSON`

Ограничение: длина URL до ~8000 символов.

---

## 14) Ignore-файлы и границы контекста

### `.cursorignore`

- Исключает файлы из semantic search и контекста Agent/Tab/Inline Edit.
- Не блокирует доступ через terminal/MCP инструменты (важно для threat model).

### `.cursorindexingignore`

- Только исключение из индексации (файлы остаются доступными агенту напрямую).

Практика:

- Глобально добавить `.env`, `*.pem`, `credentials.json`, `secrets.json`.
- Плюс permission-deny на `Read(.env*)` и `Write(.env*)` в CLI.

---

## 15) Рекомендуемая стратегия rollout (по этапам)

### Этап 1 — Local baseline

- Включить project `rules`, `AGENTS.md`, минимальный набор `commands`.
- Настроить `cli-config.json` + `permissions`.
- Завести базовый `hooks.json` (аудит + запрет опасных команд).

### Этап 2 — CI automation

- Добавить `agent -p` jobs в GitHub Actions:
  - code-review,
  - docs update,
  - ci-fix.
- Ограничить права через `.cursor/cli.json`.
- Перейти на `stream-json` для машинного мониторинга шагов.

### Этап 3 — External integration

- Подключить GitHub/Slack/Linear.
- Настроить routing rules и channel defaults.
- Добавить service account (Enterprise) для не-человеческой оркестрации.

### Этап 4 — Cloud/API scale

- Внедрить Cloud Agents API orchestrator.
- Включить webhook-пайплайн статусов.
- Прописать egress policy и secret redaction.

---

## 16) Готовые checklists

### A. Безопасный запуск CLI в CI

- [ ] `CURSOR_API_KEY` хранится в secrets.
- [ ] Используется `agent -p` + явный `--output-format`.
- [ ] Для модификаций включен `--force`.
- [ ] Ограничены `permissions` (`deny` на git/gh/secret файлы).
- [ ] Логи парсят `stream-json`, а не только stdout-текст.

### B. Безопасный запуск Cloud Agents

- [ ] Подключен GitHub app с минимально нужными правами.
- [ ] Секреты в dashboard secrets, чувствительные помечены redacted.
- [ ] Ограничен network access mode.
- [ ] Уточнен режим team follow-ups (учесть lateral movement риск).
- [ ] Включен мониторинг egress IP ranges или GitHub proxy для allowlist.

### C. MCP governance

- [ ] MCP серверы из доверенных источников.
- [ ] Секреты только через env/interpolation.
- [ ] Для каждого MCP прописаны allow/deny в CLI permissions.
- [ ] Есть план rollback/disable проблемного MCP.

---

## 17) Основные ограничения и риски (чтобы не забыть)

- CLI в print/headless с `--force` имеет полный write-power — ограничивайте permissions.
- `allowlist`/auto-run — не абсолютная security гарантия.
- Cloud Agents auto-run команды и по умолчанию имеют сеть — это отдельный риск prompt injection/exfiltration.
- `.cursorignore` не блокирует terminal/MCP доступ.
- Некоторые docs показывают отличия по auth-стилю API (Basic vs Bearer) — валидировать на вашем контуре.
- Cloud Agents API пока без MCP.

---

## 18) Минимальный “production-ready” набор артефактов в репо

- `.cursor/rules/*.mdc` — инженерные стандарты.
- `AGENTS.md` — краткие инварианты проекта.
- `.cursor/commands/*.md` — повторяемые процессы.
- `.cursor/cli.json` — project-level permission policies.
- `.cursor/hooks.json` + `.cursor/hooks/*` — runtime-guardrails.
- `.cursor/mcp.json` — интеграции внешних инструментов.
- `.cursor/environment.json` (если используете Cloud Agent custom environment).
- `.cursorignore` и `.cursorindexingignore` — контроль индекса/контекста.

---

## 19) Приоритеты внедрения (что даст максимальный эффект быстро)

1. Включить `agent -p` automation в CI на узком кейсе (например, docs update).
2. Сразу ограничить `permissions` и добавить hooks для критичных команд.
3. Подключить 1-2 MCP интеграции с высоким ROI (например docs/search + issue tracker).
4. Добавить Cloud Agents для долгих задач и PR-циклов.
5. Довести до API orchestration и service accounts (если Enterprise).



Для реализации вашего оркестратора в документации Cursor AI есть три основных пути: использование **Cloud Agents API**, запуск **Headless CLI** и перехват событий через **Hooks**.

Ниже приведен список всех инструментов и API, которые вы можете использовать для управления агентами из своего кода.

---

### 1. Cloud Agents API (Программный запуск в облаке)

Это наиболее подходящий инструмент для вашего оркестратора, если агенты должны работать на удаленных виртуалках.

* **Файл:** `https://cursor.com/docs/cloud-agent/api/endpoints.md`
* **Что применить:**
* **Launch an Agent (`POST /v0/agents`):** запуск нового агента. Можно передать `prompt`, `repository`, `branchName` и `webhook.url`.
* **Agent Status (`GET /v0/agents/{id}`):** получение текущего состояния (RUNNING, FINISHED и т.д.).
* **Agent Conversation (`GET /v0/agents/{id}/conversation`):** получение всей истории сообщений для сохранения состояния.
* **Add Follow-up (`POST /v0/agents/{id}/followup`):** отправка новых инструкций уже запущенному агенту.
* **Webhooks:** API позволяет указать URL для получения уведомлений об изменении статуса агента (в параметрах запуска).
* **List Models (`GET /v0/models`):** получение списка доступных моделей для выбора лучшей в оркестраторе.



### 2. Headless CLI (Управление локальными процессами)

Если оркестратор запускает агентов на вашем железе или в CI/CD.

* **Файлы:** `https://cursor.com/docs/cli/headless.md`, `https://cursor.com/docs/cli/reference/output-format.md`, `https://cursor.com/docs/cli/reference/parameters.md`
* **Что применить:**
* **Print Mode (`--print` или `-p`):** запуск в неинтерактивном режиме.
* **JSON Output (`--output-format json`):** получение итогового результата работы агента в виде чистого JSON.
* **Streaming JSON (`--output-format stream-json`):** идеальный вариант для мониторинга в реальном времени. Выводит NDJSON (каждая строка — событие), включая начало/конец вызова инструментов (`tool_call`).
* **Partial Output (`--stream-partial-output`):** позволяет получать текст ответа по частям (токен за токеном) в стриме JSON.
* **Session Management (`agent ls`, `--resume [id]`, `--continue`):** команды для получения списка сессий и их возобновления, что критично для сохранения стейта.
* **Force/Yolo Mode (`--force`):** автоматическое подтверждение всех действий (записи файлов и выполнения команд), чтобы оркестратор не ждал ввода пользователя.



### 3. Hooks (Глубокий мониторинг и управление циклом)

Скрипты, которые Cursor вызывает сам на разных этапах работы. Это "код внутри кода", который поможет вашему оркестратору следить за "нутром" агента.

* **Файл:** `https://cursor.com/docs/agent/hooks.md`
* **Что применить:**
* **`hooks.json`:** файл конфигурации, где вы прописываете свои скрипты-обработчики.
* **`preToolUse` / `postToolUse`:** получение детальной статистики по использованию инструментов (какие команды запускал, какие файлы читал, сколько времени это заняло).
* **`stop`:** событие завершения цикла. В ответе этого хука можно вернуть `followup_message`, чтобы заставить агента продолжать работу (авто-ретрай или следующая задача).
* **`afterAgentThought`:** получение текста "размышлений" агента (thinking blocks) для логов.
* **`sessionStart` / `sessionEnd`:** логирование начала и конца сессии, передача кастомных переменных окружения (`env`).



### 4. Service Accounts (Enterprise)

Для того чтобы ваш оркестратор имел свои собственные права и не зависел от личных аккаунтов разработчиков.

* **Файл:** `https://cursor.com/docs/account/enterprise/service-accounts.md`
* **Что применить:**
* **API Keys:** создание ключей для программного доступа.
* **Usage Consumption:** отслеживание потребления токенов именно оркестратором.



### 5. Admin & Analytics API (Статистика)

* **Файлы:** `https://cursor.com/docs/account/teams/admin-api.md`, `https://cursor.com/docs/account/teams/analytics.md`
* **Что применить:**
* **Usage Stats:** программное получение данных о том, сколько токенов потратил каждый агент.
* **AI Code Tracking API:** (Enterprise) получение метрик по каждой правке кода, которую сделал агент.



### 6. Deeplinks (Интеграция с UI)

Если ваш оркестратор должен уметь открывать конкретный чат или префиллить промпт в интерфейсе Cursor для человека.

* **Файл:** `https://cursor.com/docs/integrations/deeplinks.md`
* **Что применить:**
* **`cursor://anysphere.cursor-deeplink/prompt?text=...`**: программная генерация ссылок для открытия Cursor с нужным контекстом.



---

**Рекомендация по архитектуре:**
Для максимального контроля используйте **Headless CLI** с флагом `--output-format stream-json`. Это позволит вашему коду (оркестратору) читать `stdout` процесса, парсить каждое действие агента (какой файл он открыл, какую команду в терминале ввел) и мгновенно сохранять это в базу данных для отслеживания прогресса.