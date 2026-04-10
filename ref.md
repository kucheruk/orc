# ORC Architectural Audit — Full Context Reference

> **Дата:** 2026-04-10  
> **Автор:** AI Architect (Uncle Bob style)  
> **Цель:** передать следующему агенту полный контекст для принятия решений о рефакторинге

---

## 1. ЧТО ТАКОЕ ORC

ORC — Python-оркестратор для AI-агентов. Управляет параллельными worker'ами (до 4), каждый из которых выполняет задачи на 8-колоночной канбан-доске. Workers — это внешние CLI-процессы (Cursor Agent, Claude Code, Codex), которые ORC запускает как subprocess'ы, мониторит их JSON-стрим, детектит завершение, коммитит результат и интегрирует в main через cherry-pick.

### Ключевые характеристики
- **~12 920 LOC** в `orc_core/` (60+ модулей), **39 тестовых файлов**
- Python 3.12+, зависимости: `textual` (TUI), `rich`, `psutil`, `pyyaml`, `markdown-it-py`
- Entry points: `orc` (1 worker) и `orcs` (4 workers), определены в `pyproject.toml:19-21`
- TUI на Textual с канбан-доской, панелью сессий, model picker'ом

### Flow выполнения задачи
```
KanbanSessionManager.run_async()          # orchestration loop
  → KanbanDistributor.try_assign()        # pull-based work distribution
    → kanban_pull.find_next_work()        # right-to-left board scan
  → _execute_assignment()                 # launch worker thread
    → build_kanban_request()              # construct TaskExecutionRequest
    → TaskExecutionEngine.execute()       # main execution
      → _execute_inner()                  # THE GOD FUNCTION (285+ lines)
        → worker.launch()                 # spawn agent subprocess
        → wait_for_completion()           # 383-line supervision loop
        → _run_commit_phase()             # commit agent's changes
        → integrate_commit_into_main()    # cherry-pick to main
```

---

## 2. АРХИТЕКТУРА — СЛОИ И ЗАВИСИМОСТИ

### Граф зависимостей (верифицирован AST-парсингом)

**Циклических зависимостей НЕТ.** Граф — чистый DAG из 8 уровней.

Ключевые цепочки (→ = "зависит от"):
```
cli_app → kanban_session_manager → task_execution → supervisor_lifecycle → logging
                                 → kanban_distributor → kanban_pull → kanban_constants
                                 → integration_manager → worktree_flow → state_paths
                                 → kanban_incident_manager → teamlead_actions
```

### Самые "тяжёлые" модули по импортам

| Модуль | LOC | Кол-во внутренних импортов |
|--------|-----|---------------------------|
| `kanban_session_manager.py` | 991 | 21 модуль (!) |
| `task_execution.py` | 1785 | 18 модулей |
| `cli_app.py` | 269 | 16 модулей |
| `stream_monitor.py` | 626 | 8 модулей |
| `integration_manager.py` | 465 | 7 модулей |

### Полный размер модулей (top-20)
```
1785  task_execution.py          ← GOD MODULE
1040  stream_monitor_state.py    ← GOD CLASS (53 methods)
 991  kanban_session_manager.py  ← GOD OBJECT (43 methods)
 644  supervisor_lifecycle.py    ← GOD FUNCTION (383 lines)
 626  stream_monitor.py
 547  logging.py
 506  kanban_board.py
 465  integration_manager.py
 432  worktree_flow.py
 392  kanban_incident_manager.py
 320  teamlead_actions.py
 308  kanban_roles.py
 269  cli_app.py
 268  process.py
 236  task_state.py
 222  kanban_agent_output.py
 192  role_config.py
 181  text_parse.py
 180  runner.py
 170  state_paths.py
```

---

## 3. ПЯТЬ АРХИТЕКТУРНЫХ ГРЕХОВ

### Грех #1: God Functions — SRP на уровне метода (CRITICAL)

#### 3.1.1 `task_execution.py:716` — `_execute_inner()` (285+ строк + nested closures)

Это метод класса `TaskExecutionEngine`. Получает `TaskExecutionRequest` (frozen dataclass, строка 98) и возвращает `TaskExecutionResult` (строка 123).

**Что делает (в порядке выполнения):**

