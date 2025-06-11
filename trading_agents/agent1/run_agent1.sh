#!/bin/bash
# =============================================================================
# run_agent1.sh - Ejecuta el agente de trading agent1.py
# =============================================================================

LOG_FILE="/home/ubuntu/tr/logs/agent1.log"
DATE_NOW=$(date '+%Y-%m-%d %H:%M:%S')

echo "===== START [$DATE_NOW] =====" >> $LOG_FILE

# Cargar variables de entorno si es necesario
source /home/ubuntu/tr/.keys.sh >> $LOG_FILE 2>&1

# Ejecutar el agente
python3 /home/ubuntu/tr/scripts/utils/agent1.py >> $LOG_FILE 2>&1

if [ $? -eq 0 ]; then
    echo "[$DATE_NOW] agent1.py completed successfully." >> $LOG_FILE
else
    echo "[$DATE_NOW] agent1.py FAILED." >> $LOG_FILE
fi

echo "===== END [$DATE_NOW] =====" >> $LOG_FILE
echo "" >> $LOG_FILE
