# Panduan Pengguna - File Integrity Checker (checksum-tools)

Aplikasi ini dipakai berpasangan antara dua pihak:

- **Pengirim** — pihak yang punya data asli, membuat manifest checksum sebelum data dikirim/disalin.
- **Pemeriksa** — pihak yang menerima data (misal lewat HDD eksternal), memverifikasi bahwa data yang diterima identik dengan data asli.

Manifest dan Master Hash yang dihasilkan di Tab 1 wajib dicatat ke dalam **Berita Acara Serah Terima (BAST)**, karena Master Hash inilah yang dipakai Pemeriksa untuk memastikan file manifest tidak diubah sebelum dipakai untuk verifikasi.

---

## Tab 1: Buat Manifest (Pengirim)

Langkah-langkah:

1. **Folder Data Sumber** — klik **Browse**, pilih folder yang berisi data yang akan dikirim.
2. **Termasuk sub-folder** — centang jika ingin semua file di dalam sub-folder ikut dimasukkan ke manifest. Kosongkan centang jika hanya ingin memproses file yang ada langsung di folder tersebut (tanpa masuk ke sub-folder).
3. **Simpan Manifest Ke** — klik **Browse**, tentukan lokasi & nama file manifest (`.csv`) yang akan dibuat.
4. **Hitung jumlah baris di Manifest** — centang jika ingin manifest juga mencatat jumlah baris (newline) tiap file. Berguna untuk file teks/CSV, sedikit menambah waktu proses.
5. Klik **Mulai Buat Manifest**.
6. Tunggu hingga progress bar selesai dan status berubah menjadi **"Selesai!"**.
7. Baca ringkasan di kotak log, yang berisi:
   - Folder Data Sumber
   - Status opsi sub-folder (✅ termasuk / ❌ tidak termasuk)
   - Total file yang diproses
   - Lokasi file manifest yang disimpan
   - Tanggal proses, waktu mulai, waktu selesai, dan durasi proses
   - User ID komputer yang menjalankan proses
   - **MASTER HASH (Manifest)** — SHA-256 dari file manifest.csv itu sendiri
8. Klik **Copy Log to Clipboard** (muncul di samping tombol Mulai Buat Manifest setelah proses selesai) untuk menyalin seluruh ringkasan ke clipboard, lalu tempel ke dokumen BAST.
9. **WAJIB**: catat **Master Hash** ke dalam BAST. Master Hash inilah yang nanti dimasukkan Pemeriksa di Tab 2 untuk memvalidasi manifest.
10. Kirim file manifest (`.csv`) bersama data ke Pemeriksa (biasanya disalin ke media yang sama dengan datanya).

> Catatan: Tanggal/waktu yang tercatat mengikuti jam komputer tempat aplikasi dijalankan (belum otomatis dikonversi ke zona waktu tertentu jika jam komputer berbeda zona).

---

## Tab 2: Verifikasi Integritas (Pemeriksa)

Langkah-langkah:

1. **Folder Target Verifikasi** — klik **Browse**, pilih folder hasil salinan data (misal folder di HDD eksternal) yang akan diverifikasi.
2. **Termasuk sub-folder** — samakan pilihan ini dengan yang dipakai Pengirim saat membuat manifest (lihat catatan di ringkasan log Tab 1 / BAST), supaya cakupan file yang diperiksa konsisten.
3. **File Manifest (CSV)** — klik **Browse**, pilih file manifest yang diterima dari Pengirim.
4. **Master Hash Manifest (dari BAST, wajib)** — masukkan Master Hash yang tercatat di BAST (hasil dari Tab 1 milik Pengirim). Field ini wajib diisi.
5. Klik **Mulai Verifikasi Data**.
   - Jika Master Hash yang dimasukkan **tidak cocok** dengan hash asli file manifest, proses langsung dibatalkan dengan pesan error — artinya file manifest.csv kemungkinan sudah berubah/rusak dan tidak bisa dipercaya. Periksa kembali Master Hash di BAST atau pastikan file manifest tidak rusak/ter-edit.
   - Jika cocok, verifikasi per-file berjalan dan hasilnya tampil di tabel.
6. Setelah selesai, periksa tabel hasil. Setiap baris punya status dengan warna:
   | Status | Warna | Arti |
   |---|---|---|
   | `MATCH` | Hijau | File identik dengan manifest — aman. |
   | `MODIFIED` | Merah | File ada, tapi isinya berbeda dari manifest (hash tidak cocok). |
   | `MISSING` | Kuning | File ada di manifest tapi tidak ditemukan di folder target. |
   | `UNTRACKED` | Biru | File ada di folder target tapi tidak ada di manifest (bisa jadi file baru, atau file yang dipindah/di-rename — aplikasi akan memberi keterangan jika hash-nya cocok dengan salah satu entri manifest). |

   Tabel diurutkan otomatis: `MODIFIED` dan `MISSING` ditampilkan lebih dulu karena paling perlu perhatian.
7. Klik **Export Hasil Verifikasi** untuk menyimpan seluruh hasil ke file CSV sebagai laporan/lampiran BAST.

---

## Tips & Troubleshooting

- **"Master Hash Tidak Cocok"** saat verifikasi: pastikan Master Hash yang diketik/ditempel sama persis dengan yang tercatat di BAST (tidak ada spasi/karakter tambahan), dan pastikan file manifest.csv yang dipakai adalah file asli yang dikirim (belum diubah/di-edit).
- **Banyak status `UNTRACKED`**: kemungkinan opsi "Termasuk sub-folder" antara pembuatan manifest dan verifikasi berbeda, atau folder yang dipilih tidak sama persis dengan folder sumber aslinya.
- **Proses lambat pada file besar**: aplikasi membaca file per-chunk (4 MB) sehingga cukup efisien untuk file besar, tapi tetap dibatasi kecepatan baca media penyimpanan (terutama HDD/media eksternal).
- Nomor versi aplikasi ditampilkan di title bar jendela (`v<versi>`) — sertakan info ini jika melaporkan masalah.
