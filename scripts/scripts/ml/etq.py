# etq.py - Generar etiquetas ML a partir de señales heuristicas + retornos reales
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json

# === RUTAS ===
BASE_DIR = "/home/ec2-user/tr"
FEATURES_DIR = f"{BASE_DIR}/data/features"
HISTORIC_DIR = f"{BASE_DIR}/data/historic"
SENALES_DIR = f"{BASE_DIR}/reports/senales_heuristicas/diarias"
OUTPUT_DIR = f"{BASE_DIR}/data/features_etiquetados"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === PARAMETROS ===
RETORNO_OBJETIVO = 0.02  # 2%
DIAS_RETORNO = 3
fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")

# === FUNCIONES ===
def calcular_retorno_futuro(df, dias):
    return df["close"].shift(-dias) / df["close"] - 1

def generar_etiquetas(symbol):
    try:
        path_feat = os.path.join(FEATURES_DIR, f"{symbol}_features.parquet")
        path_hist = os.path.join(HISTORIC_DIR, f"{symbol}.parquet")
        path_senales = os.path.join(SENALES_DIR, f"{symbol}_*.csv")

        if not os.path.exists(path_feat) or not os.path.exists(path_hist):
            return None

        df_feat = pd.read_parquet(path_feat)
        df_hist = pd.read_parquet(path_hist)
        df_hist["datetime"] = pd.to_datetime(df_hist["datetime"])
        df_hist.set_index("datetime", inplace=True)

        # Calcular retorno futuro en base a datos reales
        df_feat["datetime"] = pd.to_datetime(df_feat["datetime"])
        df_feat = df_feat.sort_values("datetime")
        df_feat.set_index("datetime", inplace=True)
        df_feat["retorno_futuro"] = calcular_retorno_futuro(df_feat, DIAS_RETORNO)

        # Cargar senales heuristicas para ese simbolo
        senales_files = [f for f in os.listdir(SENALES_DIR) if f.startswith(symbol) and f.endswith(".csv")]
        df_feat["senal"] = "hold"

        for file in senales_files:
            df_senal = pd.read_csv(os.path.join(SENALES_DIR, file))
            df_senal["fecha"] = pd.to_datetime(df_senal["fecha"])
            df_senal = df_senal[df_senal["signal"] == "buy"]

            for fecha in df_senal["fecha"]:
                if fecha in df_feat.index:
                    retorno = df_feat.loc[fecha, "retorno_futuro"]
                    if isinstance(retorno, pd.Series):
                        retorno = retorno.values[0]
                    if retorno > RETORNO_OBJETIVO:
                        df_feat.at[fecha, "senal"] = "buy"
                    else:
                        df_feat.at[fecha, "senal"] = "hold"

        df_feat.reset_index(inplace=True)
        df_feat.to_parquet(os.path.join(OUTPUT_DIR, f"{symbol}_etiquetado.parquet"), index=False)
        return symbol

    except Exception as e:
        print(f"Error con {symbol}: {str(e)}")
        return None

# === PROCESAR TODOS LOS SIMBOLOS ===
symbols = [f.replace("_features.parquet", "") for f in os.listdir(FEATURES_DIR) if f.endswith("_features.parquet")]
total = 0
for sym in symbols:
    res = generar_etiquetas(sym)
    if res:
        total += 1

print(f"Etiquetas generadas para {total} simbolos")
