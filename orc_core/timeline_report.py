#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import statistics
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except Exception:
            continue
        if isinstance(payload, dict):
            yield payload


def _percentile(values: List[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = int(round((len(ordered) - 1) * p))
    idx = max(0, min(idx, len(ordered) - 1))
    return int(ordered[idx])


def build_timeline_report(path: Path, *, top_n: int = 15) -> Dict[str, Any]:
    by_step: Dict[str, List[int]] = {}
    exit_reasons: Dict[str, int] = {}
    top_slowest: List[Dict[str, Any]] = []
    total_timeline_events = 0

    for event in _read_jsonl(path):
        if event.get("type") != "debug_timeline":
            continue
        total_timeline_events += 1
        step = str(event.get("step") or "")
        result = str(event.get("result") or "")
        reason = str(event.get("reason") or "")
        marker = str(event.get("event") or "")
        duration_raw = event.get("duration_ms")

        if marker == "finish" and isinstance(duration_raw, int):
            by_step.setdefault(step, []).append(int(duration_raw))
            top_slowest.append(
                {
                    "timeline_id": str(event.get("timeline_id") or ""),
                    "task_id": str(event.get("task_id") or ""),
                    "attempt": int(event.get("attempt") or 0),
                    "step": step,
                    "result": result,
                    "reason": reason,
                    "duration_ms": int(duration_raw),
                    "timestamp_ms": int(event.get("timestamp_ms") or 0),
                }
            )

        if step.endswith("_exit") or step == "wait_for_completion_exit":
            key = f"{step}:{result}:{reason}"
            exit_reasons[key] = exit_reasons.get(key, 0) + 1

    step_stats: List[Dict[str, Any]] = []
    for step, durations in sorted(by_step.items(), key=lambda item: item[0]):
        if not durations:
            continue
        step_stats.append(
            {
                "step": step,
                "count": len(durations),
                "avg_ms": int(statistics.fmean(durations)),
                "p50_ms": _percentile(durations, 0.5),
                "p95_ms": _percentile(durations, 0.95),
                "max_ms": max(durations),
            }
        )

    top_slowest = sorted(top_slowest, key=lambda item: item["duration_ms"], reverse=True)[: max(top_n, 1)]
    top_reasons = sorted(exit_reasons.items(), key=lambda item: item[1], reverse=True)

    return {
        "source": str(path),
        "total_timeline_events": total_timeline_events,
        "steps": step_stats,
        "top_slowest": top_slowest,
        "exit_reasons": [{"key": key, "count": count} for key, count in top_reasons],
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build latency report from ORC debug timeline JSONL log.")
    parser.add_argument("--log", required=True, help="Path to orc-debug-*.jsonl")
    parser.add_argument("--top", type=int, default=15, help="How many slowest finished steps to show")
    parser.add_argument("--format", choices=["json", "text"], default="text", help="Output format")
    return parser


def _to_text(report: Dict[str, Any]) -> str:
    lines = [
        f"source: {report.get('source')}",
        f"total_timeline_events: {report.get('total_timeline_events')}",
        "",
        "steps:",
    ]
    for step in report.get("steps", []):
        lines.append(
            f"- {step['step']}: count={step['count']} avg={step['avg_ms']}ms "
            f"p50={step['p50_ms']}ms p95={step['p95_ms']}ms max={step['max_ms']}ms"
        )
    lines.append("")
    lines.append("top_slowest:")
    for item in report.get("top_slowest", []):
        lines.append(
            f"- {item['step']} task={item['task_id']} attempt={item['attempt']} "
            f"duration={item['duration_ms']}ms result={item['result']} reason={item['reason']}"
        )
    lines.append("")
    lines.append("exit_reasons:")
    for item in report.get("exit_reasons", []):
        lines.append(f"- {item['key']} => {item['count']}")
    return "\n".join(lines)


def main() -> int:
    args = _build_arg_parser().parse_args()
    report = build_timeline_report(Path(args.log), top_n=args.top)
    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_to_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
