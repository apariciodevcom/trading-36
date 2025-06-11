#!/bin/bash

# Ruta: /home/ubuntu/tr/runcon.sh

FECHA=$(date +"%Y-%m-%d")
LOG_BASE="/home/ubuntu/tr/logs/ing"
TRACE_LOG="/home/ubuntu/tr/logs/runcon_trace.log"
ERROR_LOG="/home/ubuntu/tr/logs/runcon_error.log"

echo "$(date) runcon.sh INICIADO" >> $TRACE_LOG

# Verificar argumentos
SCRIPT="$1"
LOGFILE="$2"

if [ -z "$SCRIPT" ] || [ -z "$LOGFILE" ]; then
  echo "$(date) ERROR: Faltan argumentos. Uso: runcon.sh script.py log.out" >> $TRACE_LOG
  exit 1
fi

# Cargar entorno
source /home/ubuntu/tr/.keys.sh

echo "$(date) Ejecutando: $SCRIPT" >> $TRACE_LOG

/usr/bin/python3 "$SCRIPT" >> "$LOGFILE" 2>> "$ERROR_LOG"

EXIT_CODE=$?
echo "$(date) Finalizo $SCRIPT con status $EXIT_CODE" >> $TRACE_LOG

