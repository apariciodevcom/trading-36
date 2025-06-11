import os
import pandas as pd
from datetime import datetime

# === CONFIGURACION ===
ORDENES_DIR = "/home/ubuntu/tr/reports/backtest_heuristicas/ordenes"
SALIDA_CSV = f"/home/ubuntu/tr/reports/backtest_heuristicas/resumen/bt_operaciones_{datetime.now().date()}.csv"
LOG = f"/home/ubuntu/tr/logs/backtest/bt_{datetime.now().date()}.log"

# === FUNCION DE LOG ===
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG, "a") as f:
        f.write(linea + "\n")

# === FUNCION PRINCIPAL ===
def main():
    os.makedirs(os.path.dirname(SALIDA_CSV), exist_ok=True)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

    archivos = [f for f in os.listdir(ORDENES_DIR) if f.endswith("_ordenes.csv")]
    operaciones = []

    for archivo in sorted(archivos):
        simbolo = archivo.replace("_ordenes.csv", "").upper()
        try:
            df = pd.read_csv(os.path.join(ORDENES_DIR, archivo))
            if df.empty:
                log(f"{simbolo} sin operaciones")
                continue

            operaciones.append(df)
            log(f"{simbolo} OK: {len(df)} ordenes registradas")

        except Exception as e:
            log(f"{simbolo} ERROR: {e}")

    if operaciones:
        df_final = pd.concat(operaciones, ignore_index=True)
        df_final.to_csv(SALIDA_CSV, index=False)
        log(f"Resumen total guardado: {SALIDA_CSV} ({len(df_final)} filas)")
    else:
        log("No se generaron ordenes.")

if __name__ == "__main__":
    main()
