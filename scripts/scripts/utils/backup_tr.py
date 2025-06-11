import os
import tarfile
import boto3
import logging
import json
import watchtower
from datetime import datetime

# Configuracion de logging local + CloudWatch
log_dir = "/home/ec2-user/tr/logs/utils"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "backup_tr.log")

logger = logging.getLogger("backup_tr")
logger.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s,backup,%(levelname)s,%(message)s")

fh = logging.FileHandler(log_file)
fh.setFormatter(formatter)
logger.addHandler(fh)

cw_handler = watchtower.CloudWatchLogHandler(
    log_group="trading-backups",
    stream_name="backup_tr.py"
)
cw_handler.setFormatter(formatter)
logger.addHandler(cw_handler)

# === Rutas y estado ===
BASE_DIR = "/home/ec2-user/tr"
BACKUP_BASE = "/home/ec2-user/backups"
SUMMARY_FILE = os.path.join(BASE_DIR, "reports/summary/system_status.json")
fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")

def guardar_estado(modulo, status, mensaje):
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    estado = {}
    if os.path.exists(SUMMARY_FILE):
        with open(SUMMARY_FILE, "r") as f:
            estado = json.load(f)
    estado[modulo] = {
        "fecha": fecha_hoy,
        "ultima_ejecucion": now_str,
        "status": status,
        "mensaje": mensaje
    }
    with open(SUMMARY_FILE, "w") as f:
        json.dump(estado, f, indent=2)

# === Proceso de backup ===
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_dir_name = f"backup_tr_{timestamp}"
backup_tar_path = os.path.join(BACKUP_BASE, f"{backup_dir_name}.tar.gz")

try:
    os.makedirs(BACKUP_BASE, exist_ok=True)
    with tarfile.open(backup_tar_path, "w:gz") as tar:
        tar.add(BASE_DIR, arcname=os.path.basename(BASE_DIR))
    logger.info(f"Backup local creado en {backup_tar_path}")
except Exception as e:
    logger.error(f"Fallo al crear backup local: {e}")
    guardar_estado("backup", "ERROR", f"Fallo local: {str(e)}")
    raise

try:
    s3 = boto3.client("s3")
    bucket = "leantech-trading"
    s3_key = f"backup_ec2/{os.path.basename(backup_tar_path)}"
    s3.upload_file(backup_tar_path, bucket, s3_key)
    logger.info(f"Backup subido a S3 en {s3_key}")
    guardar_estado("backup", "OK", f"Backup creado y subido: {s3_key}")
except Exception as e:
    logger.error(f"Fallo al subir backup a S3: {e}")
    guardar_estado("backup", "ERROR", f"Fallo S3: {str(e)}")
    raise
