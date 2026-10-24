"""Frozen Indonesian intent holdout v3 — DO NOT USE FOR RULE TUNING.

Protocol:
- This set was authored after development-set edits.
- Do not run it until development changes are frozen and CI is green.
- On first evaluation, report all mismatches; do not tune against this version.
- If tuning follows, this version becomes diagnostic and a new holdout is needed.

This module intentionally contains labels/data only; evaluation is performed by
an explicit, separately reviewed evaluation command when the development phase
is frozen.
"""
CASES: tuple[tuple[str, str], ...] = (
    ("Selamat datang kembali, kawan", "greeting"),
    ("Senang sekali bisa bertemu lagi", "greeting"),
    ("Apa kabar hari ini, teman?", "greeting"),
    ("Aku sungguh berterima kasih atas bantuanmu", "thanks"),
    ("Pertolonganmu sangat berarti bagiku", "thanks"),
    ("Aku berutang banyak kebaikan padamu", "thanks"),
    ("Aku pamit dan melanjutkan perjalanan", "farewell"),
    ("Kita bertemu lagi di kesempatan lain", "farewell"),
    ("Waktunya aku pergi dulu", "farewell"),
    ("Temani aku menyelesaikan persoalan ini", "help_request"),
    ("Aku tak sanggup membereskannya tanpa bantuan", "help_request"),
    ("Bersedia bantu aku mengurus ini?", "help_request"),
    ("Kita bisa celaka kalau tetap di sini", "danger"),
    ("Ada ancaman yang mendekat dari sisi timur", "danger"),
    ("Mereka mengejar kelompok kita!", "danger"),
    ("Lukaku parah, aku perlu perawatan", "heal_request"),
    ("Bisakah kesehatanku dipulihkan?", "heal_request"),
    ("Aku hampir kehabisan daya hidup", "heal_request"),
    ("Serbu pemanah di menara itu", "tactical_attack"),
    ("Utamakan sasaran yang membawa bendera", "tactical_attack"),
    ("Lepaskan tembakan ke gerombolan musuh", "tactical_attack"),
    ("Bersembunyi dulu sampai keadaan tenang", "tactical_defend"),
    ("Kita perlu memperkuat pertahanan di utara", "tactical_defend"),
    ("Jangan keluar dari perlindungan", "tactical_defend"),
    ("Aku butuh seseorang untuk mendengarkan ceritaku", "comfort"),
    ("Hari ini terasa sepi sekali buatku", "comfort"),
    ("Aku sedang khawatir dan ingin ditemani", "comfort"),
    ("Kasih aku bahan buat tertawa", "banter"),
    ("Boleh bikin lelucon singkat?", "banter"),
    ("Ayo bikin suasana lebih jenaka", "banter"),
    ("Tolong ubah angka 42 menjadi angka Romawi", "unknown"),
    ("Kapan musim hujan biasanya dimulai?", "unknown"),
    ("Aku lebih suka bermain sendiri", "unknown"),
    ("Jangan bergerak sampai aku memberi tanda", "unknown"),
    ("Haruskah kita bertahan atau mengejar mereka?", "unknown"),
)
