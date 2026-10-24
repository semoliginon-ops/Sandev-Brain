# SANDEV Brain

**Sistem kecerdasan game yang mengadaptasi kemampuan model bahasa terbuka — bukan aplikasi untuk menjalankan model AI lokal.**

## Arah proyek yang benar

SmolLM2-360M-Instruct adalah kandidat **guru/rujukan saat pengembangan** untuk mempelajari pola percakapan, pemahaman konteks, penggunaan memori, penalaran, dan pemilihan aksi. Tujuan akhirnya adalah mentransfer kemampuan yang relevan ke sistem SANDEV Brain yang bisa dipakai ulang oleh berbagai game.

**Game yang memakai SANDEV Brain tidak boleh perlu memuat atau menjalankan bobot model AI lokal.** SANDEV Brain nantinya harus berupa sistem game mandiri: komponen dialog dan respons yang telah dikurasi, memori terstruktur, pengelolaan state, perencanaan/penilaian aksi, aturan keselamatan, serta modul kecil yang dihasilkan atau dilatih dari proses adaptasi jika terbukti bermanfaat.

## Model kandidat untuk tahap riset

- SmolLM2-360M-Instruct: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- Proyek upstream: https://github.com/huggingface/smollm
- Lisensi model upstream tercantum Apache-2.0; periksa lisensi data dan artefak secara terpisah.

Model hanya alat riset/pengembangan untuk tahap ini. Tidak ada rencana mewajibkan game memuat model tersebut di perangkat pemain. Karena kemampuan model cenderung lebih kuat dalam bahasa Inggris, kualitas bahasa Indonesia harus diajarkan lewat contoh dan diukur secara nyata.

## Arsitektur target

1. **Input & world state:** game memberikan karakter, lingkungan, kebutuhan, hubungan, tujuan, dan kejadian.
2. **Context & memory manager:** memilih fakta relevan dari memori game dan menyingkirkan fakta usang/kontradiktif.
3. **Decision system:** menilai kebutuhan, tujuan, konsekuensi, dan aksi yang memang tersedia bagi game.
4. **Dialogue system:** menghasilkan respons dari paket dialog/representasi/komponen yang sudah dipelajari atau dikompilasi; tidak mengunduh atau menjalankan LLM.
5. **Action adapter:** menerjemahkan keputusan generik SANDEV Brain ke API aksi spesifik RPG, shooter, simulasi, atau genre baru.
6. **Outcome feedback:** game engine mengonfirmasi hasil aksi; hanya kejadian terverifikasi yang masuk memori.

Rincian: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md).

## Status saat ini

Folder `smollm/` berisi contoh dataset, eksperimen LoRA, dan runtime riset untuk memeriksa keluaran guru. **Runtime riset tersebut bukan runtime yang akan dibawa ke dalam game.** Belum ada model SANDEV final yang selesai dilatih atau kemampuan yang sudah berhasil dipindahkan sepenuhnya ke sistem mandiri.

Tes parser, memori, dan allow-list hanya memeriksa fondasi software; tes tersebut tidak membuktikan kecerdasan. Tahap berikutnya adalah membuat dataset perilaku terukur, menguji kualitas keluaran model guru, mengekstrak perilaku yang berguna menjadi komponen game mandiri, lalu mengukur apakah sistem hasilnya bekerja tanpa bobot LLM.

## Prinsip tetap

- Tidak membuat game yang harus memuat model AI lokal.
- Tidak mewajibkan inferensi AI cloud ketika game dimainkan.
- Sistem harus dapat dipakai ulang di game baru, bukan dikunci ke satu genre.
- Model guru adalah alat pengembangan; produk akhir adalah sistem SANDEV Brain.
- Game engine tetap menjadi sumber kebenaran atas state dan hasil aksi.
