# ADR-0001: Отказ от глобального TUI bus в пользу Textual Message + Worker

## Статус

Принято

## Контекст

В текущей реализации TUI использовался глобальный модуль `orc_core/tui/bus.py` с singleton-состоянием (`_LATEST_SNAPSHOT`) и `threading.Lock()`.
`OrcApp` опрашивал это состояние через таймер `set_interval(0.2, ...)`.

Такой подход создавал архитектурный долг:
- глобальный изменяемый стейт усложняет расширение UI (несколько потоков данных, история, мульти-агентные экраны);
- polling добавляет лишнюю сложность и задержки обновления;
- зависимость на внешний bus ломает локальность границ между `App` и фоновым раннером.

## Решение

Переход на нативную модель Textual:

1. Добавлены сообщения `SnapshotUpdated` и `OrchestratorFinished` в `orc_core/tui/messages.py`.
2. `OrcApp` переведен на worker `@work(thread=True)` вместо ручного `threading.Thread`.
3. Снапшоты передаются в `App` через `post_message(...)` и обрабатываются в `on_snapshot_updated(...)`.
4. Завершение оркестратора и ошибки передаются через `OrchestratorFinished`.
5. `StreamJsonMonitor` больше не знает про глобальный bus: он принимает injected callback `snapshot_publisher`.
6. `snapshot_publisher` прокидывается по цепочке `cli_app -> BacklogOrchestrator -> TaskExecutionRequest -> worker -> runner -> StreamJsonMonitor`.
7. `orc_core/tui/bus.py` удален.

## Последствия

Плюсы:
- убран глобальный mutable state из TUI-потока обновлений;
- push-модель обновлений вместо polling;
- лучшее соответствие архитектуре Textual и проще масштабирование UI;
- явные зависимости (через DI callback), проще тестировать и сопровождать.

Компромиссы:
- расширились сигнатуры в слоях запуска monitor/runner/engine;
- нужно поддерживать контракт callback `snapshot_publisher` в интеграционных тестах.

## Отклоненные альтернативы

1. Оставить `bus.py` как есть и только усилить lock/очередь.
   - Не решает проблему глобального состояния и архитектурной связности.

2. Использовать локальную polling-очередь в `OrcApp`.
   - Убирает singleton, но сохраняет polling и усложняет жизненный цикл.

3. Писать UI напрямую из monitor потока.
   - Риск гонок и нарушение потоковой модели Textual.
