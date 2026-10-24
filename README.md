# SANDEV Brain

**Proyek adaptasi langsung OLMo untuk membangun kecerdasan bahasa SANDEV Life.**

Tujuan proyek ini adalah mengadaptasi model OLMo agar memahami percakapan, konteks karakter, memori, emosi, tujuan, dan aksi di dunia game. Arah utamanya adalah satu model bahasa yang diadaptasi untuk SANDEV — bukan sistem hybrid dan bukan sekadar NPC berbasis aturan.

## Implementasi OLMo

Folder [`olmo/`](olmo/README.md) berisi pipeline adaptasi awal:
- Basis model resmi: [allenai/Olmo-3-7B-Instruct](https://huggingface.co/allenai/Olmo-3-7B-Instruct).
- Supervised fine-tuning dengan LoRA untuk mempelajari perilaku SANDEV Life.
- Runtime Python yang meminta model menghasilkan dialog, usulan aksi game, dan pembaruan memori dalam JSON.
- Validasi allow-list agar game hanya menjalankan aksi yang memang tersedia.
- Data seed dan contoh evaluasi untuk mengawali pengujian.

## Brain Core sebelumnya

`src/index.js` adalah prototipe logika simulasi deterministik yang sudah ada. Ia belum merupakan model bahasa dan bukan hasil adaptasi OLMo. Jalur adaptasi model sekarang dikembangkan di `olmo/`.

## Menjalankan tes runtime tanpa memuat bobot model

```bash
PYTHONPATH=olmo python -m unittest discover -s olmo
```

Tes ini memeriksa parser dan validasi keluaran, bukan kualitas kecerdasan model.

## Fine-tuning

Lihat [panduan adaptasi OLMo](olmo/README.md). Pelatihan memerlukan Python, dependensi model, checkpoint OLMo, dan komputasi yang memadai. Bobot dasar OLMo 3 7B sekitar 14,6 GB sebelum kebutuhan memori pelatihan; repo ini menyimpan kode dan data contoh, bukan bobot multi-gigabyte.

## Prinsip evaluasi

Belum ada klaim bahwa model SANDEV hasil fine-tuning sudah terlatih atau setara model lain. Data seed saat ini hanya contoh awal. Kita perlu memperbesar dataset, melatih adapter, menguji skenario yang tidak pernah dilihat saat pelatihan, dan mengukur kualitas bahasa, penggunaan konteks, akurasi aksi, latensi, serta memori.

## Referensi resmi

- [OLMo 3 model card](https://huggingface.co/allenai/Olmo-3-7B-Instruct)
- [OLMo-core: kode training resmi](https://github.com/allenai/OLMo-core)
- [Dokumentasi model AI2](https://docs.allenai.org/models/olmo/index.html)

Lisensi dan ketentuan penggunaan komponen upstream harus diperiksa sebelum redistribusi.
