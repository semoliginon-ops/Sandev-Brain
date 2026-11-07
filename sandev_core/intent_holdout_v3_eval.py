"""First evaluation report for the frozen Indonesian intent holdout v3.

This evaluator is intentionally separate from development data. The first run
consumes v3 as a blind holdout; after results are inspected, v3 is diagnostic
and must never be used for rule tuning. Create a fresh holdout for later claims.
Run: PYTHONPATH=sandev_core python -m intent_holdout_v3_eval
"""
from __future__ import annotations

from collections import Counter, defaultdict
from intent import classify_intent
from intent_holdout_v3 import CASES


def run_evaluation() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    by_label: dict[str, list[bool]] = defaultdict(list)
    statuses: Counter[str] = Counter()
    confusion: dict[str, Counter[str]] = defaultdict(Counter)
    correct = 0

    for message, expected in CASES:
        result = classify_intent(message)
        actual = str(result["intent"])
        passed = actual == expected
        correct += int(passed)
        by_label[expected].append(passed)
        confusion[expected][actual] += 1
        statuses[str(result["status"])] += 1
        rows.append({
            "message": message,
            "expected": expected,
            "actual": actual,
            "status": result["status"],
            "reason": result["reason"],
            "passed": passed,
        })

    total = len(CASES)
    per_label = {
        label: {
            "correct": sum(values),
            "total": len(values),
            "accuracy": sum(values) / len(values) if values else 1.0,
        }
        for label, values in sorted(by_label.items())
    }
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 1.0,
        "status_counts": dict(sorted(statuses.items())),
        "per_expected_intent": per_label,
        "confusion_matrix": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(confusion.items())
        },
        "rows": rows,
    }


def main() -> int:
    report = run_evaluation()
    print(
        "Indonesian intent holdout v3 (first blind evaluation; now diagnostic): "
        f"{report['correct']}/{report['total']} ({report['accuracy']:.1%})"
    )
    print(f"Statuses: {report['status_counts']}")
    print("Per expected intent:")
    for label, item in report["per_expected_intent"].items():
        print(f"  {label}: {item['correct']}/{item['total']} ({item['accuracy']:.1%})")
    print("Mismatches:")
    for row in report["rows"]:
        if not row["passed"]:
            print(
                f"  {row['message']!r}: expected={row['expected']}, "
                f"actual={row['actual']}, status={row['status']}, "
                f"reason={row['reason']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
