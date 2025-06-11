
import os
import pandas as pd
import boto3
import logging
import watchtower
from datetime import datetime

BASE_DIR = "/home/ec2-user/tr"
FEATURES_DIR = f"{BASE_DIR}/data/features"
LOG_DIR = f"{BASE_DIR}/logs"
LOG_FILE = f"{LOG_DIR}/precio_alto.log"
CLOUDWATCH_GROUP = "EC2AlertasLogs"
EMAIL = os.getenv("EMAIL_TRADING")

os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("AlertaPrecioAlto")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s,precio_alto,INFO,%(message)s")

fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(formatter)
logger.addHandler(fh)

cw = watchtower.CloudWatchLogHandler(log_group=CLOUDWATCH_GROUP)
cw.setFormatter(formatter)
logger.addHandler(cw)

def revisar_precios_altos():
    print("=== INICIANDO ALERTA PRECIO ALTO ===")
    alertas = []
    for file in os.listdir(FEATURES_DIR):
        if not file.endswith("_features.parquet"):
            continue
        symbol = file.replace("_features.parquet", "")
        path = os.path.join(FEATURES_DIR, file)
        try:
            df = pd.read_parquet(path)
            logger.info(f"{symbol} - Cargado OK - {len(df)} filas")
            if "datetime" not in df.columns:
                logger.error(f"{symbol} - No tiene columna 'datetime'")
                continue
            df = df.sort_values("datetime").dropna(subset=["close", "high", "low"])
            if len(df) < 80:
                logger.info(f"{symbol} - menos de 80 filas tras dropna")
                continue
            if not all(col in df.columns for col in ["high", "low", "close"]):
                logger.error(f"{symbol} - Faltan columnas para analisis")
                continue

            df_ultimos = df.tail(80)
            maximo = df_ultimos["high"].max()
            minimo = df_ultimos["low"].min()
            umbral = maximo - 0.18 * (maximo - minimo)
            actual = df_ultimos["close"].iloc[-1]

            logger.info(f"{symbol} evaluado - close={actual:.2f} - umbral={umbral:.2f} - rango=({minimo:.2f}, {maximo:.2f})")

            if actual >= umbral:
                msg = f"{symbol} alto en rango - close={actual:.2f} - umbral={umbral:.2f}"
                alertas.append(msg)
                logger.info(f"ALERTA_PRECIO_ALTO - {msg}")
        except Exception as e:
            logger.error(f"{symbol} error: {str(e)}")

    if alertas:
        enviar_correo(alertas)
    else:
        logger.info("No se detectaron alertas de precios altos.")

def enviar_correo(alertas):
    ses = boto3.client("ses", region_name="eu-central-1")
    asunto = "Alerta de precios altos en acciones"
    cuerpo = "\n".join(alertas)
    ses.send_email(
        Source=EMAIL,
        Destination={"ToAddresses": [EMAIL]},
        Message={
            "Subject": {"Data": asunto},
            "Body": {"Text": {"Data": cuerpo}}
        }
    )
    logger.info(f"Correo enviado con {len(alertas)} alertas")

if __name__ == "__main__":
    revisar_precios_altos()
