# SANDEV Brain

**Sistem kecerdasan game yang mengadaptasi kemampuan model bahasa terbuka — bukan aplikasi untuk menjalankan model AI lokal.**

## Arah proyek yang benar

SmolLM2-360M-Instruct adalah kandidat **guru/rujukan saat pengembangan** untuk mempelajari pola percakapan, pemahaman konteks, penggunaan memori, penalaran, dan pemilihan aksi. Tujuan akhirnya adalah mentransfer kemampuan yang relevan ke sistem SANDEV Brain yang bisa dipakai ulang oleh berbagai game.

**Game yang memakai SANDEV Brain tidak boleh perlu memuat atau menjalankan bobot model AI lokal.** SANDEV Brain harus menjadi sistem game mandiri. Tidak boleh mewajibkan inferensi LLM cloud saat bermain.

## Implementasi mandiri yang sudah mulai tersedia

Folder `sandev_core/` kini berisi komponen awal yang tidak bergantung pada model:
- normalisasi urgensi kebutuhan dan penilaian kandidat aksi berdasarkan kebutuhan/tujuan;
- pemeriksaan allow-list aksi dan prasyarat state;
- skor, alasan keputusan, tie-break deterministik, dan fallback jika tidak ada aksi layak;
- ledger memori persisten yang hanya menerima kejadian terkonfirmasi oleh game engine atau fakta yang disetujui pemain;
- pencarian memori berdasarkan tag dan penggantian fakta lama oleh fakta baru yang sudah terverifikasi;\n- umpan balik skor aksi yang konservatif berdasarkan hasil yang dikonfirmasi engine;\n- benchmark regresi delapan skenario berlabel manual untuk simulasi kehidupan, shooter, dan RPG.

Core mengembalikan **niat aksi**, bukan menjalankan aksi atau mengklaim berhasil. Game engine tetap wajib memvalidasi, mengeksekusi, dan mengonfirmasi hasilnya. Memori juga sengaja menolak usulan dari model guru sebagai fakta tepercaya.

Lihat [sandev_core/README.md](sandev_core/README.md). Benchmark dapat dijalankan dengan `PYTHONPATH=sandev_core python -m sandev_core.benchmark`; hasilnya adalah pengujian regresi skenario kecil, bukan skor kecerdasan umum.

Umpan balik hanya menerima hasil yang dikonfirmasi game engine, dibatasi konteks, dan memakai smoothing; ia bukan pembelajaran bebas atau jaminan keputusan benar. Ini masih baseline aturan/skor plus memori terverifikasi, **belum kecerdasan umum, belum sistem produksi, dan belum bukti bahwa kemampuan SmolLM2 sudah berhasil dipindahkan**. Core saat ini memerlukan state terstruktur serta kandidat aksi yang disediakan adapter game.

## Model kandidat untuk tahap riset

- SmolLM2-360M-Instruct: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- Proyek upstream: https://github.com/huggingface/smollm
- Lisensi model upstream tercantum Apache-2.0; periksa lisensi data dan artefak secara terpisah.

Model hanya alat riset/pengembangan. Tidak ada rencana mewajibkan game memuat model tersebut di perangkat pemain. Kualitas bahasa Indonesia dan perilaku game harus dinilai dengan contoh uji yang jelas, bukan diasumsikan.

## Arsitektur target

1. **Input & world state:** game memberikan karakter, lingkungan, kebutuhan, hubungan, tujuan, dan kejadian.
2. **Context & memory manager:** memilih fakta relevan dan menangani fakta usang/kontradiktif.
3. **Decision system:** menilai kebutuhan, tujuan, konsekuensi, dan aksi yang tersedia.
4. **Dialogue behavior:** menggunakan respons/aturan yang telah dikurasi atau komponen mandiri yang kelak terbukti bermanfaat.
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
