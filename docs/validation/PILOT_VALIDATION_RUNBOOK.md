# Pilot Validation Runbook (Issue #18)

This document defines the execution-ready plan for the 60-hour field pilot.

## 1. Scope

- Goal: verify field performance targets from the project plan.
- Target window: 60+ total recording hours, 10+ participants.
- Scenarios: rest, walk, stairs, light run.
- Device: ADS1293-based hardware prototype + Android app.

## 2. Exit Criteria

- Accuracy >= 95%
- Warning latency (p95) <= 1000 ms
- False alarm rate <= 5%
- Crash-free rate >= 98%
- TFLite p95 latency:
  - single channel < 22 ms
  - three channel < 38 ms
- TFLite max memory < 2.1 MB
- SUS mean >= 75

## 3. Data Files

- Sessions CSV: `docs/validation/pilot_sessions_template.csv`
- SUS CSV: `docs/validation/sus_responses_template.csv`

Each completed session must include:

- participant id and session id
- duration in minutes
- scenario label
- model prediction and ground truth label
- warning latency
- false alarm / crash flags
- on-device latency and memory measurements

## 4. Execution Steps

1. Prepare participant consent and scheduling.
2. Run pilot sessions until total duration >= 60 hours.
3. Fill session rows after each run.
4. Collect SUS answers (1-5 scale) after participant completion.
5. Generate acceptance report:

```bash
python ai/evaluation/pilot_metrics_report.py \
  --sessions docs/validation/pilot_sessions_template.csv \
  --sus docs/validation/sus_responses_template.csv \
  --output ai/models/results/pilot_metrics_report.json
```

6. Archive output report JSON and raw CSV files under versioned storage.

## 5. Notes

- This runbook and tooling complete the software side of pilot readiness.
- Physical pilot execution still depends on hardware availability and field operations.
