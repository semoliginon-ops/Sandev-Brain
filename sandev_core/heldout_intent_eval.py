"""Fresh untouched Indonesian intent evaluation set.

Do not use these examples to tune intent rules. They are a small manually
authored holdout, not statistically representative. Report the score honestly;
unknown/ambiguous predictions count as incorrect for an expected intent.
Run: PYTHONPATH=sandev_core python -m heldout_intent_eval
"""
from __future__ import annotations

from collections import Counter, defaultdict
from intent import classify_intent


# Deliberately separate from intent_eval.CASES. Keep this set untouched during
# rule iteration; if used for tuning, replace it with a newly authored set.
CASES: tuple[tuple[str, str], ...] = (
    ("Pagi, partner!", "greeting"),
    ("Akhirnya kita berjumpa lagi", "greeting"),
    ("Aku berutang budi atas bantuanmu", "thanks"),
    ("Terbantu banget sama kamu, makasih", "thanks"),
    ("Aku harus pamit sekarang", "farewell"),
    ("Nanti kita lanjut lagi, ya", "farewell"),
    ("Bisa tolong urus masalah ini bareng aku?", "help_request"),
    ("Aku butuh bantuanmu untuk menyelesaikannya", "help_request"),
    ("Posisi kita sedang dikepung!", "danger"),
    ("Ada yang mengincar kita dari arah belakang", "danger"),
    ("Aku hampir tumbang, cepat pulihkan aku", "heal_request"),
    ("Bisa pakai ramuan untuk memulihkan kondisiku?", "heal_request"),
    ("Hujani lawan itu dengan tembakan", "tactical_attack"),
    ("Jadikan musuh itu sasaran utama", "tactical_attack"),
    ("Jaga posisi dan jangan terpancing maju", "tactical_defend"),
    ("Bantu aku berlindung sampai situasi aman", "tactical_defend"),
    ("Aku lagi merasa sendirian malam ini", "comfort"),
    ("Aku cemas, boleh temani aku sebentar?", "comfort"),
    ("Coba bikin lelucon yang receh", "banter"),
    ("Buat suasananya lebih lucu dong", "banter"),
    ("Jangan pulihkan aku, simpan ramuan untuk nanti", "unknown"),
    ("Aku tidak meminta kamu menyerang siapa pun", "unknown"),
    ("Serang atau bertahan, menurutmu mana?", "unknown"),
    ("Bagaimana cara kerja gravitasi?", "unknown"),
    ("Apa kamu ingat cerita yang belum pernah kuberitahu?", "unknown"),
    ("Kalau aku diam, apakah itu berarti setuju?", "unknown"),
    ("Aku tidak takut, tapi aku juga tidak ingin bertarung", "unknown"),
    ("Mungkin kita sebaiknya bicara dulu sebelum bertindak", "unknown"),
    ("Dia terlihat aneh, apa pendapatmu?", "unknown"),
    ("Aku ingin sesuatu yang berbeda hari ini", "unknown"),
)


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
        for label, values in sorted(by_label.items())
    }
    return {
        "total": total,
        "correct": correct,
        "accuracy": correct / total if total else 1.0,
        "status_counts": dict(sorted(statuses.items())),
        "per_expected_intent": breakdown,
        "confusion_matrix": {label: dict(sorted(counts.items())) for label, counts in sorted(confusion.items())},
        "rows": rows,
    }


def main() -> int:
    report = run_evaluation()
    print(
        "Fresh Indonesian holdout (manual, non-representative): "
        f"{report['correct']}/{report['total']} ({report['accuracy']:.1%})"
    )
    print(f"Statuses: {report['status_counts']}")
    print("Per expected intent:")
    for label, item in report["per_expected_intent"].items():
        print(f"  {label}: {item['correct']}/{item['total']} ({item['accuracy']:.1%})")
    print("Confusion matrix (expected -> predicted counts):")
    for label, counts in report["confusion_matrix"].items():
        print(f"  {label}: {counts}")
    print("Mismatches:")
    for row in report["rows"]:
        if not row["passed"]:
            print(
                f"  {row['message']!r}: expected={row['expected']}, "
                f"actual={row['actual']}, status={row['status']}, reason={row['reason']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