1. **Строки 716-738:** Инициализация — разрешение путей, env vars, лог-путей
2. **Строки 739-786:** Preflight git checks — вызов `preflight_main_integration()` из `worktree_flow`, классификация ошибок через `classify_main_integration_error()` из `git_helpers`
3. **Строки 787-789:** Определение resume state — проверка `request.task_path.exists()`
4. **Строки 791-1031:** Nested closure `_finalize_completed()` (240 строк!) — включает:
   - Summary extraction и normalization (строки 794-801)
   - Stats recording (строки 807-813)
   - Commit phase orchestration (строки 830-856)
   - Main integration через cherry-pick (строки 858-953)
   - Backlog sync validation (строки 954-1024)
   - Task state cleanup (строки 1025-1031)
5. **Строки 1033-1133:** Resume detection — чтение task file, проверка conversation_id, backlog mismatch, stale done tasks
6. **Строки 1134-1173:** Fresh task setup — write_task_file, enrich с worktree metadata, save_active_session
7. **Строки 1175-1183:** Stage specs initialization
8. **Строки 1185-1239:** Ещё одна nested closure `_complete_stage()` (55 строк) — artifact validation, SDLC feedback loops

**Контекст для рефакторинга:**
- `_finalize_completed` использует `nonlocal` переменные из `_execute_inner` scope: `restart_count`, `effective_agent_output_log_path`, `timeline_id`, `ts_exec`, `runtime_backlog_path`, `base_backlog_path`
- `_complete_stage` использует `nonlocal feedback_iteration_count` и closured `stage_specs`, `artifact_bundle`, `enforce_stage_artifacts`, `implementation_stage_index`
- Весь метод обёрнут в `timeline_step` context manager (строка 707)
- `self.worker` и `self.log_path` — единственные поля `TaskExecutionEngine`

**Паттерн для извлечения:**
```python
# Текущая структура класса (строки 698-703):
class TaskExecutionEngine:
    def __init__(self, *, worker=None, log_path, backend=None):
        self.worker = worker or AgentTaskWorker(backend=backend)
        self.log_path = log_path
    
    def execute(self, request) -> TaskExecutionResult:  # строка 704
        return self._execute_inner(request, task_id, timeline_id, ts_exec)
```

#### 3.1.2 `supervisor_lifecycle.py:113` — `wait_for_completion()` (383 строки)

**Сигнатура (15 параметров):**
```python
def wait_for_completion(
    task_path: Path,          # файл состояния задачи
    monitor,                  # StreamMonitor object (untyped!)
    poll: float,              # интервал поллинга
    stall_timeout: float,     # таймаут тишины
    task_ttl: float,          # макс. время задачи
    log_path: Path,           # лог-файл
    nudge_after: int,         # (не используется в теле!)
    nudge_cooldown: float,    # (не используется в теле!)
    nudge_text: str,          # (не используется в теле!)
    task_id: str,             # ID задачи
    task_text: str,           # текст задачи (для Telegram)
    timeline_id: str = "",
    attempt: int = 0,
    elapsed_before_start: float = 0.0,
    ignore_initial_backlog_done: bool = False,
    escape_requested: Optional[Callable] = None,
    confirm_exit: Optional[Callable] = None,
) -> str:  # Возвращает СТРОКУ: "completed"|"stalled"|"ttl_exceeded"|"process_exited"|"waiting_for_input"|"model_unavailable"
```

**Локальные переменные состояния (строки 132-138):**
```python
start_time = time.time()
pid_missing_since: Optional[float] = None
last_heartbeat_time = 0.0
last_tokens_value: Optional[int] = None
last_tokens_time = time.time()
last_stuck_notice_time = 0.0
backlog_done_at_start = _task_done_in_backlog(task_path)
```

**Смешанные ответственности в while-цикле (строки 168-493):**
1. **Escape/interrupt handling** (строки 169-182)
2. **Task file removal detection** (строки 183-200)
3. **PID missing detection** с grace period (строки 201-238)
4. **Backlog done + idle detection** (строки 242-263)
5. **Report triggering** (строки 264-275)
6. **Token stall detection** + Telegram notification (строки 276-293)
7. **Stream result_status check** (строки 294-296)
8. **Process exit handling** с grace window (строки 298-397) — самый большой блок, 100 строк
9. **UI followup prompt detection** (строки 398-408)
10. **Output stall detection** с tool digestion grace (строки 409-473)
11. **TTL enforcement** (строки 474-492)
12. **Sleep** (строка 493)

