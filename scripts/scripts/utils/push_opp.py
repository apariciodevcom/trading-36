# =============================================================================
# push_opportunities.py
# =============================================================================
# Copies the daily opportunities CSV into trading-36 repo under:
# reports/senales_heuristicas/diarias/
# Then commits and pushes to the 'production' branch as a historical record.
# =============================================================================

import os
import shutil
from datetime import datetime
from pathlib import Path
import subprocess

# === CONFIG ===
FECHA = datetime.now().strftime("%Y-%m-%d")
SRC = Path(f"/home/ubuntu/tr/reports/senales_heuristicas/exploracion/top50_oportunidades_{FECHA}.csv")
DEST_REPO = Path("/home/ubuntu/trading-36")
DEST_PATH = DEST_REPO / "reports/senales_heuristicas/diarias"
COMMIT_MSG = f"Add daily opportunities report for {FECHA}"

# === CHECK FILE EXISTS ===
if not SRC.exists():
    print(f"[ERROR] File not found: {SRC}")
    exit(1)

# === COPY FILE TO PRODUCTION REPO ===
DEST_PATH.mkdir(parents=True, exist_ok=True)
dest_file = DEST_PATH / SRC.name
shutil.copy(SRC, dest_file)
print(f"[OK] Copied to: {dest_file}")

# === COMMIT AND PUSH ===
os.chdir(DEST_REPO)
subprocess.run(["git", "checkout", "production"], check=True)
subprocess.run(["git", "add", "-f", str(dest_file)], check=True)

commit_result = subprocess.run(["git", "diff", "--cached", "--quiet"])
if commit_result.returncode == 1:
    subprocess.run(["git", "commit", "-m", COMMIT_MSG], check=True)
    subprocess.run(["git", "push", "origin", "production"], check=True)
    print("[OK] Commit and push completed.")
else:
    print("[INFO] No changes to commit.")

subprocess.run(["git", "push", "origin", "production"], check=True)
print("[OK] Commit and push completed.")
