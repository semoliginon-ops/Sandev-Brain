"""Small hand-authored regression set for the Indonesian intent baseline.

Run with: PYTHONPATH=sandev_core python -m intent_benchmark
This is a sanity check, not a held-out or independent intelligence evaluation.
"""
from __future__ import annotations

from intent import classify_intent


CASES = (
    ("hai!", "greeting"),
    ("Selamat pagi", "greeting"),
    ("Halo, apa kabar?", "greeting"),
    ("makasih banyak ya", "thanks"),
    ("Terima kasih!", "thanks"),
    ("aku berterima kasih", "thanks"),
    ("dadah dulu", "farewell"),
    ("Aku pergi dulu", "farewell"),
    ("sampai jumpa", "farewell"),
    ("bantu aku dong", "help_request"),
    ("aku butuh bantuan sekarang", "help_request"),
    ("bisa bantu aku?", "help_request"),
    ("awas!", "danger"),
    ("aku dalam bahaya", "danger"),
    ("ada musuh di belakang", "danger"),
    ("darahku tinggal sedikit", "heal_request"),
    ("pulihkan HP!", "heal_request"),
    ("aku sekarat", "heal_request"),
    ("serang musuh sekarang", "tactical_attack"),
    ("habisi bos!", "tactical_attack"),
    ("lindungi aku", "tactical_defend"),
    ("mundur dulu", "tactical_defend"),
    ("aku takut", "comfort"),
    ("temani aku ya", "comfort"),
    ("ceritakan lelucon", "banter"),
    ("buat aku tertawa", "banter"),
    ("menurutmu langit sore ini seperti apa?", "unknown"),
    ("aku mau ngobrol soal musik", "unknown"),
    ("Awas, lindungi aku!", "unknown"),  # ambiguous; safe result uses intent=unknown
)


def run_benchmark() -> dict[str, object]:
    rows = []
    correct = 0
    for message, expected in CASES:
        result = classify_intent(message)
        actual = result["intent"]
        passed = actual == expected
        correct += int(passed)
        rows.append({
            "message": message,
            "expected": expected,
            "actual": actual,
            "status": result["status"],
            "passed": passed,
        })
    total = len(CASES)
    return {"total": total, "correct": correct, "accuracy": correct / total if total else 1.0,
            "rows": rows}


def main() -> int:
    report = run_benchmark()
    print(f"Indonesian intent regression: {report['correct']}/{report['total']} "
          f"({report['accuracy']:.1%})")
    for row in report["rows"]:
        marker = "PASS" if row["passed"] else "FAIL"
        print(f"{marker}: {row['message']!r} -> {row['actual']} "
              f"(expected {row['expected']}; status={row['status']})")
    return 0 if report["correct"] == report["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
