import pandas as pd
import numpy as np
import os
from datetime import datetime

# === CONFIG ===
INPUT_PATH = "/home/ubuntu/tr/data/historic/SMCI.parquet"
OUTPUT_PATH = "/home/ubuntu/tr/data/features/SMCI_features.parquet"
LOG_PATH = "/home/ubuntu/tr/logs/features/fea_smci.log"

# === FUNCIONES DE FEATURES ===
def calcular_rsi(series, window=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -delta.clip(upper=0)
    ma_up = up.rolling(window).mean()
    ma_down = down.rolling(window).mean()
    rs = ma_up / ma_down
    return 100 - (100 / (1 + rs))

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG_PATH, "a") as f:
        f.write(linea + "\n")

# === MAIN ===
def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

    if not os.path.exists(INPUT_PATH):
        log(f"ERROR: archivo no encontrado: {INPUT_PATH}")
        return

    try:
        df = pd.read_parquet(INPUT_PATH)
        df = df[df["datetime"].notna()]
        df["fecha"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("fecha")

        if len(df) < 60:
            log(f"SKIP SMCI: menos de 60 filas")
            return

        df["ma_5"] = df["close"].rolling(5).mean()
        df["ma_20"] = df["close"].rolling(20).mean()
        df["rsi_14"] = calcular_rsi(df["close"], 14)
        df["pos_rango_60"] = (df["close"] - df["low"].rolling(60).min()) / (df["high"].rolling(60).max() - df["low"].rolling(60).min())
        df["volatilidad_20"] = df["close"].rolling(20).std()
        df["cambio_1d"] = df["close"].pct_change(1)
        df["cambio_3d"] = df["close"].pct_change(3)
        df["simbolo"] = "SMCI"

        columnas_finales = ["simbolo", "fecha", "ma_5", "ma_20", "rsi_14", "pos_rango_60", "volatilidad_20", "cambio_1d", "cambio_3d", "volume"]
        df_final = df[columnas_finales].dropna()

        df_final.to_parquet(OUTPUT_PATH, index=False)
        log(f"OK: archivo generado con {len(df_final)} filas y {len(columnas_finales)-2} features.")

    except Exception as e:
        log(f"ERROR procesando SMCI: {e}")

if __name__ == "__main__":
    main()
