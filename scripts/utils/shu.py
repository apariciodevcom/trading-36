"""
===========================================================================
 Script de Generacion de Señales Heuristicas sobre Historicos - LeanTech
===========================================================================

Ubicacion: /home/ubuntu/tr/scripts/core/shu.py

Descripcion:
------------
Este script recorre todos los historicos de simbolos definidos en 
symbol_groups.json, aplica estrategias heuristicas definidas como modulos
Python externos, y genera archivos .csv con señales para cada simbolo 
procesado.

Acciones principales:
- Carga modulos de estrategias desde my_modules/estrategias/
- Lee historico en .parquet desde data/historic/
- Ejecuta las estrategias sobre el DataFrame de cada simbolo
- Guarda señales generadas en reports/senales_heuristicas/historicas/
- Registra logs por simbolo y resumen final
- Actualiza system_status.json con el resultado

Entradas esperadas:
-------------------
- /data/historic/{SIMBOLO}.parquet  con columna 'fecha' tipo datetime o date
- Columnas numericas requeridas dependen de las estrategias

Salida:
-------
- /reports/senales_heuristicas/historicas/{SIMBOLO}_senales.csv
  con columnas ['fecha', ..., 'simbolo']

Autor:        LeanTech
Ultima ed.:   2025-06-01

===========================================================================
"""

import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from importlib import import_module
import traceback

import sys
sys.path.append("/home/ubuntu/tr")

# === CONFIGURACION ===
CONFIG_PATH = Path("/home/ubuntu/tr/config/symbol_groups.json")
HISTORIC_PATH = Path("/home/ubuntu/tr/data/historic")
OUTPUT_PATH = Path("/home/ubuntu/tr/reports/senales_heuristicas/historicas")
LOG_PATH = Path(f"/home/ubuntu/tr/logs/utils/shu_{datetime.now().date()}.csv")
STATUS_PATH = Path("/home/ubuntu/tr/config/system_status.json")
ESTRATEGIAS_DIR = "my_modules.estrategias"

# === CARGAR SIMBOLOS ===
with open(CONFIG_PATH, "r") as f:
    grupos = json.load(f)

SIMBOLOS = sorted(set(sum(grupos.values(), [])))

# === CARGAR FUNCIONES DE ESTRATEGIAS ===
estrategias = {}
for archivo in os.listdir("/home/ubuntu/tr/my_modules/estrategias"):
    if archivo.endswith(".py"):
        mod = import_module(f"{ESTRATEGIAS_DIR}.{archivo[:-3]}")
        estrategias[archivo[:-3]] = mod.generar_senales

# === FUNCION DE LOG ===
def log_event(modulo, status, mensaje, inicio):
    fin = datetime.now()
    dur = round((fin - inicio).total_seconds(), 2)
    ts = fin.strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts},{modulo},{status},{mensaje},{dur}s\n"
    with open(LOG_PATH, "a") as f:
        f.write(linea)
    print(f"[{modulo}] {status}: {mensaje} ({dur}s)")

# === LIMPIAR OUTPUT ANTERIOR ===
OUTPUT_PATH.mkdir(parents=True, exist_ok=True)
for f in OUTPUT_PATH.glob("*.csv"):
    f.unlink()

# === PROCESAR CADA SIMBOLO DE FORMA SECUENCIAL ===
errores = []
inicio_total = datetime.now()

for simbolo in SIMBOLOS:
    inicio = datetime.now()
    try:
        archivo = HISTORIC_PATH / f"{simbolo}.parquet"
        if not archivo.exists():
            raise FileNotFoundError(f"{archivo} no encontrado")

        df = pd.read_parquet(archivo).reset_index(drop=True)

        resultados = []
        for nombre_est, funcion in estrategias.items():
            df_out = funcion(df.copy())
            if df_out is not None and not df_out.empty:
                df_out["simbolo"] = simbolo
                resultados.append(df_out)

        if resultados:
            df_result = pd.concat(resultados)
            df_result["fecha"] = pd.to_datetime(df_result["fecha"]).dt.strftime("%Y-%m-%d")
            df_result.to_csv(OUTPUT_PATH / f"{simbolo}_senales.csv", index=False)
            log_event("shu", "OK", f"{simbolo} procesado", inicio)
        else:
            log_event("shu", "SKIP", f"{simbolo} sin senales", inicio)

    except Exception as e:
        errores.append(simbolo)
        log_event("shu", "ERROR", f"{simbolo} fallo: {str(e)}", inicio)
        traceback.print_exc()

log_event("shu", "RESUMEN", f"{len(SIMBOLOS)-len(errores)} de {len(SIMBOLOS)} procesados", inicio_total)

# === ACTUALIZAR ESTADO ===
estado = {
    "fecha": datetime.now().strftime("%Y-%m-%d"),
    "status": "OK" if not errores else "ERROR",
    "mensaje": f"{len(SIMBOLOS)-len(errores)} de {len(SIMBOLOS)} procesados correctamente"
}
with open(STATUS_PATH, "r") as f:
    status_json = json.load(f)
status_json["senales_heuristicas"] = estado
with open(STATUS_PATH, "w") as f:
    json.dump(status_json, f, indent=2)
