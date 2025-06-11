import pandas as pd
import os
from datetime import datetime

# === RUTAS ===
FEATURES_PATH = "/home/ubuntu/tr/data/features/SMCI_features.parquet"
BACKTEST_PATH = "/home/ubuntu/tr/reports/backtest_heuristicas/resumen/bt_operaciones_2025-05-29.csv"
OUTPUT_PATH = "/home/ubuntu/tr/data/features/SMCI_features_etiquetado.parquet"
LOG_PATH = "/home/ubuntu/tr/logs/ml/label_smci.log"

# === LOGGING ===
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

    try:
        df_feat = pd.read_parquet(FEATURES_PATH)
        df_bt = pd.read_csv(BACKTEST_PATH)

        df_bt = df_bt[df_bt["senal"].isin(["buy", "sell"])]
        df_bt = df_bt[df_bt["estrategia"].notna()]
        df_bt["fecha_entrada"] = pd.to_datetime(df_bt["fecha_entrada"]).dt.date
        df_feat["fecha"] = pd.to_datetime(df_feat["fecha"]).dt.date

        df_bt = df_bt[df_bt["resultado"].isin([0, 1])]
        df_bt_smci = df_bt[df_bt["estrategia"].str.contains("smci", case=False, na=False)]

        if df_bt_smci.empty:
            log("ERROR: no se encontraron operaciones para SMCI.")
            return

        df_merged = df_feat.merge(df_bt_smci[["fecha_entrada", "resultado"]], left_on="fecha", right_on="fecha_entrada", how="inner")
        df_merged = df_merged.rename(columns={"resultado": "senal"}).drop(columns=["fecha_entrada"])

        df_merged.to_parquet(OUTPUT_PATH, index=False)
        log(f"OK: archivo etiquetado generado con {len(df_merged)} filas.")

    except Exception as e:
        log(f"ERROR: {e}")

if __name__ == "__main__":
    main()
