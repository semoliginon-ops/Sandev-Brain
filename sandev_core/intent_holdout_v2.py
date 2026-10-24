"""Intent holdout v2, now inspected and therefore diagnostic only.

Do not tune rules against this set. Its first score is a one-time, small manual
check only; once results are inspected, preserve it as a reported benchmark
version rather than calling it an untouched holdout again.
Run: PYTHONPATH=sandev_core python -m intent_holdout_v2
"""
from __future__ import annotations

from collections import Counter
from intent import classify_intent

# Originally frozen before first evaluation; now inspected. Distinct wording from both existing
# diagnostic sets and intent_dev_eval.CASES.
CASES: tuple[tuple[str, str], ...] = (
    ("Selamat pagi, semoga harimu menyenangkan", "greeting"),
    ("Wah, lama tak berjumpa denganmu", "greeting"),
    ("Salam, bagaimana keadaanmu?", "greeting"),
    ("Aku berterima kasih banyak atas pertolongan tadi", "thanks"),
    ("Bantuan tadi sungguh berharga buatku", "thanks"),
    ("Aku menghargai semua yang sudah kamu lakukan", "thanks"),
    ("Aku undur diri dulu ya", "farewell"),
    ("Kita sambung obrolan ini besok", "farewell"),
    ("Sampai berjumpa kembali", "farewell"),
    ("Tempat ini berantakan, bantu aku mengatasinya", "help_request"),
    ("Aku kesulitan mengurus ini sendirian", "help_request"),
    ("Bisakah kamu membantuku menyelesaikan tugas ini?", "help_request"),
    ("Kita sedang dalam ancaman besar", "danger"),
    ("Ada pengejar di belakang rombongan", "danger"),
    ("Cepat, keadaan kita tidak aman!", "danger"),
    ("Tenagaku hampir habis, aku perlu dipulihkan", "heal_request"),
    ("Bisakah kau mengobati lukaku?", "heal_request"),
    ("Aku butuh ramuan penyembuh sekarang", "heal_request"),
    ("Bidik penyerang yang paling berbahaya", "tactical_attack"),
    ("Jangan biarkan lawan itu lolos, lumpuhkan dia", "tactical_attack"),
    ("Alihkan serangan ke pemimpin mereka", "tactical_attack"),
    ("Kita mundur ke balik tembok untuk berlindung", "tactical_defend"),
    ("Jangan ambil risiko, amankan posisi", "tactical_defend"),
    ("Buat garis pertahanan di sisi kanan", "tactical_defend"),
    ("Rasanya berat menjalani hari ini sendirian", "comfort"),
    ("Aku sedang kehilangan semangat, boleh temani aku?", "comfort"),
    ("Aku merasa hampa dan ingin ada teman bicara", "comfort"),
    ("Leluconmu dong, aku butuh ketawa", "banter"),
    ("Bikin suasana jadi konyol sedikit", "banter"),
    ("Ada humor ringan buatku?", "banter"),
    ("Tolong hitung jumlah bintang di langit", "unknown"),
    ("Siapa penemu mesin uap?", "unknown"),
    ("Aku lebih suka teh daripada kopi", "unknown"),
    ("Jangan lakukan apa pun sampai ada instruksi", "unknown"),
    ("Apa kita harus menyerang sekarang atau menunggu?", "unknown"),
)

def run_evaluation() -> dict[str, object]:
    rows = []
    statuses: Counter[str] = Counter()
    for message, expected in CASES:
        result = classify_intent(message)
        actual = str(result["intent"])
        passed = actual == expected
        statuses[str(result["status"])] += 1
        rows.append({"message": message, "expected": expected, "actual": actual,
                     "status": result["status"], "passed": passed,
                     "reason": result["reason"]})
    total = len(rows)
    correct = sum(bool(row["passed"]) for row in rows)
    return {"total": total, "correct": correct,
            "accuracy": correct / total if total else 1.0,
            "status_counts": dict(sorted(statuses.items())), "rows": rows}

def main() -> int:
    report = run_evaluation()
    print(f"Fresh holdout v2 (manual/small; freeze rules after this read): "
          f"{report['correct']}/{report['total']} ({report['accuracy']:.1%})")
    print(f"Statuses: {report['status_counts']}")
    for row in report["rows"]:
        if not row["passed"]:
            print(f"  MISMATCH {row['message']!r}: expected={row['expected']}, "
                  f"actual={row['actual']}, status={row['status']}, reason={row['reason']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
