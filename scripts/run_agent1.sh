#!/bin/bash
# =============================================================================
# run_agent1.sh - Executes agent1 from production and pushes results to GitHub
# =============================================================================

source /home/ubuntu/tr/.keys.sh
LOG_FILE="/home/ubuntu/tr/logs/agent1.log"
DATE_NOW=$(date '+%Y-%m-%d %H:%M:%S')

echo "===== START [$DATE_NOW] =====" >> $LOG_FILE

# Run the agent from the production environment
python3 /home/ubuntu/tr/trading_agents/agent1/agent1.py >> $LOG_FILE 2>&1
AGENT_EXIT=$?

if [ $AGENT_EXIT -eq 0 ]; then
    echo "[$DATE_NOW] agent1.py completed successfully." >> $LOG_FILE

    # Publish output from production using modular publishing script
    python3 /home/ubuntu/tr/scripts/utils/push_agent_output.py >> $LOG_FILE 2>&1
    echo "[$DATE_NOW] push_agent_output.py completed." >> $LOG_FILE
else
    echo "[$DATE_NOW] agent1.py FAILED." >> $LOG_FILE
fi

echo "===== END [$DATE_NOW] =====" >> $LOG_FILE
echo "" >> $LOG_FILE
