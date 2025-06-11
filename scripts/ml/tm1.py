import os
import sys
import pandas as pd
import joblib
from xgboost import XGBClassifier
from datetime import datetime
from pathlib import Path

# === CONFIGURACION ===
INPUT_FILE = "/home/ubuntu/tr/data/entrenamiento/features_training.parquet"
OUTPUT_DIR = "/home/ubuntu/tr/modelos/ml"
LOG_FILE = f"/home/ubuntu/tr/logs/ml/tm1_{datetime.now().date()}.log"
TARGET_COLUMN = "senal"

# === PARAMETROS XGBOOST ===
PARAMS = {
    "n_estimators": 100,
    "max_depth": 4,
    "learning_rate": 0.1,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "random_state": 42,
    "use_label_encoder": False,
    "eval_metric": "mlogloss"
}

# === LOG SIMPLE ===
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG_FILE, "a") as f:
        f.write(linea + "\n")

# === FLUJO PRINCIPAL ===
def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    simbolo_filtrado = sys.argv[1].upper() if len(sys.argv) > 1 else None

    try:
        df = pd.read_parquet(INPUT_FILE)
        log(f"Archivo cargado: {df.shape[0]} filas")
    except Exception as e:
        log(f"ERROR al cargar {INPUT_FILE}: {e}")
        return

    if simbolo_filtrado:
        df = df[df["simbolo"] == simbolo_filtrado]
        log(f"Entrenando modelo SOLO para simbolo: {simbolo_filtrado}")

    if TARGET_COLUMN not in df.columns:
        log(f"ERROR: columna '{TARGET_COLUMN}' no encontrada")
        return

    if len(df) < 20:
        log(f"ERROR: datos insuficientes para entrenamiento ({len(df)} filas)")
        return

    try:
        X = df.drop(columns=[TARGET_COLUMN, "simbolo", "fecha"], errors="ignore")
        y = df[TARGET_COLUMN]
        model = XGBClassifier(**PARAMS)
        model.fit(X, y)
        nombre = f"xgboost_{simbolo_filtrado.lower()}_" if simbolo_filtrado else "xgboost_"
        nombre += datetime.now().strftime("%Y%m%d_%H%M") + ".pkl"
        joblib.dump(model, f"{OUTPUT_DIR}/{nombre}")
        log(f"Modelo guardado como: {nombre}")
    except Exception as e:
        log(f"ERROR durante entrenamiento: {e}")

if __name__ == "__main__":
    main()
