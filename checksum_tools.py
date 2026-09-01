import os
import csv
import time
import hashlib
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

# Konfigurasi Buffer Size untuk HDD (4 MB)
CHUNK_SIZE = 4 * 1024 * 1024  

class TaxDataIntegrityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Tax Data Integrity Checker - BAST Pajak")
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
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

    # ==============================
    # UI SETUP: TAB 1 (BUAT MANIFEST)
    # ==============================
    def setup_manifest_tab(self):
        frame_input = ttk.LabelFrame(self.tab_manifest, text=" Pengaturan Sumber Data ")
        frame_input.pack(fill='x', padx=15, pady=10)
        
        # Source Folder
        self.src_folder_var = tk.StringVar()
        ttk.Label(frame_input, text="Folder Data CSV:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.src_folder_var, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_src_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # Output Manifest File
        self.manifest_out_var = tk.StringVar()
        ttk.Label(frame_input, text="Simpan Manifest Ke:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.manifest_out_var, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_manifest_out).grid(row=1, column=2, padx=5, pady=5)
        
        # Opsi Hitung Baris
        self.count_lines_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_input, text="Hitung jumlah baris (Newline \\n) - Cepat", variable=self.count_lines_var).grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        # Eksekusi
        self.btn_generate = ttk.Button(self.tab_manifest, text="Mulai Buat Manifest", command=self.start_generate_manifest)
        self.btn_generate.pack(pady=10)
        
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
        ttk.Label(frame_input, text="Folder HDD Eksternal:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.tgt_folder_var, width=60).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_tgt_folder).grid(row=0, column=2, padx=5, pady=5)
        
        # Input Manifest File
        self.manifest_in_var = tk.StringVar()
        ttk.Label(frame_input, text="File Manifest (CSV):").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        ttk.Entry(frame_input, textvariable=self.manifest_in_var, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame_input, text="Browse", command=self.browse_manifest_in).grid(row=1, column=2, padx=5, pady=5)
        
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
        
        self.tree_verify.column("Status", width=100, anchor='center')
        self.tree_verify.column("File", width=300)
        self.tree_verify.column("Ukuran", width=100, anchor='e')
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

    # ==============================
    # FUNGSI-FUNGSI BROWSE BROWSE
    # ==============================
    def browse_src_folder(self):
        folder = filedialog.askdirectory(title="Pilih Folder Sumber Data CSV")
        if folder: self.src_folder_var.set(folder)

    def browse_manifest_out(self):
        file = filedialog.asksaveasfilename(title="Simpan Manifest", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file: self.manifest_out_var.set(file)

    def browse_tgt_folder(self):
        folder = filedialog.askdirectory(title="Pilih Folder HDD Eksternal")
        if folder: self.tgt_folder_var.set(folder)

    def browse_manifest_in(self):
        file = filedialog.askopenfilename(title="Pilih File Manifest", filetypes=[("CSV Files", "*.csv")])
        if file: self.manifest_in_var.set(file)

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

    def thread_generate_manifest(self, src_dir, out_csv, count_lines):
        files_to_process = []
        for root_dir, _, files in os.walk(src_dir):
            for file in files:
                files_to_process.append(os.path.join(root_dir, file))
        
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
            
            self.msg_queue.put({
                "type": "done_manifest",
                "master_hash": master_hash,
                "total_files": len(manifest_data)
            })
        except Exception as e:
            self.msg_queue.put({"type": "error", "msg": f"Gagal menyimpan CSV: {e}"})

    def thread_verify_integrity(self, tgt_dir, in_csv):
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
                # File ada di HDD tapi tidak ada di manifest
                _, actual_size, _, _ = self.calculate_file_hash(filepath, count_lines=False)
                self.msg_queue.put({"type": "result_verify", "status": "UNTRACKED", "file": rel_path, "size": actual_size, "detail": "Ada di HDD, tidak ada di Manifest."})

        # 4. Cari file yang ada di manifest tapi hilang di HDD
        for rel_path, meta in manifest_dict.items():
            if rel_path not in checked_files:
                self.msg_queue.put({"type": "result_verify", "status": "MISSING", "file": rel_path, "size": meta["size"], "detail": "Hilang dari HDD eksternal."})
                
        self.msg_queue.put({"type": "done_verify"})

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
        self.txt_manifest_log.config(state='normal')
        self.txt_manifest_log.delete('1.0', tk.END)
        self.txt_manifest_log.config(state='disabled')
        self.prog_manifest['value'] = 0
        
        count_lines = self.count_lines_var.get()
        
        # Mulai Background Thread
        thread = threading.Thread(target=self.thread_generate_manifest, args=(src, out, count_lines), daemon=True)
        thread.start()

    def start_verify(self):
        tgt = self.tgt_folder_var.get()
        mani = self.manifest_in_var.get()
        
        if not tgt or not mani:
            messagebox.showwarning("Peringatan", "Harap isi Target Folder dan File Manifest.")
            return
            
        self.btn_verify.config(state='disabled')
        self.btn_export_log.config(state='disabled')
        self.tree_verify.delete(*self.tree_verify.get_children())
        self.verification_results.clear()
        self.prog_verify['value'] = 0
        
        # Mulai Background Thread
        thread = threading.Thread(target=self.thread_verify_integrity, args=(tgt, mani), daemon=True)
        thread.start()

    def export_verification_log(self):
        if not self.verification_results: return
        file_path = filedialog.asksaveasfilename(title="Simpan Laporan", defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file_path:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["Status", "Relative_Path", "Size_Bytes", "Detail"])
                writer.writerows(self.verification_results)
            messagebox.showinfo("Sukses", "Laporan Audit berhasil disimpan.")

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
                
                summary = (f"=== PROSES SELESAI ===\n"
                           f"Total File Terproses: {msg['total_files']}\n"
                           f"MASTER HASH (Manifest): {msg['master_hash']}\n"
                           f"Catat Master Hash ini ke dalam Berita Acara (BAST).")
                self.log_to_manifest_text(summary)
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
                self.lbl_verify_status.config(text="Verifikasi Selesai!")
                self.btn_verify.config(state='normal')
                self.btn_export_log.config(state='normal')
                messagebox.showinfo("Verifikasi Selesai", "Proses audit data telah selesai.\nSilakan ekspor log untuk laporan.")
                
            elif msg["type"] == "error":
                messagebox.showerror("Error", msg["msg"])
                self.btn_generate.config(state='normal')
                self.btn_verify.config(state='normal')
                
        # Looping pengecekan antrean setiap 100ms
        self.root.after(100, self.check_queue_loop)


if __name__ == "__main__":
    root = tk.Tk()
    app = TaxDataIntegrityApp(root)
    root.mainloop()