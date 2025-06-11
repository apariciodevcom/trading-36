"""
===========================================================================
 Script: gen_ordenes_v2.py
===========================================================================

Descripción:
------------
Simula órdenes de trading a partir de señales generadas por estrategias.
Evalúa salidas por TP, SL o vencimiento. Incluye comisión fija y logueo.

Mejoras:
--------
- Agrega comisión fija por operación
- Incluye campo "comision" y "tipo_salida"
- Usa open/high/low/close para evaluar ejecución realista
- Validaciones robustas para columnas y errores silenciosos

=========================================================================== 
"""

import os
import pandas as pd
from datetime import datetime

TP = 0.03  # 2%
SL = 0.01  # 1%
MAX_DIAS = 5
COMISION = 0.6  # USD fijos por orden
LOG_FOLDER = "/home/ubuntu/tr/logs/ordenes"
SENALES_FOLDER = "/home/ubuntu/tr/reports/senales_heuristicas/historicas"
HIST_FOLDER = "/home/ubuntu/tr/data/historic"
SALIDA_FOLDER = "/home/ubuntu/tr/reports/ordenes"
os.makedirs(SALIDA_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)

def procesar_archivo(nombre_archivo):
    try:
        df_senales = pd.read_csv(os.path.join(SENALES_FOLDER, nombre_archivo))
        if not {"fecha", "signal", "estrategia"}.issubset(df_senales.columns):
            print(f"[SKIP] Columnas inválidas en {nombre_archivo}")
            return

        df_senales["fecha"] = pd.to_datetime(df_senales["fecha"])
        df_senales = df_senales[df_senales["signal"].isin(["buy", "sell"])].copy()
        simbolo = nombre_archivo.split("_senales")[0].upper()
        historico_path = os.path.join(HIST_FOLDER, f"{simbolo}.parquet")

        if not os.path.exists(historico_path):
            print(f"[SKIP] Sin histórico para {simbolo}")
            return

        df_prices = pd.read_parquet(historico_path)
        if not {"fecha", "open", "high", "low", "close"}.issubset(df_prices.columns):
            print(f"[ERROR] Histórico incompleto para {simbolo}")
            return

        df_prices["fecha"] = pd.to_datetime(df_prices["fecha"])
        df_prices = df_prices.sort_values("fecha").reset_index(drop=True)
        ordenes = []

        for _, fila in df_senales.iterrows():
            fecha_entrada = fila["fecha"]
            estrategia = fila["estrategia"]
            signal = fila["signal"]
            idx = df_prices.index[df_prices["fecha"] == fecha_entrada]

            if len(idx) == 0 or idx[0] >= len(df_prices) - 2:
                continue

            idx_entrada = idx[0] + 1
            precio_entrada = df_prices.loc[idx_entrada, "open"]
            salida_idx = None
            tipo_salida = "TIMEOUT"

            for i in range(1, MAX_DIAS + 1):
                if idx_entrada + i >= len(df_prices):
                    break

                fila_dia = df_prices.loc[idx_entrada + i]
                precio_salida = None

                if signal == "buy":
                    if fila_dia["high"] >= precio_entrada * (1 + TP):
                        precio_salida = precio_entrada * (1 + TP)
                        tipo_salida = "TP"
                    elif fila_dia["low"] <= precio_entrada * (1 - SL):
                        precio_salida = precio_entrada * (1 - SL)
                        tipo_salida = "SL"
                else:  # sell
                    if fila_dia["low"] <= precio_entrada * (1 - TP):
                        precio_salida = precio_entrada * (1 - TP)
                        tipo_salida = "TP"
                    elif fila_dia["high"] >= precio_entrada * (1 + SL):
                        precio_salida = precio_entrada * (1 + SL)
                        tipo_salida = "SL"

                if precio_salida:
                    salida_idx = idx_entrada + i
                    break

            if salida_idx:
                fila_salida = df_prices.loc[salida_idx]
            else:
                fila_salida = df_prices.iloc[min(idx_entrada + MAX_DIAS, len(df_prices) - 1)]
                precio_salida = fila_salida["close"]

            orden = {
                "id_orden": f"{simbolo}_{fecha_entrada.date()}_{estrategia}_{signal}",
                "fecha_entrada": fecha_entrada,
                "fecha_salida": fila_salida["fecha"],
                "precio_entrada": precio_entrada,
                "precio_salida": precio_salida,
                "signal": signal,
                "estrategia": estrategia,
                "dias": (fila_salida["fecha"] - fecha_entrada).days,
                "resultado": round(precio_salida - precio_entrada - COMISION if signal == "buy" else precio_entrada - precio_salida - COMISION, 4),
                "comision": COMISION,
                "tipo_salida": tipo_salida
            }
            ordenes.append(orden)

        if ordenes:
            df_out = pd.DataFrame(ordenes)
            salida_path = os.path.join(SALIDA_FOLDER, f"{simbolo}_ordenes.csv")
            df_out.to_csv(salida_path, index=False)
            print(f"[OK] {simbolo}: {len(ordenes)} órdenes generadas")
        else:
            print(f"[INFO] {simbolo}: sin órdenes válidas")

    except Exception as e:
        with open(os.path.join(LOG_FOLDER, "errores_gen_ordenes.log"), "a") as log:
            log.write(f"{nombre_archivo} - {str(e)}\n")

def main():
    archivos = [f for f in os.listdir(SENALES_FOLDER) if f.endswith("_senales.csv")]
    for archivo in archivos:
        procesar_archivo(archivo)

if __name__ == "__main__":
    main()
