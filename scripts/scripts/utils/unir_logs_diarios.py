import os
import pandas as pd
from datetime import datetime

# === CONFIGURACION ===
BASE_DIR = "/home/ec2-user/tr"
LOGS_DIR = f"{BASE_DIR}/logs"
OUTPUT_DIR = f"{BASE_DIR}/reports/logs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === FECHA DE HOY ===
hoy = datetime.utcnow().strftime("%Y-%m-%d")
csv_out = os.path.join(OUTPUT_DIR, f"merged_logs_{hoy}.csv")

# === RECOLECTAR ARCHIVOS CSV DE LOGS ===
logs_unidos = []
for root, _, files in os.walk(LOGS_DIR):
    for f in files:
        if hoy in f and f.endswith(".csv"):
            full_path = os.path.join(root, f)
            try:
                df = pd.read_csv(full_path, header=None)
                if df.shape[1] == 4:
                    df.columns = ["timestamp", "proceso", "estatus", "mensaje"]
                    logs_unidos.append(df)
                else:
                    df_check = pd.read_csv(full_path)
                    if set(df_check.columns) >= {"timestamp", "proceso", "estatus", "mensaje"}:
                        logs_unidos.append(df_check)
            except Exception as e:
                print(f"ERROR al leer {full_path}: {str(e)}")

# === UNIR Y ORDENAR ===
if logs_unidos:
    df_final = pd.concat(logs_unidos, ignore_index=True)
    df_final["timestamp"] = pd.to_datetime(df_final["timestamp"], errors="coerce")
    df_final = df_final.sort_values("timestamp")
    df_final.to_csv(csv_out, index=False)
    print(f"Logs combinados y guardados en:\n{csv_out}")

    # === RESUMEN DE ERRORES ===
    errores = df_final[df_final["estatus"] == "ERROR"]
    if not errores.empty:
        resumen = errores.groupby("proceso").size().reset_index(name="errores")
        print("\nResumen de errores por proceso:")
        print(resumen.to_string(index=False))
    else:
        print("\nNo se encontraron errores hoy.")
else:
    print("No se encontraron logs CSV compatibles para la fecha actual.")

