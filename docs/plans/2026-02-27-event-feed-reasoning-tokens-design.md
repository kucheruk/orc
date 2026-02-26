# Event Feed reasoning + tokens fallback

## Context

Observed issues:
- Event feed shows only compact event type/subtype markers, but not the latest agent reasoning text.
- `tokens` often stays `-` because stream JSON events may not include stable numeric token fields.

Goal:
- Keep current diagnostics intact.
- Add a separate reasoning panel with the latest 3-5 lines.
- Make token tracking resilient when numeric token fields are absent.

## Scope

In scope:
- `orc_core/stream_monitor.py` UI and event parsing updates.

Out of scope:
- Hook protocol changes.
- Telegram/report formatting changes outside current monitor metrics.

## Design

### 1) Dedicated reasoning buffer

- Add `self._recent_reasoning: Deque[str]` in `StreamJsonMonitor`.
- Keep `self._recent_events` unchanged for service-level event feed.
- Populate reasoning buffer from text payload extracted in `_record_event()`.
- Use lightweight filtering so the panel prefers reasoning/analysis-like entries and avoids pure service noise.

### 2) Dedicated reasoning panel in UI

- Add a separate panel `Reasoning (latest)` in `_render()`.
- Show up to 5 latest lines (matches approved user preference range 3-5).
- If empty, display `waiting for reasoning...`.
- Keep existing `Event Feed` panel unchanged.

### 3) Token fallback extraction

- Keep numeric extraction from `_extract_tokens(event)` as primary source.
- Add fallback: if numeric tokens are missing, parse token count from textual payload via `extract_tokens_from_text`.
- Preserve monotonic metric update with `max(current, candidate)`.

## Error handling and compatibility

- Parsing remains tolerant to stream-json schema variation across CLI versions.
- If reasoning cannot be detected, UI degrades gracefully (panel stays in waiting state).
- Token value remains optional and only updates when a valid candidate is found.

## Verification plan

- Run static verification on updated module (`python -m py_compile`).
- Run lint diagnostics for edited file(s).
- Manual smoke run:
  - Confirm `Reasoning (latest)` appears and refreshes.
  - Confirm `Event Feed` still shows event types.
  - Confirm `tokens` transitions from `-` to a number when token text is present.
