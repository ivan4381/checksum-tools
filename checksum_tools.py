import os
import sys
import csv
import io
import time
import datetime
import getpass
import hashlib
import socket
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

BULAN_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember"
]

# Versi Aplikasi - ubah di sini saat rilis versi baru, otomatis tampil di title bar
APP_VERSION = "1.2.2"

# Konfigurasi Buffer Size untuk HDD (4 MB)
CHUNK_SIZE = 4 * 1024 * 1024

def resource_path(relative_path):
    """Cari lokasi resource, kompatibel untuk mode script biasa maupun exe hasil PyInstaller (onefile)."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

class TaxDataIntegrityApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"File Integrity Checker v{APP_VERSION} - Data Management SHD (dama.ppn.support@pertamina.com)")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)

        # Icon Aplikasi (title bar & taskbar)
        try:
            self.root.iconbitmap(resource_path("verified.ico"))
        except Exception:
            pass


        # Antrean (Queue) untuk komunikasi antara background thread dan GUI
        self.msg_queue = queue.Queue()
        
        self.setup_ui()
        self.check_queue_loop()
        
    def setup_ui(self):
        # Notebook (Tab Control)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Buat Manifest
        self.tab_manifest = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_manifest, text='1. Buat Manifest (Pengirim)')
        self.setup_manifest_tab()
        
        # Tab 2: Verifikasi
        self.tab_verify = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_verify, text='2. Verifikasi Integritas (Pemeriksa)')
        self.setup_verify_tab()

        # Tab 3: Check Integritas 1 File
        self.tab_check = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_check, text='3. Check Integritas File')
        self.setup_check_tab()

    # ==============================
    # UI SETUP: TAB 1 (BUAT MANIFEST)
    # ==============================
    def setup_manifest_tab(self):
        frame_input = ttk.LabelFrame(self.tab_manifest, text=" Pengaturan Sumber Data ")
        frame_input.pack(fill='x', padx=15, pady=10)
        
        # Source Folder
        self.src_folder_var = tk.StringVar()
        ttk.Label(frame_input, text="Folder Data Sumber:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.src_folder_var, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_src_folder).grid(row=0, column=2, padx=5, pady=5)

        # Opsi Termasuk Sub-folder
        self.include_subfolder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_input, text="Termasuk sub-folder", variable=self.include_subfolder_var).grid(row=1, column=0, sticky='w', padx=5, pady=5)

        # Output Manifest File
        self.manifest_out_var = tk.StringVar()
        ttk.Label(frame_input, text="Simpan Manifest Ke:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.manifest_out_var, width=60).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_manifest_out).grid(row=2, column=2, padx=5, pady=5)

        # Opsi Hitung Baris
        self.count_lines_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_input, text="Hitung jumlah baris di Manifest", variable=self.count_lines_var).grid(row=3, column=0, sticky='w', padx=5, pady=5)
        
        # Eksekusi (Mulai Buat Manifest + Copy Log berdampingan agar tidak menggeser tinggi log window)
        frame_actions = ttk.Frame(self.tab_manifest)
        frame_actions.pack(pady=10)

        self.btn_generate = ttk.Button(frame_actions, text="Mulai Buat Manifest", command=self.start_generate_manifest)
        self.btn_generate.pack(side=tk.LEFT, padx=5)

        # Copy Log to Clipboard - hanya dimunculkan (pack) setelah proses selesai
        self.btn_copy_log = ttk.Button(frame_actions, text="Copy Log to Clipboard", command=self.copy_log_to_clipboard)

        # Progress & Status
        frame_status = ttk.LabelFrame(self.tab_manifest, text=" Status Proses ")
        frame_status.pack(fill='both', expand=True, padx=15, pady=10)
        
        self.lbl_manifest_status = ttk.Label(frame_status, text="Menunggu instruksi...")
        self.lbl_manifest_status.pack(anchor='w', padx=10, pady=5)
        
        self.prog_manifest = ttk.Progressbar(frame_status, orient='horizontal', mode='determinate')
        self.prog_manifest.pack(fill='x', padx=10, pady=5)
        
        self.txt_manifest_log = tk.Text(frame_status, height=10, state='disabled', bg='#f4f4f4')
        self.txt_manifest_log.pack(fill='both', expand=True, padx=10, pady=10)

    # ==============================
    # UI SETUP: TAB 2 (VERIFIKASI)
    # ==============================
    def setup_verify_tab(self):
        frame_input = ttk.LabelFrame(self.tab_verify, text=" Pengaturan Verifikasi Target ")
        frame_input.pack(fill='x', padx=15, pady=10)
        
        # Target Folder (HDD Eksternal)
        self.tgt_folder_var = tk.StringVar()
        ttk.Label(frame_input, text="Folder Target Verifikasi:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.tgt_folder_var, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_tgt_folder).grid(row=0, column=2, padx=5, pady=5)

        # Opsi Termasuk Sub-folder
        self.verify_include_subfolder_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_input, text="Termasuk sub-folder", variable=self.verify_include_subfolder_var).grid(row=1, column=0, sticky='w', padx=5, pady=5)

        # Input Manifest File
        self.manifest_in_var = tk.StringVar()
        ttk.Label(frame_input, text="File Manifest (CSV):").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.manifest_in_var, width=60).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_manifest_in).grid(row=2, column=2, padx=5, pady=5)

        # Master Hash pembanding (wajib diisi, dicatat di BAST saat manifest dibuat)
        self.expected_master_hash_var = tk.StringVar()
        ttk.Label(frame_input, text="Master Hash Manifest (dari BAST, wajib):").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.expected_master_hash_var, width=60).grid(row=3, column=1, padx=5, pady=5)

        # Eksekusi
        self.btn_verify = ttk.Button(self.tab_verify, text="Mulai Verifikasi Data", command=self.start_verify)
        self.btn_verify.pack(pady=5)
        self.btn_export_log = ttk.Button(self.tab_verify, text="Export Hasil Verifikasi", state='disabled', command=self.export_verification_log)
        self.btn_export_log.pack(pady=5)
        
        # Progress & Status
        self.lbl_verify_status = ttk.Label(self.tab_verify, text="Menunggu instruksi...")
        self.lbl_verify_status.pack(anchor='w', padx=15, pady=2)
        
        self.prog_verify = ttk.Progressbar(self.tab_verify, orient='horizontal', mode='determinate')
        self.prog_verify.pack(fill='x', padx=15, pady=5)
        
        # Tabel Hasil
        columns = ("Status", "File", "Ukuran", "Detail")
        self.tree_verify = ttk.Treeview(self.tab_verify, columns=columns, show='headings')
        self.tree_verify.heading("Status", text="Status")
        self.tree_verify.heading("File", text="Path File Relatif")
        self.tree_verify.heading("Ukuran", text="Ukuran Byte")
        self.tree_verify.heading("Detail", text="Keterangan Tambahan")
        
        self.tree_verify.column("Status", width=100, minwidth=100, anchor='center', stretch=False)
        self.tree_verify.column("File", width=300)
        self.tree_verify.column("Ukuran", width=100, minwidth=100, anchor='e', stretch=False)
        self.tree_verify.column("Detail", width=250)
        
        # Scrollbar tabel
        scrollbar = ttk.Scrollbar(self.tab_verify, orient=tk.VERTICAL, command=self.tree_verify.yview)
        self.tree_verify.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        self.tree_verify.pack(fill='both', expand=True, padx=(15, 0), pady=5)
        
        # Styling Treeview rows
        self.tree_verify.tag_configure('MATCH', background='#c6efce')     # Hijau
        self.tree_verify.tag_configure('MODIFIED', background='#ffc7ce')  # Merah
        self.tree_verify.tag_configure('MISSING', background='#ffeb9c')   # Kuning
        self.tree_verify.tag_configure('UNTRACKED', background='#b8daff') # Biru

        self.verification_results = [] # Untuk keperluan export text/csv
        self.last_verify_meta = None # Info waktu & host untuk metadata laporan export

    # ==============================
    # UI SETUP: TAB 3 (CHECK INTEGRITAS 1 FILE)
    # ==============================
    def setup_check_tab(self):
        frame_input = ttk.LabelFrame(self.tab_check, text=" Pengaturan Pengecekan File ")
        frame_input.pack(fill='x', padx=15, pady=10)

        # File yang akan dicek
        self.check_file_var = tk.StringVar()
        ttk.Label(frame_input, text="File yang Dicek:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(
            frame_input, textvariable=self.check_file_var, width=60, state='readonly'
        ).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_check_file).grid(row=0, column=2, padx=5, pady=5)

        # Hash pembanding (expected)
        self.check_expected_hash_var = tk.StringVar()
        ttk.Label(frame_input, text="Hash Pembanding (Expected):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.check_expected_hash_var, width=60).grid(row=1, column=1, padx=5, pady=5)

        # Eksekusi
        self.btn_check = ttk.Button(self.tab_check, text="Mulai Cek Integritas", command=self.start_check_single_file)
        self.btn_check.pack(pady=5)

        self.lbl_check_status = ttk.Label(self.tab_check, text="Menunggu instruksi...")
        self.lbl_check_status.pack(anchor='w', padx=15, pady=2)

        # Hasil Pengecekan
        frame_result = ttk.LabelFrame(self.tab_check, text=" Hasil Pengecekan ")
        frame_result.pack(fill='x', padx=15, pady=10)

        self.lbl_check_result_status = ttk.Label(frame_result, text="Menunggu Proses Dimulai...", font=('TkDefaultFont', 11, 'bold'))
        self.lbl_check_result_status.grid(row=0, column=0, columnspan=2, padx=5, pady=(5, 10), sticky='w')

        ttk.Label(frame_result, text="Hash Aktual (SHA256):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.check_actual_hash_var = tk.StringVar()
        ttk.Entry(
            frame_result, textvariable=self.check_actual_hash_var, width=70, state='readonly'
        ).grid(row=1, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(frame_result, text="Hash Pembanding:").grid(row=2, column=0, padx=5, pady=5, sticky='w')
        self.check_result_expected_hash_var = tk.StringVar()
        ttk.Entry(
            frame_result, textvariable=self.check_result_expected_hash_var, width=70, state='readonly'
        ).grid(row=2, column=1, padx=5, pady=5, sticky='w')

        ttk.Label(frame_result, text="Ukuran File:").grid(row=3, column=0, padx=5, pady=5, sticky='w')
        self.lbl_check_size = ttk.Label(frame_result, text="-")
        self.lbl_check_size.grid(row=3, column=1, padx=5, pady=5, sticky='w')

    # ==============================
    # FUNGSI-FUNGSI BROWSE
    # ==============================
    def browse_src_folder(self):
        folder = filedialog.askdirectory(title="Pilih Folder Sumber Data CSV")
        if folder: self.src_folder_var.set(folder)

    def browse_manifest_out(self):
        file = filedialog.asksaveasfilename(title="Simpan Manifest", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file: self.manifest_out_var.set(file)

    def browse_tgt_folder(self):
        folder = filedialog.askdirectory(title="Pilih Folder Target (Termasuk seluruh Sub-Folder)")
        if folder: self.tgt_folder_var.set(folder)

    def browse_manifest_in(self):
        file = filedialog.askopenfilename(title="Pilih File Manifest", filetypes=[("CSV Files", "*.csv")])
        if file: self.manifest_in_var.set(file)

    def browse_check_file(self):
        file = filedialog.askopenfilename(title="Pilih File yang Akan Dicek")
        if file: self.check_file_var.set(file)

    # ==============================
    # ENGINE LOGIC (Jalan di Thread)
    # ==============================
    def calculate_file_hash(self, filepath, count_lines=True):
        sha256 = hashlib.sha256()
        total_size = 0
        total_lines = 0
        
        try:
            with open(filepath, 'rb') as f:
                while chunk := f.read(CHUNK_SIZE):
                    sha256.update(chunk)
                    total_size += len(chunk)
                    if count_lines:
                        total_lines += chunk.count(b'\n')
        except Exception as e:
            return None, 0, 0, str(e)
            
        return sha256.hexdigest(), total_size, total_lines, "OK"

    def thread_generate_manifest(self, src_dir, out_csv, count_lines, include_subfolder, start_dt):
        files_to_process = []
        for root_dir, _, files in os.walk(src_dir):
            for file in files:
                files_to_process.append(os.path.join(root_dir, file))
            if not include_subfolder:
                break
        
        total_files = len(files_to_process)
        if total_files == 0:
            self.msg_queue.put({"type": "error", "msg": "Tidak ada file ditemukan di folder sumber."})
            return
        
        manifest_data = []
        
        for idx, filepath in enumerate(files_to_process, 1):
            rel_path = os.path.relpath(filepath, src_dir)
            self.msg_queue.put({"type": "progress_manifest", "current": idx, "total": total_files, "file": rel_path})
            
            f_hash, f_size, f_lines, status = self.calculate_file_hash(filepath, count_lines)
            
            if f_hash:
                manifest_data.append([rel_path, f_hash, f_size, f_lines])
            else:
                self.msg_queue.put({"type": "log_manifest", "msg": f"Gagal membaca {rel_path}: {status}"})

        # Simpan ke CSV
        try:
            with open(out_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Relative_Path", "SHA256_Hash", "Byte_Size", "Row_Count"])
                writer.writerows(manifest_data)
                
            # Hitung Master Hash
            master_hash, _, _, _ = self.calculate_file_hash(out_csv, count_lines=False)

            end_dt = datetime.datetime.now()

            self.msg_queue.put({
                "type": "done_manifest",
                "master_hash": master_hash,
                "total_files": len(manifest_data),
                "start_dt": start_dt,
                "end_dt": end_dt,
                "duration": end_dt - start_dt,
                "src_dir": src_dir,
                "out_csv": out_csv,
                "include_subfolder": include_subfolder,
                "user_id": getpass.getuser(),
            })
        except Exception as e:
            self.msg_queue.put({"type": "error", "msg": f"Gagal menyimpan CSV: {e}"})

    def thread_verify_integrity(self, tgt_dir, in_csv, expected_master_hash, include_subfolder, start_dt):
        # 0. Verifikasi Master Hash manifest sebelum lanjut apapun (wajib).
        # Master Hash = SHA256 dari file manifest.csv itu sendiri (lihat thread_generate_manifest).
        # Kalau tidak cocok, manifest kemungkinan sudah diedit/rusak -> hasil verifikasi
        # per-file di bawahnya tidak bisa dipercaya, jadi proses dihentikan di sini.
        actual_master_hash, _, _, hash_status = self.calculate_file_hash(in_csv, count_lines=False)
        if actual_master_hash is None:
            self.msg_queue.put({"type": "error", "msg": f"Gagal membaca Manifest: {hash_status}"})
            return
        if actual_master_hash.lower() != expected_master_hash.strip().lower():
            self.msg_queue.put({
                "type": "master_hash_mismatch",
                "expected": expected_master_hash.strip(),
                "actual": actual_master_hash,
            })
            return

        # 1. Baca Manifest
        manifest_dict = {}
        try:
            with open(in_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    manifest_dict[row["Relative_Path"]] = {
                        "hash": row["SHA256_Hash"],
                        "size": row["Byte_Size"],
                        "lines": row.get("Row_Count", "0")
                    }
        except Exception as e:
            self.msg_queue.put({"type": "error", "msg": f"Gagal membaca Manifest: {e}"})
            return

        # 2. Dapatkan file-file di HDD
        hdd_files = []
        for root_dir, _, files in os.walk(tgt_dir):
            for file in files:
                hdd_files.append(os.path.join(root_dir, file))
            if not include_subfolder:
                break

        # Lookup hash -> path manifest, untuk mendeteksi file yang dipindah/rename
        hash_to_path = {meta["hash"]: rel_path for rel_path, meta in manifest_dict.items()}

        total_steps = len(manifest_dict) + len(hdd_files) # Aproksimasi untuk progress bar
        current_step = 0
        
        # 3. Proses Verifikasi
        checked_files = set()
        
        for filepath in hdd_files:
            rel_path = os.path.relpath(filepath, tgt_dir)
            current_step += 1
            self.msg_queue.put({"type": "progress_verify", "current": current_step, "total": total_steps, "file": rel_path})
            
            if rel_path in manifest_dict:
                # File terdaftar di manifest, cocokkan hash
                expected_hash = manifest_dict[rel_path]["hash"]
                actual_hash, actual_size, _, _ = self.calculate_file_hash(filepath, count_lines=False)
                
                if actual_hash == expected_hash:
                    status = "MATCH"
                    detail = "File terverifikasi identik."
                else:
                    status = "MODIFIED"
                    detail = f"Hash Beda! Expected: {expected_hash[:8]}... Actual: {actual_hash[:8]}..."
                
                self.msg_queue.put({"type": "result_verify", "status": status, "file": rel_path, "size": actual_size, "detail": detail})
                checked_files.add(rel_path)
            else:
                # File ada di HDD tapi tidak ada di manifest (path tidak cocok).
                # Tetap hitung hash untuk cek apakah isinya sama dengan salah satu
                # entri manifest (kemungkinan file dipindah/rename) atau memang baru.
                actual_hash, actual_size, _, _ = self.calculate_file_hash(filepath, count_lines=False)

                if actual_hash in hash_to_path:
                    detail = (f"Hash SAMA dengan manifest (path asal: {hash_to_path[actual_hash]}). "
                               "Isi file identik, kemungkinan dipindah/rename, bukan file baru.")
                else:
                    detail = "Hash tidak ditemukan di Manifest manapun. File baru/berbeda isi."

                self.msg_queue.put({"type": "result_verify", "status": "UNTRACKED", "file": rel_path, "size": actual_size, "detail": detail})

        # 4. Cari file yang ada di manifest tapi hilang di HDD
        for rel_path, meta in manifest_dict.items():
            current_step += 1
            if rel_path not in checked_files:
                self.msg_queue.put({"type": "result_verify", "status": "MISSING", "file": rel_path, "size": meta["size"], "detail": "Hilang dari HDD eksternal."})
            self.msg_queue.put({"type": "progress_verify", "current": current_step, "total": total_steps, "file": rel_path})

        end_dt = datetime.datetime.now()
        self.msg_queue.put({
            "type": "done_verify",
            "total": total_steps,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "duration": end_dt - start_dt,
            "host_name": socket.gethostname(),
            "user_id": getpass.getuser(),
        })

    def thread_check_single_file(self, filepath, expected_hash):
        actual_hash, size, _, status = self.calculate_file_hash(filepath, count_lines=False)
        if actual_hash is None:
            self.msg_queue.put({"type": "error", "msg": f"Gagal membaca file: {status}", "source": "check"})
            return

        expected_hash_clean = expected_hash.strip()
        result_status = "MATCH" if actual_hash.lower() == expected_hash_clean.lower() else "MISMATCH"

        self.msg_queue.put({
            "type": "done_check_file",
            "status": result_status,
            "actual_hash": actual_hash,
            "expected_hash": expected_hash_clean,
            "size": size,
            "file": os.path.basename(filepath),
        })

    # ==============================
    # GUI EVENT HANDLERS & QUEUE LOOP
    # ==============================
    def start_generate_manifest(self):
        src = self.src_folder_var.get()
        out = self.manifest_out_var.get()
        
        if not src or not out:
            messagebox.showwarning("Peringatan", "Harap isi Folder Sumber dan Lokasi Simpan Manifest.")
            return
            
        self.btn_generate.config(state='disabled')
        self.btn_copy_log.pack_forget()
        self.txt_manifest_log.config(state='normal')
        self.txt_manifest_log.delete('1.0', tk.END)
        self.txt_manifest_log.config(state='disabled')
        self.prog_manifest['value'] = 0

        count_lines = self.count_lines_var.get()
        include_subfolder = self.include_subfolder_var.get()
        start_dt = datetime.datetime.now()

        # Mulai Background Thread
        thread = threading.Thread(target=self.thread_generate_manifest, args=(src, out, count_lines, include_subfolder, start_dt), daemon=True)
        thread.start()

    def start_verify(self):
        tgt = self.tgt_folder_var.get()
        mani = self.manifest_in_var.get()
        expected_master_hash = self.expected_master_hash_var.get().strip()
        include_subfolder = self.verify_include_subfolder_var.get()

        if not tgt or not mani:
            messagebox.showwarning("Peringatan", "Harap isi Target Folder dan File Manifest.")
            return

        if not expected_master_hash:
            messagebox.showwarning("Peringatan", "Master Hash Manifest (dari BAST) wajib diisi sebelum verifikasi dapat dijalankan.")
            return

        self.btn_verify.config(state='disabled')
        self.btn_export_log.config(state='disabled')
        self.tree_verify.delete(*self.tree_verify.get_children())
        self.verification_results.clear()
        self.prog_verify['value'] = 0

        start_dt = datetime.datetime.now()

        # Mulai Background Thread
        thread = threading.Thread(target=self.thread_verify_integrity, args=(tgt, mani, expected_master_hash, include_subfolder, start_dt), daemon=True)
        thread.start()

    def start_check_single_file(self):
        filepath = self.check_file_var.get()
        expected_hash = self.check_expected_hash_var.get().strip()

        if not filepath:
            messagebox.showwarning("Peringatan", "Harap pilih file yang akan dicek.")
            return

        if not expected_hash:
            messagebox.showwarning("Peringatan", "Harap isi Hash Pembanding.")
            return

        self.btn_check.config(state='disabled')
        self.lbl_check_result_status.config(text="Memproses...", foreground='black')
        self.check_actual_hash_var.set("")
        self.check_result_expected_hash_var.set("")
        self.lbl_check_size.config(text="-")
        self.lbl_check_status.config(text=f"Menghitung hash: {os.path.basename(filepath)}")

        # Mulai Background Thread
        thread = threading.Thread(target=self.thread_check_single_file, args=(filepath, expected_hash), daemon=True)
        thread.start()

    # Urutan prioritas status: yang paling butuh perhatian tampil paling atas
    VERIFY_STATUS_ORDER = {"MODIFIED": 0, "MISSING": 1, "UNTRACKED": 2, "MATCH": 3}

    def sort_verification_results(self):
        """Urutkan hasil verifikasi: status (MODIFIED dulu) -> ukuran byte (besar dulu) -> nama file (A-Z),
        lalu render ulang tabel supaya urutan tampilan konsisten dengan urutan export."""
        def sort_key(row):
            status, file, size, _detail = row
            try:
                size_val = int(size)
            except (TypeError, ValueError):
                size_val = 0
            return (self.VERIFY_STATUS_ORDER.get(status, 99), -size_val, file.lower())

        self.verification_results.sort(key=sort_key)

        self.tree_verify.delete(*self.tree_verify.get_children())
        for status, file, size, detail in self.verification_results:
            self.tree_verify.insert("", tk.END, values=(status, file, size, detail), tags=(status,))

    def export_verification_log(self):
        if not self.verification_results: return
        file_path = filedialog.asksaveasfilename(title="Simpan Laporan", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            # Bangun isi tabel (header + baris hasil) dulu di memori, agar hash dihitung
            # dari isi laporan yang sesungguhnya -> bukti integritas laporan itu sendiri.
            body_buffer = io.StringIO()
            body_writer = csv.writer(body_buffer)
            body_writer.writerow(["Status", "Relative_Path", "Size_Bytes", "Detail"])
            body_writer.writerows(self.verification_results)
            body_text = body_buffer.getvalue()

            report_hash = hashlib.sha256(body_text.encode('utf-8')).hexdigest()

            # Simpan file CSV (hanya data tabel, tanpa metadata header)
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                f.write(body_text)

            # Update status label & tampilkan pop-up sukses dengan hash + Copy button
            self.root.after(0, self.lbl_verify_status.config, {"text": f"Export sukses. Hash: {report_hash[:16]}... (lihat pop-up)"})
            self.root.after(0, self.show_export_success_dialog, report_hash)
        # Log message ke text box di tab verify tidak ada, jadi cukup update status label

    def show_export_success_dialog(self, report_hash):
        """Pop-up sukses export dengan hash dan tombol Copy to Clipboard."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Laporan Verifikasi Berhasil Disimpan")
        dialog.geometry("500x180")
        dialog.resizable(False, False)
        dialog.grab_set()

        # Label pesan utama
        lbl_msg = ttk.Label(dialog, text="Laporan Verifikasi berhasil disimpan.", font=("Segoe UI", 10))
        lbl_msg.pack(pady=(15, 10), padx=15)

        # Frame untuk hash
        frame_hash = ttk.Frame(dialog)
        frame_hash.pack(fill=tk.X, padx=15, pady=5)

        lbl_hash_label = ttk.Label(frame_hash, text="Verification Report Hash:", font=("Segoe UI", 9, "bold"))
        lbl_hash_label.pack(anchor=tk.W, pady=(0, 3))

        # Entry readonly untuk hash (bisa di-select & copy).
        # Pakai tk.Entry (bukan ttk.Entry) karena ttk.Entry readonly di tema
        # 'vista' Windows punya bug: teks tidak tampil meski textvariable terisi.
        hash_var = tk.StringVar(value=report_hash)
        entry_hash = tk.Entry(
            frame_hash, textvariable=hash_var, state='readonly', width=70,
            readonlybackground='white', fg='black', relief=tk.FLAT,
            highlightthickness=1, highlightbackground='#7a7a7a', highlightcolor='#7a7a7a', borderwidth=0
        )
        entry_hash.pack(fill=tk.X, pady=(0, 5))

        # Frame tombol
        frame_buttons = ttk.Frame(dialog)
        frame_buttons.pack(fill=tk.X, padx=15, pady=(10, 15))

        # Tombol Copy to Clipboard
        def copy_hash():
            dialog.clipboard_clear()
            dialog.clipboard_append(report_hash)
            dialog.update()
            messagebox.showinfo("Disalin", "Hash berhasil disalin ke clipboard.", parent=dialog)

        btn_copy = ttk.Button(frame_buttons, text="📋 Copy to Clipboard", command=copy_hash)
        btn_copy.pack(side=tk.LEFT, padx=(0, 5))

        # Tombol OK
        btn_ok = ttk.Button(frame_buttons, text="OK", command=dialog.destroy)
        btn_ok.pack(side=tk.LEFT)

    def format_duration_hhmmss(self, td):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def format_duration_verbose(self, td):
        total_seconds = int(td.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours} jam {minutes} menit {seconds} detik"

    def format_tanggal_indonesia(self, dt):
        return f"{dt.day:02d} {BULAN_ID[dt.month - 1]} {dt.year}"

    def copy_log_to_clipboard(self):
        log_text = self.txt_manifest_log.get('1.0', tk.END).strip()
        if not log_text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(log_text)
        self.root.update()
        messagebox.showinfo("Disalin", "Log berhasil disalin ke clipboard.")

    def log_to_manifest_text(self, text):
        self.txt_manifest_log.config(state='normal')
        self.txt_manifest_log.insert(tk.END, text + "\n")
        self.txt_manifest_log.see(tk.END)
        self.txt_manifest_log.config(state='disabled')

    def check_queue_loop(self):
        while not self.msg_queue.empty():
            msg = self.msg_queue.get()
            
            if msg["type"] == "progress_manifest":
                self.prog_manifest['maximum'] = msg["total"]
                self.prog_manifest['value'] = msg["current"]
                self.lbl_manifest_status.config(text=f"Memproses: {msg['file']}")
                
            elif msg["type"] == "log_manifest":
                self.log_to_manifest_text(msg["msg"])
                
            elif msg["type"] == "done_manifest":
                self.lbl_manifest_status.config(text="Selesai!")
                self.btn_generate.config(state='normal')
                
                start_dt = msg["start_dt"]
                end_dt = msg["end_dt"]
                subfolder_line = ("✅ Termasuk sub-folder" if msg["include_subfolder"]
                                   else "❌ Tidak termasuk sub-folder")
                summary = (f"=== PROSES SELESAI ===\n"
                           f"Folder Data Sumber: {msg['src_dir']}\n"
                           f"{subfolder_line}\n"
                           f"Total File Terproses: {msg['total_files']}\n"
                           f"Simpan Manifest Ke {msg['out_csv']}\n"
                           f"Tanggal Proses    : {start_dt.strftime('%d-%m-%Y')}\n"
                           f"Waktu Mulai       : {start_dt.strftime('%H:%M:%S')} waktu komputer setempat\n"
                           f"Waktu Selesai     : {end_dt.strftime('%H:%M:%S')} waktu komputer setempat\n"
                           f"Durasi Proses     : {self.format_duration_hhmmss(msg['duration'])}\n"
                           f"User Id           : {msg['user_id']}\n"
                           f"MASTER HASH (Manifest): {msg['master_hash']}\n"
                           f"WAJIB Catat Master Hash ini ke dalam Berita Acara (BAST).")
                self.log_to_manifest_text(summary)
                self.btn_copy_log.pack(side=tk.LEFT, padx=5)
                messagebox.showinfo("Berhasil", "Pembuatan Manifest Selesai!")
                
            elif msg["type"] == "progress_verify":
                self.prog_verify['maximum'] = msg["total"]
                self.prog_verify['value'] = msg["current"]
                self.lbl_verify_status.config(text=f"Mengecek: {msg['file']}")
                
            elif msg["type"] == "result_verify":
                self.tree_verify.insert("", tk.END, values=(msg["status"], msg["file"], msg["size"], msg["detail"]), tags=(msg["status"],))
                self.verification_results.append([msg["status"], msg["file"], msg["size"], msg["detail"]])
                self.tree_verify.yview_moveto(1) # Auto scroll ke bawah
                
            elif msg["type"] == "done_verify":
                self.last_verify_meta = {
                    "start_dt": msg["start_dt"],
                    "end_dt": msg["end_dt"],
                    "duration": msg["duration"],
                    "host_name": msg["host_name"],
                    "user_id": msg["user_id"],
                }
                self.prog_verify['value'] = self.prog_verify['maximum']
                self.sort_verification_results()
                self.lbl_verify_status.config(text="Verifikasi Selesai!")
                self.btn_verify.config(state='normal')
                self.btn_export_log.config(state='normal')
                messagebox.showinfo("Verifikasi Selesai", "Proses verifikasi file telah selesai.\nSilakan ekspor log untuk laporan.")
                
            elif msg["type"] == "master_hash_mismatch":
                self.lbl_verify_status.config(text="Verifikasi DIBATALKAN: Master Hash manifest tidak cocok!")
                self.btn_verify.config(state='normal')
                messagebox.showerror(
                    "Master Hash Tidak Cocok",
                    "Verifikasi dihentikan karena Master Hash manifest tidak sesuai dengan yang tercatat di BAST.\n"
                    "Ini menandakan file manifest.csv kemungkinan sudah diubah/rusak, sehingga hasil verifikasi "
                    "per-file di dalamnya tidak bisa dipercaya.\n\n"
                    f"Expected : {msg['expected']}\n"
                    f"Actual   : {msg['actual']}"
                )

            elif msg["type"] == "done_check_file":
                self.btn_check.config(state='normal')
                self.lbl_check_status.config(text=f"Selesai: {msg['file']}")

                self.check_actual_hash_var.set(msg["actual_hash"])
                self.check_result_expected_hash_var.set(msg["expected_hash"])
                self.lbl_check_size.config(text=f"{msg['size']:,} bytes")

                if msg["status"] == "MATCH":
                    self.lbl_check_result_status.config(text="✅ MATCH - Hash Identik", foreground='#1e7e34')
                else:
                    self.lbl_check_result_status.config(text="❌ MISMATCH - Hash Berbeda", foreground='#c82333')

            elif msg["type"] == "error":
                messagebox.showerror("Error", msg["msg"])
                self.btn_generate.config(state='normal')
                self.btn_verify.config(state='normal')
                if msg.get("source") == "check":
                    self.btn_check.config(state='normal')
                    self.lbl_check_result_status.config(text="Gagal memproses file.", foreground='#c82333')
                
        # Looping pengecekan antrean setiap 100ms
        self.root.after(100, self.check_queue_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = TaxDataIntegrityApp(root)
    root.mainloop()