**Возвращаемые строки (stringly-typed):**
- `"completed"` — 6 разных return путей
- `"process_exited"` — 2 пути
- `"stalled"` — 1 путь
- `"ttl_exceeded"` — 1 путь
- `"waiting_for_input"` — 1 путь
- `"model_unavailable"` — 1 путь
- Также может raise `KeyboardInterrupt`

#### 3.1.3 `stream_monitor_state.py:115` — `StreamMonitorState` (1040 строк, 53 метода)

**Инициализация (строки 138-167):** 30 instance переменных, включая:
```python
self.metrics = MetricsStore()           # dataclass с 11 полями
self._line_buffer: Deque[str]           # последние N строк вывода
self._recent_commands: Deque[str]       # последние 8 команд
self._recent_files: Deque[str]          # последние 10 файлов
self._recent_events: Deque[str]         # последние 8 событий
self._recent_reasoning: Deque[str]      # последние 12 строк reasoning
self._reasoning_buffer = ""             # буфер незавершённого reasoning
self._active_tool_calls: dict           # текущие tool calls
self._max_tokens_by_request: dict       # макс. токены по запросам
```

**Группы методов (неявные ответственности):**
- JSON event routing: `process_event()`, `process_line()`
- Token extraction: `_extract_token_metric()`, `_extract_structured_token_entries()`, `_extract_raw_token_line()`
- File tracking: `_record_file_event()`
- Command tracking: `_record_command()`
- Tool call lifecycle: `_handle_tool_use_begin()`, `_handle_tool_use_end()`, `active_tool_calls_watchdog_snapshot()`
- Progress tracking: `set_progress()`, `_compute_eta()`
- Reasoning buffer: `_extract_reasoning_text_fragment()`, `_handle_reasoning_content()`
- Live status: `_update_live_status_for_network_event()`, `_update_live_status_from_event()`
- Snapshot building: `build_snapshot()`

---

### Грех #2: God Object — SRP на уровне класса (HIGH)

#### `kanban_session_manager.py:65` — `KanbanSessionManager`

**Конструктор (строки 68-135) принимает 12 параметров и создаёт:**
```python
self._distributor = KanbanDistributor(tasks_dir)          # pull-based work
self._integrator = IntegrationManager(...)                 # git integration
self._slots: dict[str, SessionSlot] = {}                   # worker threads
self._slots_lock = threading.Lock()                        # thread safety
self._worktree_lock = threading.Lock()                     # worktree safety
self._incident_mgr = IncidentManager(...)                  # incident handling
self.publisher = KanbanPublisher()                         # TUI notifications
self._session_snapshots: dict[str, MonitorSnapshot] = {}   # live worker state
self._card_fail_counts: dict[str, int] = {}                # failure tracking
self._arbitrated_at_loop: dict[str, int] = {}              # arbitration history
```

**6 ответственностей:**
1. **Worker lifecycle** — `_launch_slot_thread()`, `_add_slot()`, `request_add_session()`, `request_remove_session()`
2. **Task assignment** — `_execute_assignment()` (87 строк, строка 428), вызывает `build_kanban_request()` и `engine.execute()`
3. **Role dispatch** — `_run_worker()`, `_run_teamlead()`, `_run_merge_expert()` — каждый по 50-70 строк
4. **Board state** — `_load_kanban_state()`, `_save_kanban_state()`, `_flush_state_if_dirty()`, `_mark_state_dirty()`
5. **Incident handling** — `_teamlead_arbitrate()` (71 строк), делегирует в `IncidentManager`
6. **Git operations** — прямые git-вызовы для проверки tasks/ в git status

**Импорты (21 модуль):**
```python
from .backend import Backend, get_backend
from .integration_manager import IntegrationManager
from .kanban_incident_manager import IncidentManager
from .kanban_agent_output import process_agent_result
from .kanban_card import KanbanCard, new_card_body
from .kanban_distributor import KanbanDistributor
from .kanban_constants import STAGE_DONE, STAGE_INBOX, STAGE_SHORT_NAMES, Action
from .kanban_pull import ROLE_INTEGRATOR, WorkAssignment
from .kanban_publisher import KanbanPublisher
from .kanban_request_builder import build_kanban_request
from .notify import send_telegram_message
from .kanban_roles import ROLE_TEAMLEAD, build_prompt, build_teamlead_prompt
from .teamlead_incident import Incident
from .logging import log_event
from .quit_signal import is_quit_after_task_requested, is_session_stop_requested, is_stop_requested
from .session_types import ...
from .stream_monitor_state import MonitorSnapshot
from .task_execution import TaskExecutionEngine
from .task_source import Task
from .worktree_flow import WorktreeSession, cleanup_task_worktree, create_task_worktree
```

