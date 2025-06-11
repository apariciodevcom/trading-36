"""
===========================================================================
 Script de Recuperacion Historica desde Twelve Data - LeanTech Trading
===========================================================================

Ubicacion: /home/ubuntu/tr/scripts/utils/recuperar_historico.py

Descripcion:
------------
Este script permite descargar historicos diarios completos desde la API
de Twelve Data, procesarlos y almacenarlos localmente en formato .parquet.
Es especialmente util para reconstruir historicos faltantes o iniciales
fuera del ciclo de ingesta automatizada por Lambda.

Acciones principales:
- Carga todos los simbolos definidos en symbol_groups.json
- Solicita a la API hasta 5000 datos diarios por simbolo
- Convierte y normaliza columnas numericas y de fecha
- Aplica un recorte por fecha si esta activado
- Guarda archivos .parquet por simbolo
- Registra un log local por simbolo y evento

Archivos involucrados:
----------------------
- Config entrada:   /home/ubuntu/tr/config/symbol_groups.json
- Salida datos:     /home/ubuntu/tr/data/historic_recuperado/{SIMBOLO}.parquet
- Log de ejecucion: /home/ubuntu/tr/logs/utils/recuperar_YYYY-MM-DD.log

Formato de datos:
-----------------
- Columnas: ['fecha', 'open', 'high', 'low', 'close', 'volume']
- Tipos:    fecha = datetime.date, resto = float64

Parametros configurables:
-------------------------
- RESPETAR_FECHA_LIMITE: bool
- FECHA_LIMITE: YYYY-MM-DD (incluyente)

Notas:
------
- Sobrescribe todos los archivos .parquet existentes antes de iniciar
- Limita el ritmo de requests a ~5/minuto por simbolo
- No requiere acceso a S3 ni permisos IAM

Autor:        LeanTech
Ultima ed.:   2025-06-01

===========================================================================
"""

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# === CONFIGURACION ===
RESPETAR_FECHA_LIMITE = True
FECHA_LIMITE = "2025-05-28"
BASE_DIR = "/home/ubuntu/tr"
OUTPUT_DIR = f"{BASE_DIR}/data/historic_recuperado"
CONFIG_PATH = f"{BASE_DIR}/config/symbol_groups.json"
LOG_FILE = f"{BASE_DIR}/logs/utils/recuperar_{datetime.now().date()}.log"

# === API KEY ===
load_dotenv(f"{BASE_DIR}/.keys.sh")
API_KEY = os.getenv("TWELVE_API_KEY")

# === CREAR RUTAS ===
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

for f in Path(OUTPUT_DIR).glob("*.parquet"):
    f.unlink()


# === FUNCIONES ===
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG_FILE, "a") as f:
        f.write(linea + "\n")

def fetch_data(symbol):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": "1day",
        "outputsize": 5000,
        "apikey": API_KEY
    }
    response = requests.get(url, params=params)
    data = response.json()
    if "values" not in data:
        raise ValueError(f"sin datos: {data}")
    df = pd.DataFrame(data["values"])
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    return df

def guardar_parquet(df, symbol):
    if RESPETAR_FECHA_LIMITE:
        df = df[df["datetime"] <= FECHA_LIMITE].copy()
    df["fecha"] = df["datetime"].dt.date
    df = df.drop(columns=["datetime"])
    df = df[["fecha", "open", "high", "low", "close", "volume"]]
    out_path = os.path.join(OUTPUT_DIR, f"{symbol}.parquet")
    df.to_parquet(out_path, index=False)

# === FLUJO PRINCIPAL ===
def main():
    try:
        with open(CONFIG_PATH, "r") as f:
            grupos = json.load(f)
    except Exception as e:
        log(f"ERROR al leer symbol_groups.json: {e}")
        return

    total = 0
    for grupo, simbolos in grupos.items():
        for simbolo in simbolos:
            try:
                df = fetch_data(simbolo)
                guardar_parquet(df, simbolo)
                log(f"OK {simbolo}: {len(df)} filas")
                total += 1
            except Exception as e:
                log(f"ERROR {simbolo}: {e}")
            time.sleep(12)

    log(f"Proceso completado. Simbolos procesados: {total}")

if __name__ == "__main__":
    main()
