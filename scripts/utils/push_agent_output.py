# =============================================================================
# push_agent_output.py
# =============================================================================
# Commits and pushes the output files of a specific trading agent to the
# 'production' branch of the trading-36 repository.
# This script is modular and can be reused for any agent.
# =============================================================================

import os
import subprocess
from datetime import datetime
from pathlib import Path

# === CONFIG ===
AGENT_NAME = "agent1"  # Change this for other agents
REPO_DIR = Path("/home/ubuntu/trading-36")
AGENT_DIR = REPO_DIR / f"trading_agents/{AGENT_NAME}"
EXTENSIONS = [".csv", ".json", ".log", ".md"]
FECHA = datetime.now().strftime("%Y-%m-%d")
COMMIT_MSG = f"Update {AGENT_NAME} output files for {FECHA}"

# === VERIFY PATH ===
if not AGENT_DIR.exists():
    print(f"[ERROR] Agent directory not found: {AGENT_DIR}")
    exit(1)

# === COLLECT FILES TO ADD ===
files_to_add = []
for file in AGENT_DIR.iterdir():
    if file.suffix in EXTENSIONS and file.is_file():
        files_to_add.append(file)

if not files_to_add:
    print("[INFO] No output files to add.")
    exit(0)

# === GIT OPERATIONS ===
os.chdir(REPO_DIR)
subprocess.run(["git", "checkout", "production"], check=True)

for file_path in files_to_add:
    subprocess.run(["git", "add", "-f", str(file_path)], check=True)

# Commit only if there are changes
diff_result = subprocess.run(["git", "diff", "--cached", "--quiet"])
if diff_result.returncode == 1:
    subprocess.run(["git", "commit", "-m", COMMIT_MSG], check=True)
    subprocess.run(["git", "push", "origin", "production"], check=True)
    print(f"[OK] Commit and push completed for {AGENT_NAME}")
else:
    print("[INFO] No changes to commit.")