---

### Грех #3: Stringly-Typed Domain (HIGH)

#### 3.3.1 Task completion status — голые строки

`wait_for_completion()` возвращает строки, которые потребляются в `_execute_inner()`. Полный набор значений:

```python
# supervisor_lifecycle.py — возвращает:
"completed"           # 6 путей
"process_exited"      # 2 пути  
"stalled"             # 1 путь
"ttl_exceeded"        # 1 путь
"waiting_for_input"   # 1 путь
"model_unavailable"   # 1 путь

# task_execution.py:206-210 — потребляет для restart reason:
RESTART_REASON_TEXT = {
    "stalled": "Ты перестал выдавать результат...",
    "ttl_exceeded": "Ты превысил лимит времени...",
    "process_exited": "Твой процесс неожиданно завершился...",
}

# TaskExecutionResult.status (строка 124-128):
"completed" | "failed" | "continue"  # тоже строки
```

#### 3.3.2 Error classification через парсинг текста

**Производитель** — `worktree_flow.py` создаёт `IntegrationPreflightResult` с `error: str`:
```python
# worktree_flow.py (строки в preflight_main_integration):
return IntegrationPreflightResult(ok=False, error=f"dirty before integration: {summary}")
return IntegrationPreflightResult(ok=False, error=f"git status failed in {workdir}")
```

**Потребитель** — `git_helpers.py:159-175`:
```python
def classify_main_integration_error(error: str) -> str:
    text = (error or "").strip().lower()
    if "dirty before integration" in text:     return "dirty_base_repo"
    if text.startswith("git status failed"):   return "git_status_failed"
    if "main branch" in text and "not found":  return "main_branch_missing"
    if text.startswith("checkout"):            return "checkout_failed"
    if "timeout" in text:                      return "git_timeout"
    if "cherry-pick" in text:                  return "cherry_pick_failed"
    return "unknown"
```

Изменение текста ошибки в `worktree_flow.py` **молча** ломает классификацию.

#### 3.3.3 Hardcoded workflow в `kanban_pull.py:44-100`

```python
def find_next_work(board) -> Optional[WorkAssignment]:
    _auto_promote_estimate(board)
    # 1. Handoff → Integrating
    result = _try_stage(board, STAGE_HANDOFF, Action.INTEGRATING, ROLE_INTEGRATOR, worktree=True)
    if result: return result
    # 2. Testing
    result = _try_stage_with_forward_wip(board, STAGE_TESTING, Action.TESTING, ROLE_TESTER, STAGE_HANDOFF)
    if result: return result
    result = _try_stage(board, STAGE_TESTING, Action.CODING, ROLE_CODER, worktree=True)
    if result: return result
    # 3. Review
    result = _try_stage_with_forward_wip(board, STAGE_REVIEW, Action.REVIEWING, ROLE_REVIEWER, STAGE_TESTING)
    if result: return result
    result = _try_stage(board, STAGE_REVIEW, Action.CODING, ROLE_CODER, worktree=True)
    if result: return result
    # 4. Coding
    result = _try_stage(board, STAGE_CODING, Action.CODING, ROLE_CODER, worktree=True)
    if result: return result
    # 5. Todo → Pull to Coding
    if board.has_wip_room(STAGE_CODING):
        card = board.pick_best(STAGE_TODO, Action.CODING)
        if card:
            board.move_card(card, STAGE_CODING, reason="pull: backlog ready")
            return WorkAssignment(card=card, role=ROLE_CODER, needs_worktree=True)
    # 6. Estimate, 7. Inbox...
```

Каждый этап — if/return блок. Нет таблицы маршрутизации, нет data-driven подхода.

**Стадии определены в `kanban_constants.py:9-18`:**
```python
STAGES = ("1_Inbox", "2_Estimate", "3_Todo", "4_Coding", "5_Review", "6_Testing", "7_Handoff", "8_Done")
```

