# SANDEV Brain

**Proyek adaptasi model bahasa terbuka untuk simulasi kehidupan SANDEV Life.**

## Kandidat model saat ini
- **SmolLM2-360M-Instruct** sebagai kandidat pertama untuk adaptasi percakapan, konteks, memori, penalaran, dan aksi game.
- Lisensi model upstream tercantum sebagai Apache-2.0 pada kartu model resmi: https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct
- Repo upstream berisi kode pelatihan, evaluasi, dan data: https://github.com/huggingface/smollm
- Catatan penting: model ini terutama dilatih untuk bahasa Inggris. Kemampuan bahasa Indonesia harus dibangun lewat dataset SANDEV dan dibuktikan melalui evaluasi.

## Perangkat target
Samsung A05 dengan RAM 6 GB. Model 360M adalah kandidat yang lebih masuk akal untuk uji inferensi lokal daripada model 7B, tetapi penggunaan RAM, kecepatan, panas, dan kestabilan belum diukur pada perangkat sebenarnya. Pelatihan adapter dilakukan pada lingkungan komputasi yang memadai; ini tidak berarti game harus menggunakan AI cloud saat dimainkan.

## Implementasi
Folder [smollm](smollm/README.md) berisi:
- Pipeline supervised fine-tuning dengan LoRA untuk SmolLM2.
- Dataset seed bahasa Indonesia dan contoh evaluasi terpisah.
- Runtime yang meminta keluaran dialog, usulan aksi, dan pembaruan memori dalam JSON.
- Penyimpanan memori sederhana dan validasi allow-list aksi.
- Tes runtime yang tidak perlu mengunduh bobot model.

## Status yang jujur
Pipeline dan contoh dataset adalah fondasi awal, bukan model SANDEV yang sudah selesai dilatih. Dataset masih perlu diperbesar dan dibersihkan. Tes parser tidak membuktikan kualitas kecerdasan model. Adapter harus dilatih, dievaluasi pada skenario yang tidak ada di data training, lalu diuji penggunaan RAM dan latensinya di Samsung A05 sebelum dinyatakan siap.

## Prinsip
- Satu model bahasa yang diadaptasi untuk SANDEV; penyimpanan memori dan validasi aksi adalah bagian dari game engine, bukan model AI kedua.
- Model hanya mengusulkan aksi; game engine memeriksa, menjalankan, dan mengonfirmasi hasilnya.
- Jangan menyimpan klaim model sebagai memori faktual sebelum kejadian dikonfirmasi engine.
- Periksa lisensi model, dataset, kode, dan artefak secara terpisah sebelum redistribusi.
