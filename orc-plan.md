# ORC — План правок

## 1. Integrator auto-default: зацикливание при отсутствии action=Done

### Проблема
Integrator agent завершает сессию но не меняет `action` в frontmatter карточки (оставляет `Integrating`). ORC проверяет `_IDENTITY_DEFAULTS` для auto-advance, но integrator не включён в этот словарь. В результате:
1. Integrator завершается → action остаётся `Integrating`
2. Pull system видит карточку в 7_Handoff с action=Integrating → назначает нового integrator
3. Новый integrator завершается → то же самое → бесконечный цикл

### Где наблюдалось
COL-002 в 7_Handoff: integrator запускался минимум 3 раза подряд (complete → assign → launch → complete → assign...), каждый раз тратя токены без прогресса.

### Root cause
`orc_core/kanban_agent_output.py`, словарь `_IDENTITY_DEFAULTS` содержит auto-default для coder, reviewer, tester, но НЕ для integrator:
```python
_IDENTITY_DEFAULTS = {
    "coder": {Action.CODING: Action.REVIEWING},
    "reviewer": {Action.REVIEWING: Action.TESTING},
    "tester": {Action.TESTING: Action.INTEGRATING},
    # integrator отсутствует!
}
```

### Фикс
Добавить integrator в `_IDENTITY_DEFAULTS`:
```python
"integrator": {Action.INTEGRATING: Action.DONE},
```

### Файлы
- `orc_core/kanban_agent_output.py` — добавить строку в `_IDENTITY_DEFAULTS`

### DoD
- [ ] `_IDENTITY_DEFAULTS` содержит `"integrator": {Action.INTEGRATING: Action.DONE}`
- [ ] Карточка в 7_Handoff с action=Integrating после integrator session автоматически получает action=Done
- [ ] Карточка с action=Done в 7_Handoff перемещается в 8_Done (через deferred move или forward move)
- [ ] Integrator НЕ зацикливается — после первой сессии карточка уходит в Done
- [ ] Тест: integrator identity default transition Integrating→Done
- [ ] Все существующие тесты проходят

### Контекст
- Integrator prompt (`prompts/kanban_integrator.txt`) просит агента поставить `action: Done`, но agent может забыть или не изменить frontmatter
- Auto-default — safety net для всех ролей, integrator был пропущен при добавлении
- Forward move `("7_Handoff", Action.DONE) → "8_Done"` уже существует в `_FORWARD_MOVES`
- Deferred move `("7_Handoff", "Done") → STAGE_DONE` тоже существует в `_apply_deferred_moves`
- Проблема только в отсутствии auto-default который триггерит эту цепочку

---

## 2. Orphaned processes: ORC не убивает process tree при shutdown

### Проблема
После дня работы с ORC обнаружено **36 ORC процессов**, **6 agent процессов** и **4 dotnet/roslyn процессов** — все orphaned. Каждый рестарт ORC (через `kill PID`) оставляет:
- `script` wrapper process (если запускался через `script -q /dev/null`)
- `bash` subprocess
- `agent` (cursor) child processes
- `dotnet`/`vbcscompiler` grandchild processes

`kill PID` убивает только Python-процесс ORC, но не process group. Children становятся orphans и продолжают работать, потребляя CPU/RAM.

### Масштаб
За одну рабочую сессию (10+ рестартов) накопилось:
- 36 ORC-related processes (7 инстансов × script+bash+orc)
- 6 agent processes (cursor agent CLI)
- 4 dotnet processes (vbcscompiler, dotnet run)
- Общее потребление: ~50% CPU idle load, ~2GB RAM

### Root cause
1. **Нет process group management**: ORC запускает agents как subprocesses, но при kill ORC children не получают signal
2. **`script` wrapper**: запуск через `script -q /dev/null bash -c 'orc &'` создаёт 3 уровня вложенности, `kill` убивает только leaf
3. **Lock file не помогает**: `acquire_lock` проверяет PID по lockfile, но lockfile содержит PID orc, а не script wrapper. Stale lock удаляется, новый инстанс стартует, но старые agents продолжают работать
4. **ORC orphan sweep ограничен**: `_cleanup_orphan_processes` работает только для worktree-привязанных agent процессов, не для всех children

### Решение: POSIX Process Group (best practice)

Стандартный POSIX подход к supervised process trees — session/process group. Не нужен PID registry, polling, или custom cleanup logic.

#### Принцип
ORC становится **process group leader**. Все child processes (agents, dotnet, compilers) наследуют PGID. Один `os.killpg(pgid, SIGTERM)` убивает ВСЁ дерево — 100% cleanup, zero orphans.