**Action — уже StrEnum** (хорошо):
```python
class Action(StrEnum):
    PRODUCT = "Product"
    ARCHITECT = "Architect"
    CODING = "Coding"
    REVIEWING = "Reviewing"
    TESTING = "Testing"
    INTEGRATING = "Integrating"
    ARBITRATION = "Arbitration"
    BLOCKED = "Blocked"
    DONE = "Done"
```

---

### Грех #4: DRY Violations — тройное дублирование (MEDIUM)

#### 3.4.1 `_parse_git_porcelain` — 3 реализации

**Каноническая** — `git_helpers.py:42-51`:
```python
def parse_git_porcelain(porcelain: str) -> tuple[list[str], list[str]]:
    lines = [ln.rstrip("\n") for ln in (porcelain or "").splitlines() if ln.strip()]
    tracked, untracked = [], []
    for ln in lines:
        if ln.startswith("?? "):
            untracked.append(ln)       # ← возвращает ПОЛНУЮ строку "?? path"
        else:
            tracked.append(ln)         # ← возвращает ПОЛНУЮ строку "M  path"
    return tracked, untracked
```

**Копия 1** — `worktree_flow.py:79-94`:
```python
def _parse_git_porcelain(porcelain: str) -> tuple[list[str], list[str]]:
    tracked, untracked = [], []
    for raw_line in porcelain.splitlines():
        line = raw_line.rstrip("\n")
        if len(line) < 4: continue
        status = line[:2]
        path = line[3:].strip()
        if not path: continue
        if status == "??":
            untracked.append(path)     # ← возвращает ТОЛЬКО путь (без "?? ")
        else:
            tracked.append(path)       # ← возвращает ТОЛЬКО путь (без "M  ")
    return tracked, untracked
```

**Копия 2** — `task_execution.py:559-570`:
```python
def _parse_git_porcelain(porcelain: str) -> tuple[list[str], list[str]]:
    tracked, untracked = [], []
    for line in porcelain.splitlines():
        if not line.strip(): continue
        if line.startswith("??"):
            untracked.append(line[3:].strip())  # ← ТОЛЬКО путь
        else:
            tracked.append(line[3:].strip())    # ← ТОЛЬКО путь
    return tracked, untracked
```

**КРИТИЧЕСКОЕ РАЗЛИЧИЕ:** `git_helpers.py` возвращает полные строки с status prefix, а две другие — только пути. Это НЕ баг, а **расхождение API**. `runtime_artifact_paths_from_porcelain_lines` в `git_helpers.py:54` ожидает полные строки (`ln[3:]` для извлечения пути), а аналог в `task_execution.py:573` ожидает голые пути.

**Вывод:** при объединении нужно выбрать один формат возврата и обновить все call sites.

#### 3.4.2 Runtime artifact classification — 3 версии с разными критериями

**`git_helpers.py:54-68`** — для основного git status:
```python
# Считает runtime артефактом:
path.startswith(".orc/")
path == ".cursor/orc-task-runtime.json"
path == ".cursor/orc-task.json"
path == ".cursor/orc-stop-request.json"
```

**`task_execution.py:573-587`** — для commit phase post-check:
```python
# Считает runtime артефактом:
"__pycache__" in p or p.endswith(".pyc")    # ← ТОЛЬКО ЗДЕСЬ
p == "nohup.out"                             # ← ТОЛЬКО ЗДЕСЬ
"/.orc/" in p or p.startswith(".orc/")
"/.cursor/" in p or p.startswith(".cursor/") # ← ВСЕ .cursor файлы, не только конкретные
```

**`worktree_flow.py:14-21,97-103`** — для integration preflight:
```python
INTEGRATION_SAFE_UNTRACKED_PREFIXES = (".orc/",)
INTEGRATION_SAFE_UNTRACKED_EXACT = {
    ".cursor/hooks.json",
    ".cursor/hooks/orc_before_submit.py",
    ".cursor/hooks/orc_hook_lib.py",
    ".cursor/hooks/orc_stop.py",
    ".cursor/orc-stop-request.json",
}
```

**Реальная проблема:** три набора с разными критериями означают, что один и тот же файл может считаться "безопасным" в одном контексте и "реальным изменением" в другом.

---

### Грех #5: Exception Anarchy (MEDIUM)

#### Распределение `except Exception` по файлам:
```
task_execution.py:        19 блоков
stream_monitor.py:        13 блоков
kanban_session_manager.py: 10 блоков
supervisor_lifecycle.py:    8 блоков
task_state.py:              7 блоков
logging.py:                 7 блоков
process.py:                 5 блоков
kanban_board.py:            5 блоков
hooks.py:                   3 блока
```
**Итого: 89 блоков `except Exception` в core.**

