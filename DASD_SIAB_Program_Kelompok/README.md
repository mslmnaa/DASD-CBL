# Sistem Prediksi Nilai Tukar USD/IDR Berbasis Machine Learning

Aplikasi web (Flask) untuk memprediksi nilai tukar USD/IDR dan mendukung keputusan bisnis
(treasury/hedging), lengkap dengan dashboard EDA, prediksi interaktif, forecast 30 hari, dan
evaluasi model. Proyek Tugas Besar **DASD × SIAB**.

- **Model juara:** Random Forest (dipilih berdasarkan akurasi arah).
- **Target:** log-return harian USD/IDR (lalu direkonstruksi ke level).
- **Framework:** Flask (WSGI) — kompatibel dengan cPanel *Setup Python App* (Passenger).

---

## 1. Struktur Folder

```
DASD_SIAB_Program_Kelompok/
├── app.py                 # Aplikasi Flask (routing)
├── passenger_wsgi.py      # Entry point cPanel (Passenger/WSGI)
├── ml_utils.py            # Logika ML: load model, fitur, prediksi, forecast
├── requirements.txt       # Dependensi Python
├── .env.example           # Contoh konfigurasi (salin -> .env)
├── .gitignore
├── models/                # Artefak model hasil training (.pkl)
│   ├── model_terbaik_usdidr_return.pkl
│   ├── scaler_minmax.pkl
│   └── metadata_fitur.pkl
├── data/                  # Dataset + tabel hasil (CSV)
├── templates/             # Halaman HTML (Jinja2)
└── static/                # CSS, gambar plot EDA/evaluasi
```

---

## 2. Menjalankan secara Lokal

```bash
# (disarankan) buat virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
python app.py
```

Buka **http://127.0.0.1:5000**

---

## 3. Deployment di cPanel (Setup Python App)

1. Login cPanel → **Setup Python App** → **Create Application**.
2. Isi:
   - **Python version:** 3.10+ (sesuai ketersediaan)
   - **Application root:** folder upload (mis. `DASD_SIAB_Program_Kelompok`)
   - **Application URL:** domain/subdomain tujuan
   - **Application startup file:** `passenger_wsgi.py`
   - **Application Entry point:** `application`
3. Upload seluruh isi folder ini ke *Application root* (File Manager / Git).
4. Di panel aplikasi, tambah **Environment variable**: `SECRET_KEY` = (string acak panjang).
   Buat dengan: `python -c "import secrets; print(secrets.token_hex(32))"`.
5. Klik **Run Pip Install** (memakai `requirements.txt`).
6. Klik **Restart**. Akses URL aplikasi.

> Catatan: aplikasi **tidak melatih ulang** model di server — hanya memuat `.pkl` (ringan & cepat).
> Bila ada perubahan model, latih ulang di notebook lalu ganti file di `models/`.

---

## 4. Halaman & Endpoint

| Route | Fungsi |
|---|---|
| `/` | Beranda + ringkasan KPI + prediksi besok |
| `/dataset` | Deskripsi dataset, statistik, visualisasi EDA |
| `/prediksi` | Prediksi otomatis + **simulasi skenario** (form input + validasi) |
| `/forecast` | Forecast 30 hari + grafik interaktif (Chart.js) |
| `/evaluasi` | Tabel & grafik perbandingan model vs baseline |
| `/insight` | Temuan utama & rekomendasi bisnis |
| `/panduan` | Dokumentasi penggunaan aplikasi (cara pakai tiap fitur) |
| `/api/prediksi` | JSON prediksi besok |
| `/api/forecast` | JSON forecast 30 hari |

---

## 5. Pengujian

| Jenis | Cara |
|---|---|
| Fungsi halaman | Akses tiap route → status 200 |
| Model | `/api/prediksi` mengembalikan return & level yang wajar |
| Error/Input | Form skenario menolak input non-numerik & di luar rentang (lihat pesan error) |
| Dashboard | Grafik Chart.js tampil sesuai data |
| Deployment | Jalan di lokal & cPanel |
| Keamanan | Tidak ada credential di source code; `.env` di-`.gitignore` |

Smoke test cepat (semua route 200):
```bash
python -c "import app; c=app.app.test_client(); print([c.get(r).status_code for r in ['/','/dataset','/prediksi','/forecast','/evaluasi','/insight']])"
```

---

## 6. Keamanan & Etika (ringkas)

- **Tidak ada credential di kode** — `SECRET_KEY` via environment variable.
- **Validasi input** pada form skenario (rentang & tipe) → cegah error/manipulasi input.
- **`.gitignore`** mencegah `.env` & file sensitif ikut ter-commit.
- **Disclaimer** ditampilkan: alat bantu perencanaan, bukan saran finansial.
- Detail lengkap analisis risiko ada di laporan (Bagian Analisis Keamanan TI).

---

## 7. Melatih Ulang Model (opsional)

Jalankan notebook `Prediksi_USDIDR_Machine_Learning_v3.ipynb` (di folder proyek induk).
Notebook akan menyimpan ulang artefak ke folder `output/`. Salin `*.pkl` ke `models/`
dan `evaluasi_model.csv` ke `data/`.
