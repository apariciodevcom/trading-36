import os
import boto3
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil

BUCKET_NAME = "leantech-trading"
S3_PREFIX = "data/historic/"
OUTPUT_DIR = Path("/home/ubuntu/tr/data/historic/")
LOG_PATH = Path("/home/ubuntu/tr/logs/core/s3_to_parquet_log.csv")
CONFIG_PATH = Path("/home/ubuntu/tr/config/symbol_groups.json")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

s3 = boto3.client("s3")

def log_event(modulo, status, mensaje, inicio):
    fin = datetime.now()
    dur = round((fin - inicio).total_seconds(), 2)
    ts = fin.strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts},{modulo},{status},{mensaje},{dur}s\n"
    with open(LOG_PATH, "a") as f:
        f.write(linea)
    print(f"[{ts}] [{modulo}] {status}: {mensaje} ({dur}s)")

def descargar_y_convertir(symbol):
    s3_key = f"{S3_PREFIX}{symbol}.csv"
    local_parquet = OUTPUT_DIR / f"{symbol}.parquet"
    try:
        inicio = datetime.now()
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=s3_key)
        df = pd.read_csv(obj["Body"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime").reset_index(drop=True)
        df.to_parquet(local_parquet, index=False)
        log_event("s3_to_parquet", "OK", f"{symbol} procesado", inicio)
    except Exception as e:
        log_event("s3_to_parquet", "ERROR", f"{symbol} fallo: {str(e)}", inicio)
        
def main():
    import json
    total_inicio = datetime.now()
    procesados = 0

    # Limpiar carpeta OUTPUT_DIR
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(CONFIG_PATH, "r") as f:
        grupos = json.load(f)
    simbolos = sorted(set(sum(grupos.values(), [])))

    for simbolo in simbolos:
        before = datetime.now()
        descargar_y_convertir(simbolo)
        procesados += 1

    total_duracion = round((datetime.now() - total_inicio).total_seconds(), 2)
    resumen = f"{procesados} archivos procesados en {total_duracion}s"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_PATH, "a") as f:
        f.write(f"{ts},s3_to_parquet,RESUMEN,{resumen},{total_duracion}s\n")
    print(f"[{ts}] [s3_to_parquet] RESUMEN: {resumen}")

if __name__ == "__main__":
    main()

