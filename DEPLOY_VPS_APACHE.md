# Panduan Deployment ke VPS menggunakan Apache

Panduan langkah demi langkah men-deploy aplikasi **Sistem Prediksi USD/IDR (Flask)** ke
sebuah VPS (Ubuntu/Debian) dengan **Apache** sebagai web server.

Aplikasi ini adalah aplikasi **WSGI** (Flask). Apache tidak menjalankan Python secara langsung,
jadi ada dua cara umum:

| Metode | Ringkas | Rekomendasi |
|---|---|---|
| **A. Apache reverse proxy → Gunicorn** | Apache meneruskan request ke Gunicorn (WSGI server) yang dikelola `systemd`. | ✅ **Disarankan** — paling stabil, mudah di-restart & dipantau, `gunicorn` sudah ada di `requirements.txt`. |
| **B. Apache + mod_wsgi** | Apache menjalankan Python langsung lewat modul `mod_wsgi`. | Alternatif "Apache murni" tanpa proses terpisah. |

> Asumsi: VPS Ubuntu 22.04/24.04, akses `sudo`, domain `contoh.com` mengarah ke IP VPS
> (ganti sesuai milik Anda). Jika belum punya domain, ganti `ServerName` dengan IP VPS.

---

## 0. Persiapan Awal (umum untuk kedua metode)

### 0.1 Update sistem & pasang paket dasar
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip apache2 git
```

### 0.2 Upload kode aplikasi ke VPS
Pilih salah satu:
```bash
# Opsi 1: lewat Git (jika sudah di GitHub)
sudo mkdir -p /var/www
cd /var/www
sudo git clone <URL-REPO-ANDA> usdidr
```
```bash
# Opsi 2: lewat SCP dari komputer lokal (jalankan di komputer lokal)
scp -r "DASD_SIAB_Program_Kelompok" user@IP_VPS:/tmp/usdidr
# lalu di VPS:
sudo mv /tmp/usdidr /var/www/usdidr
```

Struktur akhir yang diharapkan: `/var/www/usdidr/app.py`, `.../ml_utils.py`, `.../models/`, dst.

### 0.3 Buat virtual environment & pasang dependensi
```bash
cd /var/www/usdidr
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
```

### 0.4 Siapkan SECRET_KEY (jangan hardcode di kode)
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# salin hasilnya — dipakai sebagai SECRET_KEY pada langkah systemd / Apache di bawah
```

### 0.5 Hak akses folder (agar Apache/Gunicorn bisa membaca)
```bash
sudo chown -R www-data:www-data /var/www/usdidr
```

### 0.6 Firewall
```bash
sudo ufw allow OpenSSH
sudo ufw allow "Apache Full"   # buka port 80 & 443
sudo ufw enable
```

---

## Metode A — Apache reverse proxy → Gunicorn (disarankan)

### A.1 Uji Gunicorn manual dulu
Objek Flask bernama `app` di dalam `app.py`, jadi target WSGI-nya `app:app`.
```bash
cd /var/www/usdidr
source venv/bin/activate
gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
# buka browser ke http://IP_VPS:8000 (sementara) untuk memastikan jalan, lalu Ctrl+C
deactivate
```