#### Типичные паттерны:

**Silent swallow** (самое опасное):
```python
# supervisor_lifecycle.py:216
try:
    task_path.unlink()
    delete_runtime_state_file(task_path, log_path, reason="pid_missing_task_done")
except Exception:
    pass  # ← файл мог не удалиться, но мы этого не узнаем
```

**Partial logging** (лучше, но всё равно ловит слишком широко):
```python
# kanban_session_manager.py:150
except Exception as exc:
    _logger.warning("Failed to load kanban state: %s", exc)
```

**Кастомных типов — ВСЕГО 2:**
- `AgentNotInstalledError(RuntimeError)` в `agent_preflight.py`
- Implicit `ModelSelectionError` (не определён формально)

---

## 4. ЧТО СДЕЛАНО ПРАВИЛЬНО (важно не потерять при рефакторинге)

### 4.1 Protocol-based Backend abstraction
`backend.py:10-37` — `@runtime_checkable class Backend(Protocol)` с 8 методами. Три реализации: `CursorBackend`, `ClaudeBackend`, `CodexBackend`. Тесты проверяют `assertIsInstance(CursorBackend(), Backend)`.

### 4.2 Frozen dataclasses для конфигов
```python
TaskStageSpec(frozen=True)      # task_execution.py:60
TimingConfig(frozen=True)       # task_execution.py:67
ModelConfig(frozen=True)        # task_execution.py:82
TemplateConfig(frozen=True)     # task_execution.py:89
TaskExecutionRequest(frozen=True) # task_execution.py:97
TaskExecutionResult(frozen=True)  # task_execution.py:123
WorkAssignment(frozen=True)       # kanban_pull.py:37
IntegrationResult(frozen=True)    # worktree_flow.py:34
IntegrationPreflightResult(frozen=True) # worktree_flow.py:41
MonitorSnapshot(frozen=True)      # stream_monitor_state.py:31
MetricsStore                      # stream_monitor_state.py:16 (НЕ frozen — мутабельный)
```

### 4.3 Thread safety
- `kanban_board.py` — `self._lock = threading.RLock()` для card operations
- `kanban_session_manager.py` — `self._slots_lock`, `self._worktree_lock`, `self._directive_lock`
- `kanban_distributor.py` — `self._lock` для thread-safe assignment

### 4.4 Atomic I/O
`atomic_io.py` — `write_json_atomic()` и `write_text_atomic()` через temp file + rename

### 4.5 Clean module naming
Файлы называются по ответственности: `kanban_board`, `stream_monitor`, `git_helpers`, `worktree_flow`

### 4.6 Pull-based work distribution
`kanban_pull.py` — right-to-left scan — correct Lean/Kanban practice

---

## 5. RACE CONDITIONS и CONCURRENCY ISSUES

### 5.1 Stats file TOCTOU
`task_execution.py:216-260` — `_update_completion_stats()`:
```python
stats = json.loads(stats_file.read_text()) if stats_file.exists() else {}
# ... modify stats dict ...
write_json_atomic(stats_file, stats)
```
При параллельном завершении задач: read A → read B → write A → write B (B перезаписывает A).

### 5.2 KanbanBoard refresh
`kanban_board.py` — `refresh()` сбрасывает `self._cards = []` и перестраивает. Читатели могут видеть пустой список между clear и rebuild. RLock защищает, но код вне lock может кешировать ссылку.

---

## 6. HARDCODED PATHS и MAGIC STRINGS

### Directory names (разбросаны по 10+ файлам):
```python
".orc/"                    # logging.py:37, git_helpers.py:60, task_execution.py:582, worktree_flow.py:14
".cursor/"                 # git_helpers.py:62-64, task_execution.py:583, worktree_flow.py:15-20, hooks.py
"tasks/"                   # kanban_constants.py:86, kanban_roles.py, kanban_session_manager.py
"_board"                   # task_execution.py:955 — sentinel backlog path name
"_index.md"                # kanban_constants.py:85
```

