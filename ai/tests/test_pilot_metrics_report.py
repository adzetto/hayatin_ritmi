"""Unit tests for pilot_metrics_report.py."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "evaluation"))

import pilot_metrics_report as pmr


def _make_session(i: int, *, warning_ms: float = 800.0, crash: str = "0") -> dict[str, str]:
    participant_id = f"p{(i % 10) + 1}"
    return {
        "session_id": f"s{i}",
        "participant_id": participant_id,
        "duration_minutes": "6",
        "scenario": "rest",
        "predicted_label": "normal",
        "ground_truth_label": "normal",
        "warning_latency_ms": str(warning_ms),
        "false_alarm": "0",
        "crash": crash,
        "tflite_latency_single_ms": "10.0",
        "tflite_latency_three_ms": "20.0",
        "tflite_memory_mb": "1.5",
    }


def test_compute_sus_score_midpoint():
    # All answers "3" should map to SUS 50.0.
    assert pmr.compute_sus_score([3] * 10) == 50.0


def test_build_report_passes_acceptance():
    sessions = [_make_session(i) for i in range(600)]  # 600 * 6 min = 60 hours
    sus_scores = [80.0] * 10
    report = pmr.build_report(sessions, sus_scores)

    assert report["all_checks_passed"] is True
    assert report["summary"]["total_hours"] == 60.0
    assert report["summary"]["unique_participants"] == 10.0
    assert report["summary"]["accuracy_percent"] == 100.0


def test_build_report_fails_latency_check():
    sessions = [_make_session(i, warning_ms=1200.0) for i in range(600)]
    sus_scores = [80.0] * 10
    report = pmr.build_report(sessions, sus_scores)

    assert report["all_checks_passed"] is False
    assert report["acceptance_checks"]["warning_latency_p95"]["passed"] is False
