# config.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuración de email
MAX_EMAILS_PER_DAY = 50
SES_PROFILE_NAME = "ses-trading"

# Configuración regional y formato de fecha
TIMEZONE = "Europe/Zurich"
DATE_FORMAT = "%Y-%m-%d"

LOCAL_LOG_PATH = "/home/ubuntu/tr/logs/email/email_counter.json"

