# Event Feed Reasoning and Tokens Fallback Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a dedicated UI panel with the latest agent reasoning lines and fix token metric updates when stream events do not expose numeric token fields.

**Architecture:** Keep the existing event feed intact and introduce a separate in-memory reasoning buffer in `StreamJsonMonitor`. Extend event parsing with a text-token fallback while preserving monotonic token updates. Limit changes to monitor/UI code to avoid protocol or hooks changes.

**Tech Stack:** Python 3.14, Rich (`Layout`, `Panel`, `Table`, `Text`), existing `orc_core` monitor/parser helpers.

---

### Task 1: Add reasoning capture and rendering

**Files:**
- Modify: `orc_core/stream_monitor.py`
- Test: manual smoke run via existing orchestrator flow

**Step 1: Add reasoning buffer and helper methods**

Implement:
- `self._recent_reasoning: Deque[str]` in `__init__`
- helper for identifying reasoning-like events
- helper to append cleaned reasoning lines

**Step 2: Add dedicated panel to UI layout**

Implement:
- panel `Reasoning (latest)` with up to 5 most recent reasoning lines
- fallback text `waiting for reasoning...`
- keep `Event Feed` panel unchanged

**Step 3: Verify rendering updates compile**

Run: `python -m py_compile orc_core/stream_monitor.py`
Expected: no output, exit code 0.

### Task 2: Fix tokens fallback from text payload

**Files:**
- Modify: `orc_core/stream_monitor.py`

**Step 1: Add text parsing fallback**

Implement:
- import `extract_tokens_from_text` from `orc_core.text_parse`
- in `_record_event`, after numeric extraction, parse from extracted event text when numeric tokens are absent

**Step 2: Preserve monotonic token behavior**

Implement:
- keep `self.metrics.tokens_total = max(current, candidate)` semantics for both numeric and text-derived values

**Step 3: Validate with static check**

Run: `python -m py_compile orc_core/stream_monitor.py`
Expected: no output, exit code 0.

### Task 3: Lint and final verification

**Files:**
- Check: `orc_core/stream_monitor.py`

**Step 1: Run diagnostics**

Run: `ReadLints` for edited file.
Expected: no newly introduced lint errors.

**Step 2: Manual behavior verification**

Run: monitor flow and confirm:
- `Reasoning (latest)` updates with 3-5 latest lines.
- `Event Feed` still shows event type/subtype updates.
- `Tokens` changes from `-` to numeric when token strings are present in text payload.

**Step 3: Commit**

```bash
git add orc_core/stream_monitor.py
git commit -m "fix: show latest reasoning panel and parse tokens from text fallback"
```
