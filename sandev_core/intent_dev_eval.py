"""Development-only Indonesian intent evaluation; not a held-out benchmark.

Run: PYTHONPATH=sandev_core python -m intent_dev_eval [--min-accuracy 0.70]
This dataset is intended for iterative development and must never be described as
independent evidence of generalization.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from intent import classify_intent

# New examples authored for development. Keep separate from intent_eval.CASES
# and heldout_intent_eval.CASES; tuning against this set is expected.
CASES: tuple[tuple[str, str], ...] = (
    ("Pagi, bro! Senang lihat kamu", "greeting"),
    ("Halo kawan, apa kabarmu?", "greeting"),
    ("Hai, kita ketemu lagi", "greeting"),
    ("Makasih banyak ya, kamu nolong banget", "thanks"),
    ("Aku sangat menghargai pertolonganmu", "thanks"),
    ("Terima kasih banyak atas dukungannya", "thanks"),
    ("Aku pamit dulu, nanti balik lagi", "farewell"),
    ("Sampai ketemu di lain waktu", "farewell"),
    ("Aku harus pergi sekarang", "farewell"),
    ("Bisa tolongin aku sebentar?", "help_request"),
    ("Aku perlu bantuanmu sekarang", "help_request"),
    ("Tolong bantu selesaikan urusan ini", "help_request"),
    ("Mereka ada di dekat kita, hati-hati!", "danger"),
    ("Situasinya gawat, kita terancam", "danger"),
    ("Musuh sudah mengejar kita", "danger"),
    ("Tolong pulihkan kesehatanku", "heal_request"),
    ("Aku butuh obat untuk memulihkan diri", "heal_request"),
    ("Sisa darahku sedikit sekali", "heal_request"),
    ("Jadikan dia target dan tembak", "tactical_attack"),
    ("Ayo fokus pada lawan itu", "tactical_attack"),
    ("Hajar musuh yang di depan", "tactical_attack"),
    ("Jangan dekati mereka, berlindung dulu", "tactical_defend"),
    ("Tetap di tempat aman dan jaga posisi", "tactical_defend"),
    ("Tolong lindungi bagian belakang", "tactical_defend"),
    ("Aku lagi murung, temani sebentar ya", "comfort"),
    ("Aku merasa cemas sendirian", "comfort"),
    ("Jangan pergi dulu, aku butuh teman", "comfort"),
    ("Coba hibur aku dengan lelucon", "banter"),
    ("Bikin aku ngakak dong", "banter"),
    ("Lontarkan candaan yang lucu", "banter"),
    ("Berapa hasil tujuh dikali delapan?", "unknown"),
    ("Ceritakan fakta tentang planet Saturnus", "unknown"),
    ("Apakah kamu suka warna biru?", "unknown"),
    ("Jangan menyerang dulu, tunggu aba-abaku", "unknown"),
    ("Menurutmu menyerang atau bertahan lebih baik?", "unknown"),
)

def run_evaluation() -> dict[str, object]:
    rows = []
    by_label: dict[str, list[bool]] = defaultdict(list)
    statuses: Counter[str] = Counter()
    for message, expected in CASES:
        result = classify_intent(message)
        actual = str(result["intent"])
        passed = actual == expected
        by_label[expected].append(passed)
        statuses[str(result["status"])] += 1
        rows.append({"message": message, "expected": expected, "actual": actual,
                     "status": result["status"], "passed": passed,
                     "reason": result["reason"]})
    total = len(rows)
    correct = sum(bool(row["passed"]) for row in rows)
    return {
        "total": total, "correct": correct,
        "accuracy": correct / total if total else 1.0,
        "status_counts": dict(sorted(statuses.items())),
        "per_expected_intent": {
            label: {"correct": sum(values), "total": len(values),
                    "accuracy": sum(values) / len(values)}
            for label, values in sorted(by_label.items())
        },
        "rows": rows,
    }

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-accuracy", type=float, default=0.70)
    args = parser.parse_args()
    if not 0 <= args.min_accuracy <= 1:
        parser.error("--min-accuracy must be between 0 and 1")
    report = run_evaluation()
    print(f"Indonesian development evaluation: {report['correct']}/{report['total']} "
          f"({report['accuracy']:.1%}); CI minimum={args.min_accuracy:.1%}")
    print(f"Statuses: {report['status_counts']}")
    for label, item in report["per_expected_intent"].items():
        print(f"  {label}: {item['correct']}/{item['total']} ({item['accuracy']:.1%})")
    failures = [row for row in report["rows"] if not row["passed"]]
    for row in failures:
        print(f"  FAIL {row['message']!r}: expected={row['expected']}, "
              f"actual={row['actual']}, reason={row['reason']}")
    if report["accuracy"] < args.min_accuracy:
        print("FAIL: development-set accuracy is below the configured threshold.")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
