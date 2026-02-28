#!/usr/bin/env python3
"""Pilot validation metrics calculator for Issue #18.

Expected session CSV columns:
    session_id,participant_id,duration_minutes,scenario,predicted_label,
    ground_truth_label,warning_latency_ms,false_alarm,crash,
    tflite_latency_single_ms,tflite_latency_three_ms,tflite_memory_mb

Expected SUS CSV columns:
    participant_id,q1,q2,q3,q4,q5,q6,q7,q8,q9,q10
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class Targets:
    min_hours: float = 60.0
    min_participants: int = 10
    accuracy_percent: float = 95.0
    warning_latency_ms: float = 1000.0
    false_alarm_percent: float = 5.0
    crash_free_percent: float = 98.0
    tflite_single_ms: float = 22.0
    tflite_three_ms: float = 38.0
    tflite_memory_mb: float = 2.1
    sus_score: float = 75.0


TARGETS = Targets()

SESSION_FIELDS = {
    "session_id",
    "participant_id",
    "duration_minutes",
    "scenario",
    "predicted_label",
    "ground_truth_label",
    "warning_latency_ms",
    "false_alarm",
    "crash",
    "tflite_latency_single_ms",
    "tflite_latency_three_ms",
    "tflite_memory_mb",
}

SUS_FIELDS = {
    "participant_id",
    "q1",
    "q2",
    "q3",
    "q4",
    "q5",
    "q6",
    "q7",
    "q8",
    "q9",
    "q10",
}


def _parse_bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "evet"}


def _parse_float(value: str) -> Optional[float]:
    text = str(value).strip()
    if not text:
        return None
    return float(text)


def _percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    rank = (len(ordered) - 1) * (p / 100.0)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    if low == high:
        return float(ordered[low])
    weight = rank - low
    return ordered[low] * (1.0 - weight) + ordered[high] * weight


def _mean(values: Iterable[float]) -> Optional[float]:
    data = list(values)
    if not data:
        return None
    return sum(data) / len(data)


def _check_fields(path: Path, header: List[str], required: set[str]) -> None:
    missing = required.difference(set(header))
    if missing:
        raise ValueError(f"{path} is missing required columns: {sorted(missing)}")


def load_sessions(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        _check_fields(path, reader.fieldnames, SESSION_FIELDS)
        return list(reader)


def compute_sus_score(answers: List[int]) -> float:
    if len(answers) != 10:
        raise ValueError("SUS requires exactly 10 answers")
    if any(a < 1 or a > 5 for a in answers):
        raise ValueError("SUS answers must be in [1, 5]")

    odd = sum(answers[i] - 1 for i in (0, 2, 4, 6, 8))
    even = sum(5 - answers[i] for i in (1, 3, 5, 7, 9))
    return (odd + even) * 2.5


def load_sus_scores(path: Optional[Path]) -> Optional[List[float]]:
    if path is None:
        return None

    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError(f"{path} has no header row")
        _check_fields(path, reader.fieldnames, SUS_FIELDS)

        scores: List[float] = []
        for row in reader:
            answers = [int(row[f"q{i}"]) for i in range(1, 11)]
            scores.append(compute_sus_score(answers))
        return scores


def summarize_sessions(sessions: List[Dict[str, str]]) -> Dict[str, Optional[float]]:
    total_sessions = len(sessions)
    participants = {s["participant_id"].strip() for s in sessions if s["participant_id"].strip()}
    total_minutes = sum(float(s["duration_minutes"]) for s in sessions)
    total_hours = total_minutes / 60.0

    labeled = 0
    correct = 0
    for s in sessions:
        pred = s["predicted_label"].strip()
        truth = s["ground_truth_label"].strip()
        if pred and truth:
            labeled += 1
            if pred == truth:
                correct += 1

    accuracy_percent = (100.0 * correct / labeled) if labeled else None

    false_alarm_count = sum(1 for s in sessions if _parse_bool(s["false_alarm"]))
    false_alarm_percent = (100.0 * false_alarm_count / total_sessions) if total_sessions else None

    crash_count = sum(1 for s in sessions if _parse_bool(s["crash"]))
    crash_free_percent = (
        100.0 * (1.0 - (crash_count / total_sessions)) if total_sessions else None
    )

    warning_latency_values = [
        x
        for x in (_parse_float(s["warning_latency_ms"]) for s in sessions)
        if x is not None
    ]
    warning_latency_p95_ms = _percentile(warning_latency_values, 95)

    tflite_single_values = [
        x
        for x in (_parse_float(s["tflite_latency_single_ms"]) for s in sessions)
        if x is not None
    ]
    tflite_three_values = [
        x
        for x in (_parse_float(s["tflite_latency_three_ms"]) for s in sessions)
        if x is not None
    ]
    memory_values = [
        x for x in (_parse_float(s["tflite_memory_mb"]) for s in sessions) if x is not None
    ]

    return {
        "total_sessions": float(total_sessions),
        "unique_participants": float(len(participants)),
        "total_hours": total_hours,
        "labeled_sessions": float(labeled),
        "accuracy_percent": accuracy_percent,
        "false_alarm_percent": false_alarm_percent,
        "crash_free_percent": crash_free_percent,
        "warning_latency_p95_ms": warning_latency_p95_ms,
        "tflite_single_p95_ms": _percentile(tflite_single_values, 95),
        "tflite_three_p95_ms": _percentile(tflite_three_values, 95),
        "tflite_memory_max_mb": max(memory_values) if memory_values else None,
    }


def _numeric_check(value: Optional[float], target: float, op: str) -> Dict[str, object]:
    if value is None:
        return {"value": None, "target": f"{op} {target}", "passed": False}
    if op == ">=":
        passed = value >= target
    elif op == "<=":
        passed = value <= target
    elif op == "<":
        passed = value < target
    else:
        raise ValueError(f"Unsupported check operator: {op}")
    return {"value": value, "target": f"{op} {target}", "passed": passed}


def evaluate_checks(
    summary: Dict[str, Optional[float]],
    sus_mean: Optional[float],
) -> Dict[str, Dict[str, object]]:
    checks: Dict[str, Dict[str, object]] = {
        "participants": _numeric_check(
            summary["unique_participants"], float(TARGETS.min_participants), ">="
        ),
        "pilot_hours": _numeric_check(summary["total_hours"], TARGETS.min_hours, ">="),
        "accuracy": _numeric_check(summary["accuracy_percent"], TARGETS.accuracy_percent, ">="),
        "warning_latency_p95": _numeric_check(
            summary["warning_latency_p95_ms"], TARGETS.warning_latency_ms, "<="
        ),
        "false_alarm_rate": _numeric_check(
            summary["false_alarm_percent"], TARGETS.false_alarm_percent, "<="
        ),
        "crash_free": _numeric_check(summary["crash_free_percent"], TARGETS.crash_free_percent, ">="),
        "tflite_single_p95": _numeric_check(
            summary["tflite_single_p95_ms"], TARGETS.tflite_single_ms, "<"
        ),
        "tflite_three_p95": _numeric_check(
            summary["tflite_three_p95_ms"], TARGETS.tflite_three_ms, "<"
        ),
        "tflite_memory_max": _numeric_check(
            summary["tflite_memory_max_mb"], TARGETS.tflite_memory_mb, "<"
        ),
        "sus_mean": _numeric_check(sus_mean, TARGETS.sus_score, ">="),
    }
    return checks


def build_report(
    sessions: List[Dict[str, str]],
    sus_scores: Optional[List[float]],
    sessions_path: Optional[str] = None,
    sus_path: Optional[str] = None,
) -> Dict[str, object]:
    summary = summarize_sessions(sessions)
    sus_mean = _mean(sus_scores) if sus_scores else None
    checks = evaluate_checks(summary, sus_mean)
    all_checks_passed = all(item["passed"] for item in checks.values())

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "sessions_csv": sessions_path,
            "sus_csv": sus_path,
            "sessions_count": len(sessions),
            "sus_response_count": len(sus_scores) if sus_scores else 0,
        },
        "summary": {
            **summary,
            "sus_mean": sus_mean,
        },
        "acceptance_checks": checks,
        "all_checks_passed": all_checks_passed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate pilot metrics report JSON.")
    parser.add_argument("--sessions", required=True, type=Path, help="Path to pilot sessions CSV")
    parser.add_argument("--sus", type=Path, help="Path to SUS responses CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ai/models/results/pilot_metrics_report.json"),
        help="Output JSON path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sessions = load_sessions(args.sessions)
    sus_scores = load_sus_scores(args.sus)
    report = build_report(
        sessions=sessions,
        sus_scores=sus_scores,
        sessions_path=str(args.sessions),
        sus_path=str(args.sus) if args.sus else None,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report written: {args.output}")
    print(f"All checks passed: {report['all_checks_passed']}")
    for name, check in report["acceptance_checks"].items():
        status = "PASS" if check["passed"] else "FAIL"
        print(f"- {name}: {status} (value={check['value']}, target={check['target']})")


if __name__ == "__main__":
    main()
