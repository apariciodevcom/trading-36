#!/usr/bin/env python3
import os
import sys
import shutil
import json
import pandas as pd
import logging
import watchtower
from datetime import datetime
from collections import defaultdict
import sys

# === PATH DEL PROYECTO ===
sys.path.append("/home/ubuntu/tr")
BASE_DIR = "//home/ubuntu/tr"
sys.path.append(BASE_DIR)

from my_modules.email_sender import enviar_email

# === RUTAS ===
SENALES_DIR = f"{BASE_DIR}/reports/senales_heuristicas/diarias"
HISTORIC_DIR = f"{BASE_DIR}/data/historic"
LOG_DIR = f"{BASE_DIR}/logs/alerts"
SUMMARY_PATH = f"{BASE_DIR}/reports/summary/system_status.json"
DESTINATARIO = os.getenv("EMAIL_TRADING")
LOG_GROUP = "EC2AlertasSenales"
fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")

# === LOGGING ===
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"alertas_{fecha_hoy}.csv")
log_persistente = os.path.join(LOG_DIR, "alertas.log")

logger = logging.getLogger("AlertasSenales")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s,alertas,%(levelname)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S")

for handler_path in [log_file, log_persistente]:
    fh = logging.FileHandler(handler_path)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

cw_handler = watchtower.CloudWatchLogHandler(log_group=LOG_GROUP)
cw_handler.setFormatter(formatter)
logger.addHandler(cw_handler)

# === FUNCION DE ESTADO ===
def guardar_estado(modulo, status, mensaje):
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    status_obj = {}
    if os.path.exists(SUMMARY_PATH):
        with open(SUMMARY_PATH, "r") as f:
            status_obj = json.load(f)
    status_obj[modulo] = {
        "fecha": fecha_hoy,
        "ultima_ejecucion": now_str,
        "status": status,
        "mensaje": mensaje
    }
    with open(SUMMARY_PATH, "w") as f:
        json.dump(status_obj, f, indent=2)

# === AGRUPAR SENALES ===
senales = defaultdict(list)

for archivo in os.listdir(SENALES_DIR):
    if not archivo.endswith(".csv"):
        continue
    try:
        symbol = archivo.split("_")[0]
        estrategia = "_".join(archivo.split("_")[1:-1])
        ruta = os.path.join(SENALES_DIR, archivo)
        df = pd.read_csv(ruta)

        if "fecha" in df.columns and "signal" in df.columns:
            fecha_max = df["fecha"].max()
            fila = df[df["fecha"] == fecha_max]
            if fila.empty:
                continue
            signal = fila.iloc[-1]["signal"]

            close = None
            ruta_hist = os.path.join(HISTORIC_DIR, f"{symbol}.parquet")
            if os.path.exists(ruta_hist):
                df_hist = pd.read_parquet(ruta_hist)
                df_hist["datetime"] = pd.to_datetime(df_hist["datetime"])
                df_hist.set_index("datetime", inplace=True)
                fila_hist = df_hist[df_hist.index.date == pd.to_datetime(fecha_max).date()]
                if not fila_hist.empty:
                    close = round(fila_hist["close"].iloc[-1], 2)

            senales[(symbol, signal)].append((estrategia, fecha_max, close))
    except Exception as e:
        logger.error(f"Error procesando {archivo}: {str(e)}")

# === FILTRAR SENALES CON MULTIPLES ESTRATEGIAS ===
def preparar_tabla(signal_type):
    filas = []
    for (symbol, signal), estrategias in senales.items():
        if signal != signal_type or len(estrategias) < 2:
            continue
        estrategias_str = ", ".join([e[0] for e in estrategias])
        fecha = estrategias[0][1]
        cierre = estrategias[0][2] if estrategias[0][2] is not None else "N/D"
        filas.append({
            "Simbolo": symbol,
            "Estrategias": estrategias_str,
            "Fecha": fecha,
            "Cierre": cierre
        })
    if not filas:
        return f"<h3>No hay señales de {signal_type.upper()} con coincidencia de estrategias ({fecha_hoy})</h3>", 0
    df = pd.DataFrame(filas)
    tabla = df.to_html(index=False, border=1, justify="center", classes="tabla")
    return f"""<h3>{len(filas)} simbolos con 2 o mas estrategias de {signal_type.upper()} ({fecha_hoy}):</h3>{tabla}""", len(filas)

html_buy, n_buy = preparar_tabla("buy")
html_sell, n_sell = preparar_tabla("sell")

html_completo = f"""<html>
<head>
<style>
h3 {{ font-family: Arial; }}
table.tabla {{
  font-family: Arial, sans-serif;
  border-collapse: collapse;
  width: 100%;
}}
table.tabla th, table.tabla td {{
  border: 1px solid #dddddd;
  text-align: center;
  padding: 8px;
}}
table.tabla th {{
  background-color: #f2f2f2;
}}
</style>
</head>
<body>
{html_buy}
<br>
{html_sell}
</body>
</html>
"""

asunto = f"Senales Coincidentes por Estrategia - {fecha_hoy}"

# === ENVIAR EMAIL ===
if DESTINATARIO:
    exito = enviar_email(asunto=asunto, cuerpo=html_completo, destinatario=DESTINATARIO, html=True)
    if exito:
        logger.info("Correo enviado exitosamente.")
        total = n_buy + n_sell
        guardar_estado("alertas", "OK", f"{total} alertas detectadas y enviadas")
    else:
        logger.error("Fallo el envio del correo.")
        guardar_estado("alertas", "ERROR", "Fallo envio de correo")
else:
    logger.error("EMAIL_TRADING no esta definido.")
    guardar_estado("alertas", "ERROR", "EMAIL_TRADING no definido")
    


# HIST_DIR = f"{BASE_DIR}/reports/senales_heuristicas/historicas"
# os.makedirs(HIST_DIR, exist_ok=True)

# for archivo in os.listdir(SENALES_DIR):
    # if archivo.endswith(".csv"):
        # src = os.path.join(SENALES_DIR, archivo)
        # dst = os.path.join(HIST_DIR, archivo)
        # try:
            # shutil.move(src, dst)
            # logger.info(f"{archivo} movido a historicas")
        # except Exception as e:
            # logger.error(f"Fallo al mover {archivo}: {str(e)}")
