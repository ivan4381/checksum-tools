# checksum-tools

**File Integrity Checker - Data Management SHD**

Aplikasi desktop (Tkinter) untuk membuat manifest checksum (SHA-256) dari sebuah folder data, lalu memverifikasi integritas data tersebut setelah dipindahkan/disalin ke media lain (misal HDD eksternal). Dipakai sebagai bukti serah-terima data yang bisa dicatat di Berita Acara Serah Terima (BAST).

## Fitur

**Tab 1 - Buat Manifest (Pengirim)**
- Pilih folder data sumber, opsional menyertakan sub-folder atau hanya file di level teratas.
- Hitung SHA-256 tiap file, opsional hitung jumlah baris (newline) sekaligus.
- Simpan manifest ke CSV (`Relative_Path`, `SHA256_Hash`, `Byte_Size`, `Row_Count`).
- Hitung **Master Hash** (SHA-256 dari file manifest itu sendiri) sebagai bukti manifest belum diubah — wajib dicatat di BAST.
- Log ringkasan proses (folder sumber, opsi sub-folder, total file, lokasi manifest, tanggal/waktu mulai-selesai, durasi, User ID yang menjalankan, dan Master Hash).
- Tombol **Copy Log to Clipboard** untuk menyalin ringkasan log setelah proses selesai.

**Tab 2 - Verifikasi Integritas (Pemeriksa)**
- Pilih folder target (misal HDD eksternal) dan file manifest CSV yang diterima.
- Wajib memasukkan Master Hash dari BAST — verifikasi dibatalkan otomatis jika Master Hash tidak cocok (manifest dianggap tidak bisa dipercaya).
- Opsional menyertakan sub-folder atau hanya file di level teratas folder target.
- Hasil verifikasi per-file ditampilkan dengan status `MATCH`, `MODIFIED`, `MISSING`, atau `UNTRACKED` (termasuk deteksi file yang dipindah/rename berdasarkan hash yang sama).
- Export hasil verifikasi ke CSV.

## Kebutuhan

- Python 3.9+ dengan Tkinter (bawaan instalasi Python standar dari [python.org](https://www.python.org/)).
- Tidak ada dependency pihak ketiga untuk menjalankan aplikasi — lihat [requirements.txt](requirements.txt) (isinya hanya dependency untuk build exe).

## Menjalankan dari Source

```bash
python checksum_tools.py
```

## Build ke .exe (Windows, one-file)

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --icon="verified.ico" --add-data "verified.ico;." --name checksum_tools checksum_tools.py
```

Hasil build ada di folder `dist/checksum_tools.exe`. Icon `.ico` dibuat dari `verified.png` (dikonversi sekali dengan Pillow) dan dipakai baik untuk icon file exe (`--icon`) maupun icon title bar/taskbar saat aplikasi berjalan (di-load lewat `resource_path()` di dalam kode).

## Versi Aplikasi

Nomor versi yang tampil di title bar diatur lewat variabel `APP_VERSION` di baris atas `checksum_tools.py` — ubah nilainya saat merilis versi baru.

## Panduan Pengguna

Lihat [Panduan_Pengguna.md](Panduan_Pengguna.md) untuk panduan langkah-demi-langkah penggunaan aplikasi (termasuk alur BAST antara pengirim dan pemeriksa data).
