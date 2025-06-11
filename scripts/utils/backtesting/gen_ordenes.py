import os
import pandas as pd
from datetime import datetime, timedelta

# === CONFIGURACION ===
SENAL_DIR = "/home/ubuntu/tr/reports/senales_heuristicas/historicas"
HIST_DIR = "/home/ubuntu/tr/data/historic"
ORDENES_DIR = "/home/ubuntu/tr/reports/backtest_heuristicas/ordenes/"
LOG = f"/home/ubuntu/tr/logs/utils/gen_ordenes_{datetime.now().date()}.log"

TP = 0.03
SL = -0.01
MAX_DIAS = 5

# === FUNCIONES ===
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG, "a") as f:
        f.write(linea + "\n")

def simular_ordenes(simbolo):
    try:
        df_signals = pd.read_csv(f"{SENAL_DIR}/{simbolo}_senales.csv")
        df_prices = pd.read_parquet(f"{HIST_DIR}/{simbolo}.parquet")
        df_prices["fecha"] = pd.to_datetime(df_prices["datetime"])
        df_signals["fecha"] = pd.to_datetime(df_signals["fecha"])

        ordenes = []

        for _, row in df_signals.iterrows():
            if row["signal"] not in ["buy", "sell"]:
                continue

            fecha_entrada = row["fecha"]
            estrategia = row["estrategia"]
            senal = row["signal"]

            try:
                idx_entrada = df_prices.index[df_prices["fecha"] == fecha_entrada][0]
                precio_entrada = df_prices.loc[idx_entrada, "close"]
                sub_df = df_prices.iloc[idx_entrada + 1 : idx_entrada + 1 + MAX_DIAS]

                for i, r in sub_df.iterrows():
                    precio_actual = r["close"]
                    dias = (r["fecha"] - fecha_entrada).days

                    cambio = (precio_actual - precio_entrada) / precio_entrada
                    if senal == "sell":
                        cambio = -cambio

                    if cambio >= TP or cambio <= SL or r["fecha"] == sub_df["fecha"].iloc[-1]:
                        ordenes.append({
                            "fecha_entrada": fecha_entrada.date(),
                            "fecha_salida": r["fecha"].date(),
                            "senal": senal,
                            "estrategia": estrategia,
                            "resultado": round(cambio, 4),
                            "dias": dias
                        })
                        break

            except Exception as e:
                log(f"{simbolo} ERROR al procesar fila: {e}")
                continue

        if ordenes:
            df_out = pd.DataFrame(ordenes)
            os.makedirs(ORDENES_DIR, exist_ok=True)
            df_out.to_csv(f"{ORDENES_DIR}/{simbolo}_ordenes.csv", index=False)
            log(f"OK {simbolo}: {len(ordenes)} ordenes generadas")
        else:
            log(f"OK {simbolo}: sin ordenes")

    except Exception as e:
        log(f"{simbolo} ERROR general: {e}")

# === EJECUCION ===
def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    archivos = [f for f in os.listdir(SENAL_DIR) if f.endswith("_senales.csv")]

    for archivo in sorted(archivos):
        simbolo = archivo.replace("_senales.csv", "")
        simular_ordenes(simbolo)

if __name__ == "__main__":
    main()
