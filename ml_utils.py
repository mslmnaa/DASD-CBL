# -*- coding: utf-8 -*-
"""
Logika machine learning bersama untuk aplikasi prediksi USD/IDR.

Modul ini MEMUAT model yang sudah dilatih (tidak melatih ulang di server) sesuai
prinsip MLOps: model disimpan sebagai .pkl, aplikasi tinggal melakukan inferensi.
Feature engineering di sini IDENTIK dengan notebook training agar konsisten.
"""
import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")

MAKRO_PCT = ["OIL", "GOLD", "SP500", "IHSG", "VIX", "CPI"]

# Rentang NILAI ABSOLUT yang wajar untuk tiap indikator makro (validasi input).
# Dipakai untuk menolak input tak masuk akal (negatif, nol, atau di luar nalar).
MAKRO_RANGE_ABS = {
    "OIL":   (10.0,   200.0),    # harga minyak (USD/barel)
    "GOLD":  (800.0,  5000.0),   # harga emas (USD/oz)
    "SP500": (1000.0, 10000.0),  # indeks S&P 500
    "IHSG":  (3000.0, 10000.0),  # indeks IHSG
    "VIX":   (5.0,    90.0),     # indeks volatilitas
    "CPI":   (0.0,    20.0),     # inflasi Indonesia (%)
}
MAKRO_SATUAN = {
    "OIL": "USD/barel", "GOLD": "USD/oz", "SP500": "indeks",
    "IHSG": "indeks", "VIX": "indeks", "CPI": "%",
}
# Batas perubahan harian implisit yang masih wajar (vs nilai terakhir) — mencegah
# lompatan absurd dalam SATU hari yang membuat model berekstrapolasi di luar nalar.
MAX_PERUBAHAN_HARIAN_PCT = 25.0

# ------------------------------------------------------------------ artefak
_model = joblib.load(os.path.join(MODELS_DIR, "model_terbaik_usdidr_return.pkl"))
_scaler = joblib.load(os.path.join(MODELS_DIR, "scaler_minmax.pkl"))
META = joblib.load(os.path.join(MODELS_DIR, "metadata_fitur.pkl"))
FEATURE_COLS = META["feature_cols"]


# ------------------------------------------------------------------ data prep
def _build_features(df):
    """Bangun fitur stasioner (return) identik dengan notebook training."""
    df = df.sort_values("Date").reset_index(drop=True)
    kolom_numerik = df.select_dtypes(include=[np.number]).columns.tolist()

    # Koreksi kesalahan input USDIDR (spike satu hari) -> interpolasi
    prev = df["USDIDR"].shift(1)
    nxt = df["USDIDR"].shift(-1)
    mask_error = (df["USDIDR"] < 0.6 * prev) & (df["USDIDR"] < 0.6 * nxt)
    df.loc[mask_error, "USDIDR"] = np.nan
    df["USDIDR"] = df["USDIDR"].interpolate(method="linear")

    df["Date"] = pd.to_datetime(df["Date"])
    d = df.set_index("Date").sort_index()
    d[kolom_numerik] = d[kolom_numerik].ffill().bfill()

    d["ret"] = np.log(d["USDIDR"]).diff()
    d["USDIDR_prev"] = d["USDIDR"].shift(1)
    for l in [1, 2, 3, 5, 10]:
        d[f"ret_lag{l}"] = d["ret"].shift(l)
    d["ret_roll7_mean"] = d["ret"].shift(1).rolling(7).mean()
    d["ret_roll7_std"] = d["ret"].shift(1).rolling(7).std()
    d["ret_roll30_mean"] = d["ret"].shift(1).rolling(30).mean()
    d["ret_roll30_std"] = d["ret"].shift(1).rolling(30).std()
    for col in MAKRO_PCT:
        d[f"{col}_chg_lag1"] = d[col].pct_change().shift(1)
    d["rate_diff"] = d["BI_rate"] - d["US_rate"]
    d["rate_diff_lag1"] = d["rate_diff"].shift(1)
    d["rate_diff_chg_lag1"] = d["rate_diff"].diff().shift(1)
    d["day_of_week"] = d.index.dayofweek
    d["month"] = d.index.month
    return d


def load_dataset():
    """Muat dataset mentah (untuk halaman EDA)."""
    path = os.path.join(DATA_DIR, "dataset.csv")
    return pd.read_csv(path, parse_dates=["Date"])


