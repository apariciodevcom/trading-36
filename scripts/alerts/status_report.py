import os
import json
import logging
import boto3
import watchtower
from datetime import datetime

# === RUTAS Y CONFIGURACION ===
BASE_DIR = "/home/ec2-user/tr"
STATUS_FILE = os.path.join(BASE_DIR, "reports/summary/system_status.json")
LOG_DIR = os.path.join(BASE_DIR, "logs/alerts")
LOG_FILE = os.path.join(LOG_DIR, "system_status.log")
LOG_GROUP = "EC2SystemStatusLogs"

EMAIL_TRADING = os.getenv("EMAIL_TRADING")
ses = boto3.client("ses", region_name="eu-central-1")

# === LOGGING ===
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("status_report")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s,%(name)s,%(levelname)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S")

fh = logging.FileHandler(LOG_FILE)
fh.setFormatter(formatter)
logger.addHandler(fh)

try:
    cw_handler = watchtower.CloudWatchLogHandler(log_group=LOG_GROUP)
    cw_handler.setFormatter(formatter)
    logger.addHandler(cw_handler)
except Exception as e:
    logger.warning(f"CloudWatch deshabilitado: {e}")

# === FUNCIONES ===
def cargar_status():
    if not os.path.exists(STATUS_FILE):
        raise FileNotFoundError("system_status.json no encontrado")
    with open(STATUS_FILE, "r") as f:
        return json.load(f)

def construir_tabla_html(data):
    filas = []
    for modulo, info in sorted(data.items()):
        fecha = info.get("fecha", "-")
        hora = info.get("ultima_ejecucion", "-")
        estado = info.get("status", "-")
        mensaje = info.get("mensaje", "")
        color = "#c6efce" if estado == "OK" else "#ffc7ce" if estado == "ERROR" else "#ffeb9c"
        fila = f"""
        <tr style="background-color:{color}">
            <td>{modulo}</td>
            <td>{fecha}</td>
            <td>{hora}</td>
            <td>{estado}</td>
            <td>{mensaje}</td>
        </tr>
        """
        filas.append(fila)
    return """
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse">
        <thead>
            <tr>
                <th>Modulo</th><th>Fecha</th><th>Hora</th><th>Estado</th><th>Mensaje</th>
            </tr>
        </thead>
        <tbody>
            {filas}
        </tbody>
    </table>
    """.format(filas="\n".join(filas))

def enviar_correo_html(asunto, cuerpo_html):
    if not EMAIL_TRADING:
        logger.error("EMAIL_TRADING no definido en entorno")
        return

    try:
        ses.send_email(
            Source=EMAIL_TRADING,
            Destination={"ToAddresses": [EMAIL_TRADING]},
            Message={
                "Subject": {"Data": asunto, "Charset": "UTF-8"},
                "Body": {
                    "Html": {"Data": cuerpo_html, "Charset": "UTF-8"}
                }
            }
        )
        logger.info("Correo enviado correctamente")
    except Exception as e:
        logger.error(f"Fallo envio de correo: {str(e)}")

# === MAIN ===
def main():
    try:
        logger.info("Inicio status_report")
        data = cargar_status()
        fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")
        asunto = f"[TRADING] Estado diario del sistema - {fecha_hoy}"
        tabla_html = construir_tabla_html(data)
        enviar_correo_html(asunto, tabla_html)
    except Exception as e:
        logger.error(f"Error en status_report: {str(e)}")

if __name__ == "__main__":
    main()