#### 2a. ORC = process group leader
В `cli_app.py:main()` до любой другой работы:
```python
os.setpgrp()  # ORC becomes process group leader
```
Lockfile записывает PGID:
```python
{"pid": os.getpid(), "pgid": os.getpgrp(), "started_at": "..."}
```

#### 2b. Agent processes наследуют group
`subprocess.Popen` по умолчанию наследует PGID parent — ничего менять не нужно. Важно: **НЕ** передавать `start_new_session=True` при запуске agents (иначе они выйдут из группы).

Проверить что `runner.py` и `task_execution.py` не используют `start_new_session=True` или `preexec_fn=os.setsid`.

#### 2c. Graceful shutdown: killpg
В `_shutdown_all()` после join threads:
```python
import signal
os.killpg(os.getpgrp(), signal.SIGTERM)
```

В signal handler для SIGTERM/SIGINT:
```python
signal.signal(signal.SIGTERM, lambda sig, frame: os.killpg(os.getpgrp(), signal.SIGTERM))
```

#### 2d. Stale lock cleanup при startup
В `acquire_lock()`, если stale lock найден:
```python
stale_pgid = data.get("pgid")
if stale_pgid:
    try:
        os.killpg(stale_pgid, signal.SIGKILL)  # kill entire stale tree
    except ProcessLookupError:
        pass  # already dead
```

#### 2e. atexit fallback
```python
import atexit
atexit.register(lambda: os.killpg(os.getpgrp(), signal.SIGTERM))
```
Работает при нормальном exit, sys.exit, необработанные исключения. Не работает при SIGKILL — но SIGKILL не перехватываем по определению.

#### Почему НЕ нужен PID registry
- Process group — kernel-level механизм, не файловый
- `os.killpg` атомарен и race-condition-free
- Не нужно обновлять файл при каждом agent launch/death
- Работает даже если ORC crashed без cleanup (stale lock → killpg при рестарте)

### Файлы
- `orc_core/process.py` — process group management, `acquire_lock` с PGID
- `orc_core/kanban_session_manager.py` — PID registry write при agent launch, cleanup при shutdown
- `orc_core/state_paths.py` — `running_pids_path()` функция
- `orc_core/cli_app.py` — `os.setpgrp()` при старте

### DoD
- [ ] ORC вызывает `os.setpgrp()` при старте (cli_app.py:main)
- [ ] Lock file содержит `pgid` помимо `pid`
- [ ] При stale lock cleanup — `os.killpg(pgid, SIGKILL)` перед удалением lock
- [ ] Agent subprocesses НЕ используют `start_new_session=True` (наследуют PGID)
- [ ] `_shutdown_all()` вызывает `os.killpg(pgid, SIGTERM)` после join threads
- [ ] `atexit.register` + signal handlers для SIGTERM/SIGINT → killpg
- [ ] После kill -9 ORC PID и рестарта: stale lock cleanup убивает весь предыдущий process tree
- [ ] После рестарта ORC: 0 orphaned agent/dotnet processes от предыдущего запуска
- [ ] Тест: verify os.setpgrp() called, verify lockfile contains pgid
- [ ] Все существующие тесты проходят

### Контекст
- `os.setpgrp()` / `os.killpg()` — стандартный POSIX, работает на macOS и Linux
- `psutil` уже в зависимостях — можно использовать как fallback для edge cases
- Process group — kernel-level, не нужен файловый registry, атомарен, race-free
- Текущий orphan sweep в kanban_session_manager (`_cleanup_orphan_processes`) — workaround для отсутствия process group; после фикса можно упростить
- `script` wrapper для TUI — отдельная проблема, но process group решает cleanup даже для script→bash→orc→agent цепочки
- Проверить что `runner.py` не использует `start_new_session=True` — если использует, agents выйдут из group и killpg их не достанет

---

## 3. КРИТИЧЕСКИЙ: код из worktree веток не попадает в main — 9 карточек "Done" без кода

### Проблема
Независимый аудит обнаружил: 9 из 20 карточек в 8_Done не имеют соответствующего кода в main branch. Код был написан, закоммичен в worktree ветки, прошёл review и testing, но НИКОГДА не был cherry-picked/merged в main. При cleanup worktree ORC удалил ветки — коммиты стали unreachable.

