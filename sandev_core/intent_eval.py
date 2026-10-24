"""Challenge-set evaluation for Indonesian intent generalization.

Run from the repository root:
    PYTHONPATH=sandev_core python -m intent_eval

This set intentionally uses paraphrases that are not copied from DEFAULT_PATTERNS.
It is a manually authored challenge set, not a statistically representative or
independent benchmark. Once used to tune rules, it must no longer be described
as held out.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from intent import classify_intent


# message, expected intent. Unknown cases are intentionally unsupported or
# unsafe-to-infer requests; ambiguity cases expect the safe "unknown" intent.
CASES: tuple[tuple[str, str], ...] = (
    ("Pagi, kawan!", "greeting"),
    ("Senang ketemu kamu lagi", "greeting"),
    ("Wah, bantuanmu berarti banget buatku", "thanks"),
    ("Aku cabut dulu, sampai nanti", "farewell"),
    ("Boleh temenin aku sebentar?", "help_request"),
    ("Aku kewalahan, bantu beresin ini", "help_request"),
    ("Mereka mengepung kita dari belakang!", "danger"),
    ("Ada lawan mendekat dari arah utara", "danger"),
    ("Kondisiku kritis, perlu pemulihan", "heal_request"),
    ("Tolong isi lagi tenaga atau darahku", "heal_request"),
    ("Arahkan tembakan ke lawan yang paling dekat", "tactical_attack"),
    ("Hantam dia sebelum dia kabur", "tactical_attack"),
    ("Jangan maju, tetap di belakangku", "unknown"),
    ("Kita perlu berlindung di balik batu", "tactical_defend"),
    ("Ambil jarak dan tahan posisi dulu", "tactical_defend"),
    ("Aku lagi down, jangan tinggalin aku sendirian", "comfort"),
    ("Boleh tetap di sini? Aku lagi gelisah", "comfort"),
    ("Lempar satu humor receh dong", "banter"),
    ("Kasih sesuatu yang kocak buat mencairkan suasana", "banter"),
    ("Jangan obati aku dulu, aku masih kuat", "unknown"),
    ("Serang mereka atau mundur saja?", "unknown"),
    ("Apa pendapatmu tentang musik jazz?", "unknown"),
    ("Ceritakan sesuatu tentang asal-usul kerajaan ini", "unknown"),
    ("Aku tidak takut, kita lanjut", "unknown"),
    ("Jangan tembak sebelum aku memberi aba-aba", "unknown"),
)


def run_evaluation() -> dict[str, object]:
    rows: list[dict[str, object]] = []
    per_intent: dict[str, list[bool]] = defaultdict(list)
    statuses: Counter[str] = Counter()
    correct = 0

    for message, expected in CASES:
        result = classify_intent(message)
        actual = str(result["intent"])
        passed = actual == expected
        correct += int(passed)
        per_intent[expected].append(passed)
        statuses[str(result["status"])] += 1
        rows.append({
            "message": message,
            "expected": expected,
            "actual": actual,
            "status": result["status"],
            "passed": passed,
            "reason": result["reason"],
        })

    total = len(CASES)
    breakdown = {
        label: {
            "correct": sum(values),
            "total": len(values),
            "accuracy": sum(values) / len(values) if values else 1.0,
        }
        for label, values in sorted(per_intent.items())
    }
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 1.0,
        "status_counts": dict(sorted(statuses.items())),
        "per_expected_intent": breakdown,
        "rows": rows,
    }


def main() -> int:
    report = run_evaluation()
    print(
        "Indonesian intent challenge set: "
        f"{report['correct']}/{report['total']} "
        f"({report['accuracy']:.1%})"
    )
    print(f"Statuses: {report['status_counts']}")
    print("Per expected intent:")
    for label, item in report["per_expected_intent"].items():
        print(
            f"  {label}: {item['correct']}/{item['total']} "
            f"({item['accuracy']:.1%})"
        )
    print("Mismatches:")
    for row in report["rows"]:
        if not row["passed"]:
            print(
                f"  {row['message']!r}: expected={row['expected']}, "
                f"actual={row['actual']}, status={row['status']}, "
                f"reason={row['reason']}"
            )
    # Evaluation reports are diagnostic; a low score must be visible rather
    # than silently changing the classifier or making CI pretend it passed.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
