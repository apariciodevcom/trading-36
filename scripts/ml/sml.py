import os
import json
import pandas as pd
import numpy as np
import joblib
from datetime import datetime

BASE_DIR = "/home/ec2-user/tr"
FEATURES_DIR = f"{BASE_DIR}/data/features"
MODELOS_DIR = f"{BASE_DIR}/modelos/ml"
OUTPUT_DIR = f"{BASE_DIR}/reports/senales_ml"
STATUS_FILE = f"{BASE_DIR}/reports/summary/system_status.json"

os.makedirs(OUTPUT_DIR, exist_ok=True)

fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")

def guardar_estado(modulo, status, mensaje):
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    status_obj = {}
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            status_obj = json.load(f)
    status_obj[modulo] = {
        "fecha": fecha_hoy,
        "ultima_ejecucion": now_str,
        "status": status,
        "mensaje": mensaje
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status_obj, f, indent=2)

# Detectar modelos disponibles
modelos = [f for f in os.listdir(MODELOS_DIR) if f.endswith(".pkl")]
if not modelos:
    print("No se encontraron modelos en:", MODELOS_DIR)
    guardar_estado("senales_ml", "ERROR", "No se encontraron modelos")
    exit(1)

# Cargar features disponibles
features_files = [f for f in os.listdir(FEATURES_DIR) if f.endswith("_features.parquet")]
if not features_files:
    print("No se encontraron features en:", FEATURES_DIR)
    guardar_estado("senales_ml", "ERROR", "No se encontraron archivos de features")
    exit(1)

exitos = 0
errores = 0

# Aplicar cada modelo a todos los archivos de features
for modelo_file in modelos:
    modelo_path = os.path.join(MODELOS_DIR, modelo_file)
    model_name = modelo_file.replace(".pkl", "")
    print(f"Usando modelo: {model_name}")

    output_model_dir = os.path.join(OUTPUT_DIR, model_name)
    os.makedirs(output_model_dir, exist_ok=True)

    try:
        modelo = joblib.load(modelo_path)
    except Exception as e:
        print(f"Error cargando modelo {modelo_file}: {str(e)}")
        errores += 1
        continue

    if not hasattr(modelo, "feature_names_in_"):
        print(f"Modelo {modelo_file} no contiene metadata de features.")
        errores += 1
        continue

    feature_names = list(modelo.feature_names_in_)

    for feat_file in features_files:
        try:
            symbol = feat_file.replace("_features.parquet", "")
            df = pd.read_parquet(os.path.join(FEATURES_DIR, feat_file))

            if df.shape[0] < 10:
                print(f"{symbol} muy pocos datos, omitido")
                continue

            df_numeric = df.select_dtypes(include=[np.number])
            for col in feature_names:
                if col not in df_numeric.columns:
                    df_numeric[col] = np.nan
            X = df_numeric[feature_names].bfill().ffill()

            y_pred = modelo.predict(X)
            df["pred_senal"] = np.where(y_pred == 1, "buy", "hold")
            df["symbol"] = symbol

            output_path = os.path.join(output_model_dir, f"{symbol}.csv")
            df.to_csv(output_path, index=False)
            print(f"Senales generadas: {symbol} con {len(df)} filas")
            exitos += 1

        except Exception as e:
            print(f"Error en {symbol} con {modelo_file}: {str(e)}")
            errores += 1

# === Estado final ===
if exitos > 0:
    guardar_estado("senales_ml", "OK", f"{exitos} archivos generados correctamente")
else:
    guardar_estado("senales_ml", "ERROR", "No se genero ninguna senal")
