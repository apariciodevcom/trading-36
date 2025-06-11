import os
import pandas as pd
from datetime import datetime

# === CONFIGURACION ===
CARPETA = "/home/ubuntu/tr/data/historic_recuperado/"
FECHA_OBJETIVO = "2025-05-29"
LOG = f"/home/ubuntu/tr/logs/utils/verif_recuperado_{datetime.now().date()}.log"

# === FUNCION LOG ===
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG, "a") as f:
        f.write(linea + "\n")

# === FLUJO PRINCIPAL ===
def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

    archivos = [f for f in os.listdir(CARPETA) if f.endswith(".parquet")]
    total = 0
    errores = []

    for archivo in sorted(archivos):
        simbolo = archivo.replace(".parquet", "").upper()
        try:
            df = pd.read_parquet(os.path.join(CARPETA, archivo))
            fecha_max = df["datetime"].max().strftime("%Y-%m-%d")
            if fecha_max != FECHA_OBJETIVO:
                errores.append(f"{simbolo} tiene fecha {fecha_max}")
            else:
                log(f"OK {simbolo}")
            total += 1
        except Exception as e:
            errores.append(f"{simbolo} ERROR al leer: {e}")

    log(f"Validados {total} archivos.")
    if errores:
        log("Errores encontrados:")
        for err in errores:
            log(f"- {err}")
    else:
        log("Todos los archivos tienen la fecha correcta.")

if __name__ == "__main__":
    main()
