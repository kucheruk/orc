# ORC-REL-008

Устранить OS-зависимость и хрупкость в управлении деревом процессов: заменить `pgrep -P` и прямые POSIX-сигналы на кроссплатформенную реализацию через `psutil`.

---

## Комментарий исполнителя

- Что сделали: в `orc_core/process.py` заменили `list_child_pids()` с `subprocess + pgrep` на `psutil.Process(...).children()`, а `kill_process_tree()` переписали на `terminate() -> wait_procs() -> kill()` для потомков и родителя с обработкой `NoSuchProcess`/`ZombieProcess`/`AccessDenied`.
- Что проверили (verifier): успешно выполнены `python -m unittest tests.test_process tests.test_task_execution`; добавлен новый набор тестов `tests/test_process.py` на чтение детей, устойчивость к отсутствующему PID, эскалацию для зависших потомков и завершение родителя после детей.
- Этап shrink: удалена зависимость от внешнего `pgrep` и POSIX-специфичных `signal/os.kill` в process-runtime; уменьшена хрупкость по race-condition в процессе завершения дерева.
- Trade-offs: добавлена новая runtime-зависимость `psutil` (обновлены `pyproject.toml` и `uv.lock`) в обмен на кроссплатформенность и более предсказуемую работу с процессами.
- Вне scope: не меняли политику restarts/TTL и orchestration flow в `task_execution`/`supervisor`; внешние контракты вызова `kill_process_tree(...)` сохранены.
- Риски и фокус для QA: проверить поведение на Linux/macOS/Windows (включая WSL), особенно кейсы `AccessDenied` и быстрые гонки «процесс умер между enumerate и terminate».
- Важно следующему разработчику: для дальнейших изменений process lifecycle опираться на `psutil` API и не возвращаться к shell-утилитам (`pgrep`) в runtime-коде.