### Масштаб ущерба
| Карточка | Код в unreachable commits | Статус восстановления |
|----------|--------------------------|----------------------|
| COL-003 GrafanaCollector | GrafanaCollector.cs, tests (289 lines), resilience tests | Branch restored: `recover/COL-003` |
| COL-004 QlikCollector | QlikCollector.cs (293 lines), QlikRpcClient (236 lines) | Branch restored: `recover/COL-004` |
| ORG-001 OrgSyncService | OrgSyncRunner, tests (228 lines), migrations | Branch restored: `recover/ORG-001` |
| DIAG-001 Diagnostics | Migrations, repositories, search index | Branch restored: `recover/DIAG-001` |
| AUTH-001 Keycloak OIDC | AuthService, AdminRequirement, OidcOptions, tests | Branch restored: `recover/AUTH-001` |
| FE-003 TopBar | Theme toggle, topbar scaffold | Branch restored: `recover/FE-003` |
| FE-004 Charts | MetricApiEndpoints (190 lines), charts.js, ChartCard | Branch restored: `recover/FE-004` |
| BE-004 Seed data | ReferenceCatalogParser (250 lines), SeedService, tests | Branch restored: `recover/BE-004` |
| BE-005 Razor Pages | Admin endpoints, MetricBindingRepository, Auth | Branch restored: `recover/BE-005` |

### Root cause chain
1. **Нет механизма cherry-pick/merge из worktree в main** — ORC integrator prompt говорил "ORC handles merge automatically", но такого кода НЕ БЫЛО. Integrator agent работал в worktree, коммитил там, ставил Done — но код оставался в worktree ветке.

2. **`cleanup_task_worktree` удаляет ветку при Done** — когда карточка достигала Done, ORC удалял worktree directory И git branch (`git branch -D orc/{task_id}`). Коммиты становились unreachable.

3. **Auto-commit в base repo коммитил только card files** (tasks/*.md), не проектные файлы из worktree — потому что проектные файлы физически в другой directory.

4. **Integrator prompt (до фикса) не требовал merge** — промпт говорил "you do NOT perform the merge yourself", вводя агента в заблуждение.

5. **Ни reviewer, ни tester, ни teamlead не проверяли main** — все работали в worktrees и видели код там. Никто не заметил что main пустой.

### Немедленные действия (выполнено)
- [x] Восстановлены 9 веток из unreachable commits (`git branch recover/{card} {sha}`)
- [ ] Cherry-pick/merge каждой ветки в master (требует ручного разрешения конфликтов)
- [ ] Карточки где код не восстанавливается — вернуть из Done в Coding

### Системный фикс (предотвращение)
Нужен механизм merge worktree→main ПЕРЕД удалением worktree. Варианты:

**Вариант A: Integrator делает merge** (текущий подход после фикса промпта)
- Integrator prompt уже обновлён: agent должен `git add -A && commit`
- Но agent работает В worktree, коммит идёт в worktree branch, не в main
- Нужен дополнительный шаг: `git checkout main && git merge orc/{task_id} && git checkout -`

**Вариант B: ORC делает merge в коде** (надёжнее)
- В `kanban_session_manager` или `kanban_agent_output`, после integrator ставит Done:
  ```python
  if new_stage == "8_Done" and worktree:
      run_git(base_workdir, ["git", "merge", worktree.branch_name, "--no-edit"])
  ```
- Merge перед `cleanup_task_worktree`
- При конфликте — не удалять worktree, пометить Blocked

**Вариант C: cleanup_task_worktree НЕ удаляет ветку** (safety net)
- Удалять worktree directory, но НЕ `git branch -D`
- Ветка остаётся, коммиты reachable
- Периодическая GC веток которые уже в main

### Рекомендация
**Вариант B + C**: ORC делает merge в коде (гарантия), плюс не удаляет ветку (safety net). Double protection.

### DoD
- [ ] Все 9 recover/ веток merged в master (или карточки возвращены в pipeline)
- [ ] ORC выполняет `git merge` worktree branch в main перед cleanup
- [ ] `cleanup_task_worktree` НЕ удаляет git branch (только worktree directory)
- [ ] При merge conflict — карточка остаётся в Handoff, не уходит в Done
- [ ] Тест: card Done → worktree code appears in main branch
- [ ] Тест: merge conflict → card stays in Handoff with Blocked action

### Файлы
- `orc_core/kanban_session_manager.py` или `kanban_worker_runner.py` — merge перед cleanup
- `orc_core/worktree_flow.py` — `cleanup_task_worktree` не удаляет branch
- `orc_core/kanban_agent_output.py` — merge trigger при Done transition
