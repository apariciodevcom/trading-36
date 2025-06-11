#!/bin/bash

# === Load environment variables ===
source /home/ubuntu/tr/.keys.sh

# =============================================================================
# run_publish_pipeline.sh - Daily heuristics generation, HTML publishing, and Git versioning
# =============================================================================

LOG_FILE="/home/ubuntu/tr/logs/cron_pub.log"
DATE_NOW=$(date '+%Y-%m-%d %H:%M:%S')

echo "===== START [$DATE_NOW] =====" >> $LOG_FILE

# 1. Generate daily top50 opportunities (CSV)
echo "[$DATE_NOW] Running eur.py..." >> $LOG_FILE
python3 /home/ubuntu/tr/scripts/utils/eur.py >> $LOG_FILE 2>&1
if [ $? -eq 0 ]; then
    echo "[$DATE_NOW] eur.py OK." >> $LOG_FILE
else
    echo "[$DATE_NOW] eur.py FAILED. Aborting." >> $LOG_FILE
    exit 1
fi

# 2. Generate & publish HTML from CSV
echo "[$DATE_NOW] Running pub_1.py..." >> $LOG_FILE
python3 /home/ubuntu/tr/scripts/utils/pub_1.py >> $LOG_FILE 2>&1
if [ $? -eq 0 ]; then
    echo "[$DATE_NOW] pub_1.py OK." >> $LOG_FILE
else
    echo "[$DATE_NOW] pub_1.py FAILED. Aborting." >> $LOG_FILE
    exit 1
fi

# 3. Commit CSV to GitHub (production)
echo "[$DATE_NOW] Running push_opp.py..." >> $LOG_FILE
python3 /home/ubuntu/tr/scripts/utils/push_opp.py >> $LOG_FILE 2>&1
if [ $? -eq 0 ]; then
    echo "[$DATE_NOW] push_opp.py OK." >> $LOG_FILE
else
    echo "[$DATE_NOW] push_opp.py FAILED." >> $LOG_FILE
fi

echo "===== END [$DATE_NOW] =====" >> $LOG_FILE
echo "" >> $LOG_FILE