def get_model_data():
    """Kembalikan dataframe siap-model (sudah dibersihkan & ber-fitur)."""
    df = load_dataset()
    d = _build_features(df)
    return d.dropna(subset=FEATURE_COLS + ["ret", "USDIDR", "USDIDR_prev"]).copy()


# ------------------------------------------------------------------ inferensi
def _predict_ret(feature_dict):
    Xf = pd.DataFrame([feature_dict])[FEATURE_COLS]
    return float(_model.predict(_scaler.transform(Xf))[0])


def _next_day_features(d_model, macro_changes=None, rate_diff=None):
    """
    Bangun vektor fitur untuk HARI KERJA BERIKUTNYA (besok) dari histori.
    Asumsi default: perubahan makro = 0 (sama dengan logika forecast), kecuali
    di-override oleh skenario user. Ini menjaga konsistensi prediksi besok
    antara halaman Beranda, Prediksi, dan Forecast hari ke-1.
    """
    ret_hist = d_model["ret"].tolist()
    rate_diff_last = float(d_model["rate_diff"].iloc[-1])
    next_date = d_model.index[-1] + pd.tseries.offsets.BDay(1)

    feat = {
        "ret_lag1": ret_hist[-1], "ret_lag2": ret_hist[-2], "ret_lag3": ret_hist[-3],
        "ret_lag5": ret_hist[-5], "ret_lag10": ret_hist[-10],
        "ret_roll7_mean": float(np.mean(ret_hist[-7:])),
        "ret_roll7_std": float(np.std(ret_hist[-7:])),
        "ret_roll30_mean": float(np.mean(ret_hist[-30:])),
        "ret_roll30_std": float(np.std(ret_hist[-30:])),
        "OIL_chg_lag1": 0.0, "GOLD_chg_lag1": 0.0, "SP500_chg_lag1": 0.0,
        "IHSG_chg_lag1": 0.0, "VIX_chg_lag1": 0.0, "CPI_chg_lag1": 0.0,
        "rate_diff_lag1": rate_diff_last, "rate_diff_chg_lag1": 0.0,
        "day_of_week": next_date.dayofweek, "month": next_date.month,
    }
    if macro_changes:
        for col in MAKRO_PCT:
            if macro_changes.get(col) is not None:
                feat[f"{col}_chg_lag1"] = float(macro_changes[col]) / 100.0  # persen -> desimal
    if rate_diff is not None:
        feat["rate_diff_lag1"] = float(rate_diff)
    return feat, next_date


def _build_result(d_model, feat, next_date):
    r_hat = _predict_ret(feat)
    harga_terakhir = float(d_model["USDIDR"].iloc[-1])
    level = harga_terakhir * np.exp(r_hat)
    return {
        "tanggal_basis": str(d_model.index[-1].date()),
        "tanggal_prediksi": str(next_date.date()),
        "harga_terakhir": round(harga_terakhir, 2),
        "return": r_hat,
        "return_persen": round(r_hat * 100, 4),
        "arah": "NAIK" if r_hat > 0 else "TURUN",
        "prediksi_level": round(level, 2),
        "selisih": round(level - harga_terakhir, 2),
    }


def predict_next_day(d_model=None):
    """Prediksi return & level USD/IDR untuk hari kerja berikutnya (data terbaru)."""
    if d_model is None:
        d_model = get_model_data()
    feat, next_date = _next_day_features(d_model)
    return _build_result(d_model, feat, next_date)


def predict_scenario(macro_changes, rate_diff=None, d_model=None):
    """
    Prediksi besok dengan SKENARIO asumsi perubahan makro dari user.
    macro_changes: dict {OIL: %, GOLD: %, ...} dalam PERSEN (mis. 2.5 = +2.5%).
    """
    if d_model is None:
        d_model = get_model_data()
    feat, next_date = _next_day_features(d_model, macro_changes=macro_changes, rate_diff=rate_diff)
    return _build_result(d_model, feat, next_date)


def last_macro_values(d_model=None):
    """Nilai ABSOLUT terbaru tiap indikator makro (acuan default & konversi %)."""
    if d_model is None:
        d_model = get_model_data()
    return {col: float(d_model[col].iloc[-1]) for col in MAKRO_PCT}