### A.2 Buat service systemd agar Gunicorn berjalan permanen
Buat file `/etc/systemd/system/usdidr.service`:
```bash
sudo nano /etc/systemd/system/usdidr.service
```
Isi:
```ini
[Unit]
Description=Gunicorn untuk aplikasi prediksi USD/IDR
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/usdidr
Environment="SECRET_KEY=GANTI_DENGAN_HASIL_TOKEN_HEX"
ExecStart=/var/www/usdidr/venv/bin/gunicorn --workers 3 --bind 127.0.0.1:8000 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```
Aktifkan:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now usdidr
sudo systemctl status usdidr      # pastikan "active (running)"
```

### A.3 Aktifkan modul proxy Apache
```bash
sudo a2enmod proxy proxy_http headers
```

### A.4 Buat virtual host Apache
```bash
sudo nano /etc/apache2/sites-available/usdidr.conf
```
Isi:
```apache
<VirtualHost *:80>
    ServerName contoh.com
    ServerAlias www.contoh.com

    ProxyPreserveHost On
    ProxyPass        / http://127.0.0.1:8000/
    ProxyPassReverse / http://127.0.0.1:8000/

    # Sajikan file statis langsung dari Apache (lebih cepat, kurangi beban Gunicorn)
    Alias /static /var/www/usdidr/static
    <Directory /var/www/usdidr/static>
        Require all granted
    </Directory>

    ErrorLog  ${APACHE_LOG_DIR}/usdidr_error.log
    CustomLog ${APACHE_LOG_DIR}/usdidr_access.log combined
</VirtualHost>
```

> Catatan: agar `/static` benar-benar dilayani Apache (bukan diteruskan ke Gunicorn),
> tambahkan pengecualian proxy berikut **di atas** baris `ProxyPass /` jika perlu:
> `ProxyPass /static !`

### A.5 Aktifkan site & restart
```bash
sudo a2ensite usdidr.conf
sudo a2dissite 000-default.conf   # nonaktifkan halaman default Apache
sudo apache2ctl configtest        # harus "Syntax OK"
sudo systemctl reload apache2
```

Buka `http://contoh.com` (atau `http://IP_VPS`). Selesai. **Lanjut ke bagian HTTPS** di bawah.

Setiap kali kode berubah:
```bash
cd /var/www/usdidr && git pull            # jika pakai git
sudo systemctl restart usdidr             # muat ulang aplikasi
```

---

## Metode B — Apache + mod_wsgi (alternatif "Apache murni")

### B.1 Pasang mod_wsgi untuk Python 3
```bash
sudo apt install -y libapache2-mod-wsgi-py3
sudo a2enmod wsgi
```

### B.2 Pastikan ada file entry point WSGI
Repo sudah punya `passenger_wsgi.py` yang mengekspor objek `application`
(`from app import app as application`) — mod_wsgi bisa langsung memakainya.

### B.3 Virtual host Apache dengan daemon mode
```bash
sudo nano /etc/apache2/sites-available/usdidr.conf
```
Isi:
```apache
<VirtualHost *:80>
    ServerName contoh.com
    ServerAlias www.contoh.com

    # Jalankan di virtualenv proyek; daemon terpisah agar stabil
    WSGIDaemonProcess usdidr python-home=/var/www/usdidr/venv python-path=/var/www/usdidr
    WSGIProcessGroup usdidr
    WSGIScriptAlias / /var/www/usdidr/passenger_wsgi.py

    # SECRET_KEY lewat environment Apache
    SetEnv SECRET_KEY GANTI_DENGAN_HASIL_TOKEN_HEX

    <Directory /var/www/usdidr>
        Require all granted
    </Directory>

    Alias /static /var/www/usdidr/static
    <Directory /var/www/usdidr/static>
        Require all granted
    </Directory>

    ErrorLog  ${APACHE_LOG_DIR}/usdidr_error.log
    CustomLog ${APACHE_LOG_DIR}/usdidr_access.log combined
</VirtualHost>
```

> Catatan: `SetEnv` tidak selalu terbaca oleh `os.environ` di semua konfigurasi mod_wsgi.
> Bila `SECRET_KEY` tidak terbaca, alternatif paling andal: simpan di file `.env` lalu muat
> di awal `app.py`, **atau** gunakan Metode A yang memakai `systemd Environment=`.

### B.4 Aktifkan & restart
```bash
sudo a2ensite usdidr.conf
sudo a2dissite 000-default.conf
sudo apache2ctl configtest
sudo systemctl reload apache2
```

