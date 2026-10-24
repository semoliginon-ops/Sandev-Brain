# SANDEV Brain

**Sistem kecerdasan game yang mengadaptasi kemampuan model bahasa terbuka — bukan aplikasi untuk menjalankan model AI lokal.**

## Arah proyek yang benar

SmolLM2-360M-Instruct adalah kandidat **guru/rujukan saat pengembangan** untuk mempelajari pola percakapan, pemahaman konteks, penggunaan memori, penalaran, dan pemilihan aksi. Tujuan akhirnya adalah membangun sistem SANDEV Brain mandiri yang bisa dipakai ulang oleh berbagai game.

**Game yang memakai SANDEV Brain tidak boleh perlu memuat atau menjalankan bobot model AI lokal.** Sistem juga tidak boleh mewajibkan inferensi LLM cloud saat bermain.

## Implementasi mandiri yang sudah mulai tersedia

Folder `sandev_core/` berisi fondasi awal yang tidak bergantung pada model:
- normalisasi urgensi kebutuhan dan penilaian kandidat aksi berdasarkan kebutuhan/tujuan;
- pemeriksaan allow-list aksi dan prasyarat state;
- skor, alasan keputusan, tie-break deterministik, dan fallback jika tidak ada aksi layak;
- adapter generik berversi untuk menerima snapshot terstruktur dari genre game berbeda;
- ledger memori persisten yang hanya menerima kejadian terkonfirmasi oleh game engine atau fakta yang disetujui pemain;
- pencarian memori berdasarkan tag dan penggantian fakta lama oleh fakta baru yang sudah terverifikasi;
- umpan balik skor aksi konservatif berdasarkan hasil yang dikonfirmasi engine;
- benchmark regresi delapan skenario berlabel manual untuk simulasi kehidupan, shooter, dan RPG;\n- interpretasi perintah terbatas yang mengikat nama entitas ke snapshot engine, termasuk pronomina berbasis `focus_entity_id` dan target spasial hanya saat relasi eksplisit dari engine tersedia.

Adapter yang baru ditambahkan menguji kontrak snapshot yang sama untuk companion shooter, karakter RPG, dan karakter simulasi kehidupan. Adapter memvalidasi bentuk data dan menghasilkan **niat aksi**, bukan menjalankan aksi atau mengklaim berhasil. Integrasi game nyata tetap harus memasok state/kandidat legal dan meminta engine memvalidasi niat sebelum eksekusi.

Lihat [sandev_core/README.md](sandev_core/README.md). Benchmark dapat dijalankan dengan `PYTHONPATH=sandev_core python -m sandev_core.benchmark`; hasilnya adalah pengujian regresi skenario kecil, bukan skor kecerdasan umum.

Ini masih baseline aturan/skor plus memori terverifikasi, **belum kecerdasan umum, belum sistem produksi, dan belum bukti bahwa kemampuan SmolLM2 sudah berhasil dipindahkan**. Pemahaman bahasa terbuka, obrolan companion, dialog spontan, dan kesinambungan kepribadian belum diimplementasikan. Kualitas bahasa Indonesia dan perilaku game harus diuji, bukan diasumsikan.


## Siklus proposal perintah dan batas eksekusi

Modul `sandev_core/pending_command_session.py` menghubungkan perintah bahasa Indonesia yang dikenali dengan registry proposal. Proposal mempunyai ID, masa berlaku, dan versi state; pesan baru membatalkan proposal yang masih berstatus `pending`. Status `pending` bukan izin untuk menjalankan aksi.

Host game dapat menggunakan `PendingCommandSession.execute_pending(...)` sebagai gerbang serah-terima. Callback engine wajib melakukan pemeriksaan versi state **secara atomik bersama validasi aturan game dan eksekusi**, lalu mengembalikan `{"confirmed": true, "result": {}}` (nilai `confirmed` harus boolean). Hanya konfirmasi eksplisit dari callback yang menandai proposal selesai.

Contoh pola integrasi:

```python
from pending_command_session import PendingCommandSession

session = PendingCommandSession()

# Sesudah handle_message menghasilkan status "pending":
result = session.execute_pending(
    player_session_id,
    proposal["action_id"],
    get_current_state_version=game.get_state_version,
    engine_execute_if_version_matches=game.validate_and_execute_if_version,
)
```

Nama metode pada `game` di atas adalah contoh kontrak host, bukan API yang sudah tersedia di repo. Implementasi host harus memvalidasi target, izin, prasyarat, serta versi state di dalam operasi atomik. Lock di `PendingCommandSession` hanya menyerialisasi pesan dan eksekusi yang menggunakan instance yang sama; lock ini tidak melindungi mutasi dari proses lain. Registry masih in-memory, jadi status proposal tidak bertahan saat proses restart. Ini adalah fondasi integrasi, bukan bukti bahwa game tertentu sudah terhubung.

## Model kandidat untuk tahap riset

- SmolLM2-360M-Instruct: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- Proyek upstream: https://github.com/huggingface/smollm
- Lisensi model upstream tercantum Apache-2.0; periksa lisensi data dan artefak secara terpisah.

Model hanya alat riset/pengembangan. Tidak ada rencana mewajibkan game memuat model tersebut di perangkat pemain.

## Arsitektur target

1. **Input & world state:** game memberikan karakter, lingkungan, kebutuhan, hubungan, tujuan, dan kejadian.
2. **Context & memory manager:** memilih fakta relevan dan menangani fakta usang/kontradiktif.
3. **Decision system:** menilai kebutuhan, tujuan, konsekuensi, dan aksi yang tersedia.
4. **Dialogue behavior:** komponen bahasa mandiri untuk percakapan dan dialog kontekstual, setelah fondasi dan evaluasinya siap.
5. **Action adapter:** menerjemahkan keputusan generik ke aksi spesifik RPG, shooter, simulasi, atau genre baru.
6. **Outcome feedback:** engine mengonfirmasi hasil; hanya kejadian terverifikasi yang masuk memori.

Rincian: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md).

## Tes

GitHub Actions menjalankan tes core mandiri dan tes harness riset tanpa mengunduh bobot model:

```sh
PYTHONPATH=sandev_core python -m unittest discover -s sandev_core -v
PYTHONPATH=smollm python -m unittest discover -s smollm -v
```

Periksa hasil workflow terbaru untuk status tes aktual.

## Prinsip tetap

- Tidak membuat game yang harus memuat model AI lokal.
- Tidak mewajibkan inferensi AI cloud ketika game dimainkan.
- Sistem dapat dipakai ulang di game baru, bukan dikunci ke satu genre.
- Model guru adalah alat pengembangan; produk akhir adalah sistem SANDEV Brain mandiri.
- Game engine tetap menjadi sumber kebenaran atas state dan hasil aksi.
