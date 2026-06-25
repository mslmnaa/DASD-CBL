# -*- coding: utf-8 -*-
"""
Aplikasi web prediksi nilai tukar USD/IDR berbasis Machine Learning.
Framework: Flask (WSGI) -- kompatibel dengan cPanel "Setup Python App" (Passenger).

Menjalankan lokal:  python app.py   lalu buka http://127.0.0.1:5000
"""
import os
from flask import Flask, render_template, request, jsonify

import ml_utils as ml

app = Flask(__name__)
# SECRET_KEY dibaca dari environment (jangan hardcode credential di source code)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-key-ganti-di-produksi")

# Cache data siap-model sekali di memori (hindari komputasi berulang -> optimasi)
_D = None
def D():
    global _D
    if _D is None:
        _D = ml.get_model_data()
    return _D

# Rentang validasi input skenario = NILAI ABSOLUT wajar tiap indikator (lihat ml_utils).
BATAS_INPUT = ml.MAKRO_RANGE_ABS


@app.route("/")
def beranda():
    info = {
        "model": ml.META["nama_model"],
        "akurasi_arah": round(ml.META["metrik"]["Dir.Acc(%)"], 2),
        "rmse": round(ml.META["metrik"]["RMSE"], 2),
        "mape": round(ml.META["metrik"]["MAPE(%)"], 3),
        "tanggal": ml.META["tanggal_terakhir"],
        "harga": round(ml.META["harga_terakhir"], 2),
    }
    pred = ml.predict_next_day(D())
    return render_template("index.html", info=info, pred=pred, active="beranda")


@app.route("/dataset")
def dataset():
    return render_template("dataset.html", s=ml.dataset_summary(), active="dataset")


@app.route("/prediksi", methods=["GET", "POST"])
def prediksi():
    pred = ml.predict_next_day(D())
    skenario = None
    error = None
    # Default tiap field = nilai absolut terakhir dari dataset (acuan "tidak berubah").
    last = ml.last_macro_values(D())
    nilai_form = {k: f"{last[k]:g}" for k in BATAS_INPUT}

    if request.method == "POST":
        macro_abs = {}
        try:
            for col, (lo, hi) in BATAS_INPUT.items():
                raw = request.form.get(col, "").strip().replace(",", ".")
                nilai_form[col] = raw
                if raw == "":
                    raise ValueError(f"{col} wajib diisi (tidak boleh kosong).")
                try:
                    val = float(raw)
                except ValueError:
                    raise ValueError(f"{col} harus berupa angka (input: '{raw}').")
                if val <= 0:
                    raise ValueError(f"{col} harus bernilai positif, bukan {val:g}.")
                if not (lo <= val <= hi):
                    raise ValueError(
                        f"{col} di luar rentang wajar {lo:g}–{hi:g} {ml.MAKRO_SATUAN[col]} "
                        f"(input: {val:g})."
                    )
                macro_abs[col] = val
            skenario = ml.predict_scenario_abs(macro_abs, d_model=D())
        except ValueError as e:
            error = f"Input tidak valid: {e}"
        except Exception:
            error = "Terjadi kesalahan saat memproses input. Periksa kembali isian Anda."

    return render_template("prediksi.html", pred=pred, skenario=skenario, error=error,
                           batas=BATAS_INPUT, nilai=nilai_form, satuan=ml.MAKRO_SATUAN,
                           last=last, active="prediksi")


@app.route("/forecast")
def forecast():
    data = ml.forecast(horizon=30, d_model=D())
    hist = D()["USDIDR"].iloc[-60:]
    histori = [{"tanggal": str(i.date()), "nilai": round(float(v), 2)}
               for i, v in hist.items()]
    return render_template("forecast.html", forecast=data, histori=histori,
                           model=ml.META["nama_model"], active="forecast")


@app.route("/evaluasi")
def evaluasi():
    tabel = ml.get_eval_table()
    return render_template("evaluasi.html", tabel=tabel,
                           juara=ml.META["nama_model"], active="evaluasi")


@app.route("/insight")
def insight():
    return render_template("insight.html", active="insight")


@app.route("/panduan")
def panduan():
    """Dokumentasi penggunaan aplikasi (cara pakai tiap fitur)."""
    return render_template("panduan.html", batas=BATAS_INPUT, satuan=ml.MAKRO_SATUAN,
                           last=ml.last_macro_values(D()), active="panduan")


@app.route("/api/forecast")
def api_forecast():
    """Endpoint JSON (untuk integrasi/monitoring)."""
    return jsonify(ml.forecast(horizon=30, d_model=D()))


@app.route("/api/prediksi")
def api_prediksi():
    return jsonify(ml.predict_next_day(D()))


@app.errorhandler(404)
def not_found(e):
    return render_template("404.html", active=""), 404


if __name__ == "__main__":
    app.run(debug=True, port=5000)
