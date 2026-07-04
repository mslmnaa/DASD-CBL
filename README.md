# Sistem Prediksi Nilai Tukar USD/IDR Berbasis Machine Learning

Aplikasi web (Flask) untuk memprediksi nilai tukar USD/IDR dan mendukung keputusan bisnis
(perencanaan treasury dan lindung nilai), lengkap dengan dashboard eksplorasi data, prediksi
interaktif, forecast 30 hari, dan evaluasi model. Proyek Tugas Besar **DASD x SIAB**.

**Demo langsung:** https://msalman.my.id

---

## Ringkasan

- **Kasus:** prediksi arah dan nilai tukar USD/IDR harian dari indikator pasar dan makroekonomi.
- **Model juara:** Random Forest, dipilih berdasarkan akurasi arah (sekitar 65 persen).
- **Target:** log-return harian USD/IDR, lalu direkonstruksi kembali menjadi level nilai tukar.
- **Framework:** Flask (WSGI), di-deploy di VPS dengan Apache dan Gunicorn.

---

## Fitur Aplikasi

| Halaman | Fungsi |
|---|---|
| Beranda | Ringkasan indikator kunci dan prediksi hari berikutnya |
| Dataset dan EDA | Deskripsi dataset, statistik, dan visualisasi eksplorasi |
| Prediksi | Prediksi otomatis dan simulasi skenario dengan validasi input |
| Forecast 30 Hari | Proyeksi nilai tukar 30 hari ke depan dengan grafik interaktif |
| Evaluasi | Tabel dan grafik perbandingan model terhadap baseline |
| Insight | Temuan utama dan rekomendasi keputusan bisnis |
| Panduan | Dokumentasi cara penggunaan tiap fitur |

Endpoint data (JSON): `GET /api/prediksi` dan `GET /api/forecast`.

---

## Teknologi

- **Bahasa:** Python
- **Backend:** Flask (WSGI)
- **Machine Learning:** scikit-learn, XGBoost, pandas, numpy, joblib
- **Visualisasi:** Chart.js (interaktif) dan Matplotlib/Seaborn (grafik EDA)
- **Server produksi:** Gunicorn di belakang Apache (reverse proxy), HTTPS Let's Encrypt

---

## Struktur Proyek

```
.
├── app.py                 # Aplikasi Flask (routing)
├── ml_utils.py            # Logika ML: muat model, fitur, prediksi, forecast
├── passenger_wsgi.py      # Titik masuk WSGI alternatif
├── requirements.txt       # Dependensi Python
├── .env.example           # Contoh konfigurasi (salin menjadi .env)
├── .gitignore
├── models/                # Artefak model hasil training (.pkl)
│   ├── model_terbaik_usdidr_return.pkl
│   ├── scaler_minmax.pkl
│   └── metadata_fitur.pkl
├── data/                  # Dataset dan tabel hasil (CSV)
├── templates/             # Halaman HTML (Jinja2)
├── static/                # CSS dan gambar plot EDA/evaluasi
└── DEPLOY_VPS_APACHE.md   # Panduan deployment ke VPS (Apache + Gunicorn)
```

---

## Menjalankan Secara Lokal

```bash
# 1. (disarankan) buat virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 2. pasang dependensi
pip install -r requirements.txt

# 3. jalankan
python app.py
```

Buka http://127.0.0.1:5000

> Aplikasi hanya memuat model dari berkas `.pkl` (tidak melatih ulang di server), sehingga ringan dan cepat.

---

## Model dan Data

- **Dataset:** [Indonesia Financial Time Series Dataset 2010-2026 (Kaggle)](https://www.kaggle.com/datasets/raphaelnazareth/indonesia-financial-time-series-dataset-2010-2026)
  — 4.293 baris data harian, 10 kolom (target `USDIDR` plus 8 indikator: OIL, GOLD, SP500, IHSG, VIX, CPI, BI_rate, US_rate).
- **Pendekatan:** target adalah log-return harian (lebih stasioner), level direkonstruksi kembali dari prediksi return.
- **Perbandingan model:** Linear Regression, Random Forest, XGBoost, dan Baseline Naif.
  Random Forest terpilih karena akurasi arah tertinggi (sekitar 65 persen).

Melatih ulang model: jalankan notebook `Prediksi_USDIDR_Machine_Learning_v3.ipynb`, lalu salin
artefak `.pkl` ke `models/` dan `evaluasi_model.csv` ke `data/`.

---

## Deployment

Aplikasi berjalan di VPS Ubuntu dengan **Apache sebagai reverse proxy** yang meneruskan
permintaan ke **Gunicorn** (dikelola `systemd`), dengan **HTTPS** dari Let's Encrypt.
Langkah lengkap ada di [`DEPLOY_VPS_APACHE.md`](DEPLOY_VPS_APACHE.md).

Ringkasan cepat:

```bash
# di VPS, dari folder aplikasi
gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
# lalu Apache mem-proxy port 80/443 ke 127.0.0.1:8000
```

Kunci rahasia diatur lewat environment variable (`SECRET_KEY`), bukan ditulis di kode.

---

## Pengujian

| Jenis | Cara |
|---|---|
| Fungsi halaman | Akses tiap route, pastikan status 200 |
| Model | `/api/prediksi` mengembalikan return dan level yang wajar |
| Error/Input | Form skenario menolak input non-numerik dan di luar rentang |
| Dashboard | Grafik Chart.js tampil sesuai data |
| Deployment | Berjalan di lokal dan daring (https://msalman.my.id) |
| Keamanan | Tidak ada kredensial di kode; `.env` diabaikan git |

Smoke test cepat (semua route utama harus 200):

```bash
python -c "import app; c=app.app.test_client(); print([c.get(r).status_code for r in ['/','/dataset','/prediksi','/forecast','/evaluasi','/insight','/panduan']])"
```

---

## Keamanan dan Etika (ringkas)

- Tidak ada kredensial di kode; `SECRET_KEY` lewat environment variable.
- Validasi input pada form skenario (tipe dan rentang) mencegah error dan manipulasi.
- `.gitignore` mencegah `.env` dan berkas sensitif ikut ter-commit.
- HTTPS aktif dan firewall membatasi port yang terbuka.
- Disclaimer ditampilkan: alat bantu perencanaan, bukan saran finansial.

---

## Repository dan Kelompok

- **Source code:** https://github.com/mslmnaa/DASD-CBL
- **Kelompok:** [Nomor Kelompok] — [Nama Anggota]
- **Mata kuliah:** Desain Analisis Sains Data (DASD) x Sistem Informasi Analitik Bisnis (SIAB)