### Timeout constants (разные в каждом модуле):
```python
GIT_COMMAND_TIMEOUT_SECONDS = 20.0    # git_helpers.py:10
GIT_TIMEOUT_SECONDS = 30.0           # worktree_flow.py:13
GIT_STATS_TIMEOUT_SECONDS = 10.0     # stream_monitor.py (approx)
PROCESS_EXIT_GRACE_SECONDS = 3.0     # supervisor_lifecycle.py:17
DONE_BACKLOG_IDLE_GRACE_SECONDS = 20.0 # supervisor_lifecycle.py:18
PID_MISSING_GRACE_SECONDS = 1.0      # supervisor_lifecycle.py:19
TOOL_DIGESTION_GRACE_SECONDS = 180.0  # supervisor_lifecycle.py:20
TOKENS_STUCK_NOTICE_SECONDS = 15*60   # supervisor_lifecycle.py:21
```

---

## 7. ТЕСТОВАЯ ИНФРАСТРУКТУРА

### Тестовые файлы (39 штук):
```
tests/test_task_execution.py              # использует _FakeWorker, _FakeMonitor
tests/test_task_execution_resume.py
tests/test_task_execution_worktree_state.py
tests/test_task_execution_process_cleanup.py
tests/test_kanban_board.py
tests/test_kanban_card.py
tests/test_kanban_pull.py
tests/test_kanban_roles.py
tests/test_kanban_snapshot.py
tests/test_kanban_session_integration.py
tests/test_backend_protocol.py            # assertIsInstance проверки
tests/test_backend_cursor.py
tests/test_backend_claude.py
tests/test_backend_codex.py
tests/test_supervisor_lifecycle.py
tests/test_supervisor_lifecycle_process_exit.py
tests/test_stream_monitor.py
tests/test_integration_manager.py
tests/test_worktree_flow.py
tests/test_hooks.py
tests/test_role_config.py
tests/test_model_selector.py
tests/test_cli_app.py
tests/test_process.py
tests/test_notify.py
tests/test_logging.py
tests/test_atomic_io.py
tests/test_task_state.py
tests/test_task_contract.py
tests/test_task_source.py
tests/test_gitignore_guard.py
tests/test_tui_app.py
tests/test_teamlead_incident.py
tests/conftest.py
```

### Test doubles:
- `_FakeWorker` — подменяет `TaskWorker` Protocol
- `_FakeMonitor` — подменяет `StreamMonitor`
- `_FakeMetrics` — подменяет `MetricsStore`

### Проблемы тестируемости:
- `logging.py:27-34` — 8 глобальных мутабельных переменных, нет reset
- `subprocess.run()` вызывается напрямую в 6 файлах без инъекции
- Тесты `task_execution` требуют реальную FS + git repo (через tmpdir fixtures)

---

## 8. KEY PROTOCOLS AND INTERFACES

### `Backend` Protocol (`backend.py:10-37`):
```python
@runtime_checkable
class Backend(Protocol):
    name: str                    # property
    cli_binary: str              # property
    ensure_installed() -> None
    build_agent_cmd(*, model, prompt, resume_id, resume_latest, resume_prompt) -> list[str]
    setup_hooks(workdir, log_path) -> None
    get_resume_id(workdir, log_path) -> str | None
    default_model() -> str
    list_models_cmd() -> list[str] | None
```

### `TaskWorker` Protocol (`task_execution.py:131-154`):
```python
class TaskWorker(Protocol):
    def launch(self, *, workdir, prompt_path, model, log_path,
               report_interval, summary_lines, task_id,
               progress_done, progress_total, progress_in_progress,
               agent_output_log_path, agent_env, snapshot_publisher,
               resume_id, resume_latest, resume_prompt,
               timeline_id, attempt): ...
```

### `TaskSource` Protocol (`task_source.py`):
```python
class TaskSource(Protocol):
    def list_tasks() -> List[Task]
    def get_open_tasks() -> List[Task]
    def get_first_open_task() -> Optional[Task]
    def get_task_by_id(task_id) -> Optional[Task]
    def is_task_done(task_id) -> bool
    def mark_task_done(task_id) -> bool
```

---

## 9. РЕКОМЕНДУЕМАЯ ПОСЛЕДОВАТЕЛЬНОСТЬ РЕФАКТОРИНГА

### Фаза 1: Quick wins (1-2 дня)