def predict_scenario_abs(macro_abs, d_model=None):
    """
    Prediksi besok dari input NILAI ABSOLUT indikator makro hari ini.
    Tiap nilai dikonversi ke % perubahan terhadap nilai terakhir, lalu diteruskan
    ke model (yang memang dilatih pada perubahan, bukan level mentah).

    macro_abs: dict {OIL: 74.1, GOLD: 4210, ...} dalam satuan asli indikator.
    Raise ValueError bila perubahan harian implisit terlalu ekstrem (tak wajar).
    """
    if d_model is None:
        d_model = get_model_data()
    last = last_macro_values(d_model)
    macro_changes = {}
    for col in MAKRO_PCT:
        if macro_abs.get(col) is None:
            continue
        prev = last[col]
        chg = 0.0 if prev == 0 else (float(macro_abs[col]) - prev) / prev * 100.0
        if abs(chg) > MAX_PERUBAHAN_HARIAN_PCT:
            raise ValueError(
                f"{col} {macro_abs[col]:g} berarti perubahan {chg:+.1f}% dalam satu hari "
                f"terhadap nilai terakhir ({prev:g}) — terlalu ekstrem. "
                f"Gunakan nilai yang lebih wajar."
            )
        macro_changes[col] = chg
    feat, next_date = _next_day_features(d_model, macro_changes=macro_changes)
    return _build_result(d_model, feat, next_date)


def forecast(horizon=30, d_model=None):
    """Forecast iteratif `horizon` hari kerja ke depan + confidence band."""
    if d_model is None:
        d_model = get_model_data()
    tanggal_terakhir = d_model.index[-1]
    tanggal_depan = pd.bdate_range(
        start=tanggal_terakhir + pd.tseries.offsets.BDay(1), periods=horizon
    )
    ret_hist = d_model["ret"].tolist()
    harga = float(d_model["USDIDR"].iloc[-1])
    rate_diff_last = float(d_model["rate_diff"].iloc[-1])
    sigma = float(META.get("sigma_ret", np.std(ret_hist[-60:])))

    out = []
    for h, tgl in enumerate(tanggal_depan, start=1):
        feat = {
            "ret_lag1": ret_hist[-1], "ret_lag2": ret_hist[-2], "ret_lag3": ret_hist[-3],
            "ret_lag5": ret_hist[-5], "ret_lag10": ret_hist[-10],
            "ret_roll7_mean": float(np.mean(ret_hist[-7:])),
            "ret_roll7_std": float(np.std(ret_hist[-7:])),
            "ret_roll30_mean": float(np.mean(ret_hist[-30:])),
            "ret_roll30_std": float(np.std(ret_hist[-30:])),
            "OIL_chg_lag1": 0.0, "GOLD_chg_lag1": 0.0, "SP500_chg_lag1": 0.0,
            "IHSG_chg_lag1": 0.0, "VIX_chg_lag1": 0.0, "CPI_chg_lag1": 0.0,
            "rate_diff_lag1": rate_diff_last, "rate_diff_chg_lag1": 0.0,
            "day_of_week": tgl.dayofweek, "month": tgl.month,
        }
        r_hat = _predict_ret(feat)
        harga = harga * np.exp(r_hat)
        lebar = sigma * np.sqrt(h)
        out.append({
            "tanggal": str(tgl.date()),
            "prediksi": round(harga, 2),
            "bawah": round(harga * np.exp(-lebar), 2),
            "atas": round(harga * np.exp(+lebar), 2),
        })
        ret_hist.append(r_hat)
    return out


def get_eval_table():
    """Tabel evaluasi model (dari notebook) sebagai list-of-dict."""
    path = os.path.join(DATA_DIR, "evaluasi_model.csv")
    df = pd.read_csv(path, index_col=0)
    df = df.reset_index().rename(columns={"index": "Model"})
    return df.to_dict(orient="records")


def dataset_summary():
    """Ringkasan dataset untuk halaman EDA."""
    df = load_dataset()
    return {
        "n_baris": len(df),
        "n_fitur": df.shape[1] - 1,
        "tanggal_awal": str(df["Date"].min().date()),
        "tanggal_akhir": str(df["Date"].max().date()),
        "kolom": list(df.columns),
        "missing": int(df.isnull().sum().sum()),
        "describe": df.describe().T.round(2).reset_index().rename(
            columns={"index": "Variabel"}).to_dict(orient="records"),
        "head": df.head(8).round(2).astype(object).where(df.head(8).notna(), "—").to_dict(orient="records"),
    }