Setiap kali kode berubah, cukup *touch* file WSGI agar mod_wsgi memuat ulang:
```bash
sudo touch /var/www/usdidr/passenger_wsgi.py
```

---

## HTTPS (SSL gratis via Let's Encrypt) — sangat disarankan

```bash
sudo apt install -y certbot python3-certbot-apache
sudo certbot --apache -d contoh.com -d www.contoh.com
# ikuti prompt; certbot otomatis menambah konfigurasi :443 & redirect 80→443
sudo systemctl reload apache2
```
Perpanjangan otomatis sudah aktif; uji dengan:
```bash
sudo certbot renew --dry-run
```

---

## Pengujian Pasca-Deploy

```bash
# dari komputer mana pun
curl -I http://contoh.com/            # harus 200 (atau 301 ke https bila SSL aktif)
curl    http://contoh.com/api/prediksi   # harus mengembalikan JSON prediksi
```
Cek juga di browser: halaman Beranda, Dataset, Prediksi (coba input tak wajar → ditolak),
Forecast (grafik tampil), Evaluasi, Insight, Panduan, dan **toggle tema terang/gelap**.

---

## Troubleshooting

| Gejala | Penyebab umum & solusi |
|---|---|
| **502 / 503 (Metode A)** | Gunicorn mati. Cek `sudo systemctl status usdidr` & `journalctl -u usdidr -e`. |
| **500 Internal Server Error** | Lihat log: `sudo tail -n 50 /var/log/apache2/usdidr_error.log`. Sering karena dependensi belum terpasang di venv atau path model salah. |
| **CSS/gambar tidak muncul** | Alias `/static` salah atau `ProxyPass /static !` belum ditambahkan (Metode A). Cek hak akses `www-data`. |
| **Permission denied** | `sudo chown -R www-data:www-data /var/www/usdidr`. |
| **mod_wsgi pakai Python sistem, bukan venv** | Pastikan `python-home=/var/www/usdidr/venv` benar di `WSGIDaemonProcess`. |
| **Perubahan kode tak muncul** | Metode A: `sudo systemctl restart usdidr`. Metode B: `sudo touch .../passenger_wsgi.py`. |

Perintah log berguna:
```bash
sudo tail -f /var/log/apache2/usdidr_error.log     # error Apache real-time
journalctl -u usdidr -f                             # log Gunicorn real-time (Metode A)
```

---

## Checklist Keamanan Deployment (relevan dengan analisis keamanan tugas)

- [x] **Tidak ada credential di source code** — `SECRET_KEY` lewat `systemd Environment=` / env Apache.
- [x] **`.env` & file sensitif tidak ikut ter-deploy publik** — sudah di `.gitignore`.
- [x] **HTTPS aktif** (Let's Encrypt) — enkripsi data in-transit.
- [x] **Firewall (ufw)** hanya membuka port 80/443/SSH.
- [x] **Validasi input** pada form prediksi mencegah input tak wajar / manipulasi.
- [x] **Aplikasi tidak training ulang di server** — hanya memuat `.pkl` (ringan, permukaan serangan kecil).
- [ ] *(Opsional)* Nonaktifkan `debug` Flask di produksi — saat dijalankan via Gunicorn/mod_wsgi,
      `app.run(debug=True)` tidak terpakai, jadi sudah aman. Pastikan tidak menjalankan `python app.py` di produksi.
- [ ] *(Opsional)* Batasi akses dashboard dengan Basic Auth Apache bila perlu privasi.

> **Basic Auth opsional** (membatasi akses dashboard):
> ```bash
> sudo apt install -y apache2-utils
> sudo htpasswd -c /etc/apache2/.htpasswd admin
> ```
> lalu di dalam `<VirtualHost>`:
> ```apache
> <Location />
>     AuthType Basic
>     AuthName "Akses Terbatas"
>     AuthUserFile /etc/apache2/.htpasswd
>     Require valid-user
> </Location>
> ```