1. **Создать `TaskCompletionStatus` enum** — заменить строки `"completed"`, `"stalled"`, `"ttl_exceeded"`, `"process_exited"`, `"waiting_for_input"`, `"model_unavailable"` в `supervisor_lifecycle.py` и всех call sites
2. **Создать `IntegrationErrorKind` enum** — заменить `classify_main_integration_error()` на типизированный return + убрать парсинг строк
3. **Удалить дубли `_parse_git_porcelain`** из `worktree_flow.py:79` и `task_execution.py:559`, использовать `git_helpers.parse_git_porcelain`. Нужно выбрать формат (полные строки vs голые пути) и обновить call sites

### Фаза 2: Средние рефакторинги (3-5 дней)

4. **Извлечь фазы из `_execute_inner()`** — каждая фаза в отдельный метод или класс:
   - `_preflight_integration()` → строки 739-786
   - `_resolve_resume_state()` → строки 1040-1133
   - `_setup_fresh_task()` → строки 1134-1173
   - `_finalize_completed()` → уже closure, сделать методом
   - `_complete_stage()` → уже closure, сделать методом
5. **Разбить `StreamMonitorState`** на 3-4 класса:
   - `TokenExtractor` (token parsing logic)
   - `ToolCallTracker` (active tool call state machine)
   - `LiveStatusComputer` (phase/status derivation)
   - `MonitorSnapshotBuilder` (snapshot composition)

### Фаза 3: Крупные рефакторинги (5-7 дней)

6. **Декомпозиция `KanbanSessionManager`**:
   - `WorkerPool` — thread lifecycle, slot management
   - `TaskRouter` — role dispatch, assignment
   - `KanbanStateStore` — persistence, dirty tracking
   - `KanbanSessionManager` — тонкий фасад
7. **Refactor `wait_for_completion()`** в state machine:
   - States: `Watching`, `PidMissing`, `ProcessExited`, `BacklogDone`, `Stalled`, `TtlExceeded`
   - Transitions вместо 383-строчного if/elif в while
8. **Иерархия исключений**: `OrcError` → `GitOperationError`, `TaskExecutionError`, `WorktreeError`, `IntegrationError`

### Фаза 4: Ongoing

9. Заменять `except Exception` на конкретные типы — начать с `supervisor_lifecycle.py` (8 блоков) и `task_execution.py` (19 блоков)
10. Унифицировать runtime artifact classification в один модуль
11. Protocol abstractions для subprocess (testability)

---

## 10. ФАЙЛЫ, КОТОРЫЕ НУЖНО БУДЕТ МЕНЯТЬ

| Файл | Что менять | Грех |
|------|-----------|------|
| `orc_core/task_execution.py` | Извлечь фазы из `_execute_inner`, удалить дубли git parsing, enum'ы для status | #1, #3, #4 |
| `orc_core/supervisor_lifecycle.py` | State machine вместо while loop, enum для return status | #1, #3 |
| `orc_core/stream_monitor_state.py` | Разбить на 3-4 класса | #1 |
| `orc_core/kanban_session_manager.py` | Декомпозиция на 3-4 класса | #2 |
| `orc_core/git_helpers.py` | Enum для error kinds, каноническая git porcelain parse | #3, #4 |
| `orc_core/worktree_flow.py` | Удалить дубль `_parse_git_porcelain`, типизировать ошибки | #3, #4 |
| `orc_core/kanban_pull.py` | Data-driven workflow sequence (опционально) | #3 |
| `orc_core/kanban_constants.py` | Новые enum'ы (если не в отдельном файле) | #3 |

---

## 11. КРИТИЧЕСКИЕ ИНВАРИАНТЫ (не нарушать при рефакторинге)

1. **Thread safety:** `_slots_lock` защищает `_slots` dict, `_worktree_lock` защищает worktree create/cleanup — оба НЕОБХОДИМЫ
2. **Atomic I/O:** все записи state файлов через `write_json_atomic` — сохранить
3. **Timeline context managers:** `timeline_step()` и `timeline_instant()` — система трассировки, не удалять
4. **Pull semantics:** right-to-left scan — это не баг, а kanban best practice
5. **Worktree isolation:** каждая задача работает в отдельном git worktree — это core design decision
6. **`_board` sentinel:** когда `base_backlog_path.name == "_board"` — это kanban mode, backlog invariant не проверяется (строка 955)
7. **Resume logic:** task file с `conversation_id` позволяет продолжить прерванную сессию агента
8. **Hook isolation:** `orc_hook_lib.py` — standalone копия для subprocess'ов Cursor, не может импортировать из `orc_core`
