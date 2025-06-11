#!/usr/bin/env python3
import os
import sys
import pandas as pd
import logging
import json
import importlib
from datetime import datetime, timedelta

# === CONFIGURACION ===
BASE_DIR = "/home/ec2-user/tr"
sys.path.append(BASE_DIR)
HISTORIC_DIR = f"{BASE_DIR}/data/historic"
SENALES_DIR = f"{BASE_DIR}/reports/senales_historicas"
RESULTADOS_DIR = f"{BASE_DIR}/reports/backtest_heuristicas"
SUMMARY_DIR = f"{BASE_DIR}/reports/summary"
RESUMEN_PATH = os.path.join(RESULTADOS_DIR, "resumen_metricas_full.csv")
LOG_DIR = f"{BASE_DIR}/logs/backtest"
GRUPOS_PATH = f"{BASE_DIR}/config/symbol_groups.json"
ESTRATEGIAS_DIR = f"{BASE_DIR}/my_modules/estrategias"
STATUS_FILE = os.path.join(SUMMARY_DIR, "system_status.json")
DIAS = 360
DIAS_HOLD = 3
FECHA = datetime.utcnow().strftime("%Y-%m-%d")

os.makedirs(SENALES_DIR, exist_ok=True)
os.makedirs(RESULTADOS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# === LOGGING ===
log_file = os.path.join(LOG_DIR, f"run_backtest_{FECHA}.csv")
log_persistente = os.path.join(LOG_DIR, "run_backtest.log")

logger = logging.getLogger("backtest_full")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s,%(name)s,%(levelname)s,%(message)s", datefmt="%Y-%m-%d %H:%M:%S")

fh1 = logging.FileHandler(log_file)
fh1.setFormatter(formatter)
logger.addHandler(fh1)

fh2 = logging.FileHandler(log_persistente)
fh2.setFormatter(formatter)
logger.addHandler(fh2)

# === FUNCION ESTANDAR DE ESTADO ===
def guardar_estado(modulo, status, mensaje):
    now_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    status_obj = {}
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r") as f:
            status_obj = json.load(f)
    status_obj[modulo] = {
        "fecha": FECHA,
        "ultima_ejecucion": now_str,
        "status": status,
        "mensaje": mensaje
    }
    with open(STATUS_FILE, "w") as f:
        json.dump(status_obj, f, indent=2)

# === Cargar simbolos ===
symbols = set()
try:
    with open(GRUPOS_PATH, "r") as f:
        grupos = json.load(f)
        for lista in grupos.values():
            symbols.update(lista)
except Exception as e:
    logger.error(f"Error al leer symbol_groups.json: {str(e)}")
    guardar_estado("backtest_heuristico", "ERROR", "No se pudo leer symbol_groups.json")
    sys.exit(1)

# === Cargar estrategias ===
estrategias = {}
mod_path = "my_modules.estrategias"
for archivo in os.listdir(ESTRATEGIAS_DIR):
    if archivo.endswith(".py") and not archivo.startswith("__"):
        nombre = archivo.replace(".py", "")
        try:
            mod = importlib.import_module(f"{mod_path}.{nombre}")
            estrategias[nombre] = mod.generar_senales
            logger.info(f"{nombre} cargada correctamente")
        except Exception as e:
            logger.error(f"Error al cargar {nombre}: {str(e)}")

# === Paso 1: Generar señales ===
for symbol in sorted(symbols):
    path = os.path.join(HISTORIC_DIR, f"{symbol}.parquet")
    if not os.path.exists(path):
        logger.warning(f"{symbol} sin historico")
        continue
    try:
        df = pd.read_parquet(path)
        df["datetime"] = pd.to_datetime(df["datetime"])
        df.set_index("datetime", inplace=True)
        fecha_corte = datetime.utcnow().date() - timedelta(days=DIAS)
        df = df[df.index.date >= fecha_corte]
        if df.empty:
            logger.warning(f"{symbol} sin datos suficientes")
            continue

        for nombre, funcion in estrategias.items():
            try:
                df_senales = funcion(df)
                if "fecha" in df_senales.columns and "signal" in df_senales.columns:
                    df_senales = df_senales[["fecha", "signal"]]
                    salida = os.path.join(SENALES_DIR, f"{symbol}_{nombre}.csv")
                    df_senales.to_csv(salida, index=False)
                    logger.info(f"{symbol} - {nombre} señales OK")
                else:
                    logger.warning(f"{symbol} - {nombre} columnas faltantes")
            except Exception as e:
                logger.error(f"{symbol} - {nombre} fallo al generar señales: {str(e)}")
    except Exception as e:
        logger.error(f"{symbol} fallo al leer historico: {str(e)}")

# === Paso 2: Backtest ===
def backtest(df_signals, df_prices):
    operaciones = []
    df_prices.index = pd.to_datetime(df_prices.index)
    df_signals["fecha"] = pd.to_datetime(df_signals["fecha"])
    df_signals = df_signals[df_signals["signal"] == "buy"]
    for fecha_entrada in df_signals["fecha"]:
        if fecha_entrada not in df_prices.index:
            continue
        try:
            precio_entrada = df_prices.loc[fecha_entrada]["close"]
            fecha_salida = fecha_entrada + timedelta(days=DIAS_HOLD)
            df_sal = df_prices[df_prices.index > fecha_entrada]
            df_sal = df_sal[df_sal.index <= fecha_salida]
            if df_sal.empty:
                continue
            precio_salida = df_sal.iloc[-1]["close"]
            retorno = (precio_salida - precio_entrada) / precio_entrada * 100
            operaciones.append({
                "fecha_entrada": fecha_entrada.date(),
                "precio_entrada": round(precio_entrada, 2),
                "fecha_salida": df_sal.index[-1].date(),
                "precio_salida": round(precio_salida, 2),
                "retorno_pct": round(retorno, 2)
            })
        except Exception as e:
            logger.warning(f"Backtest error en {fecha_entrada}: {e}")
    return operaciones

# === Ejecutar backtest ===
for archivo in os.listdir(SENALES_DIR):
    if archivo.endswith(".csv"):
        try:
            symbol = archivo.split("_")[0]
            estrategia = "_".join(archivo.replace(".csv", "").split("_")[1:])
            ruta = os.path.join(SENALES_DIR, archivo)
            ruta_hist = os.path.join(HISTORIC_DIR, f"{symbol}.parquet")
            if not os.path.exists(ruta_hist):
                logger.warning(f"{symbol} historico no encontrado para backtest")
                continue
            df_senales = pd.read_csv(ruta)
            df_precio = pd.read_parquet(ruta_hist)
            df_precio["datetime"] = pd.to_datetime(df_precio["datetime"])
            df_precio.set_index("datetime", inplace=True)
            ops = backtest(df_senales, df_precio)
            if ops:
                df_result = pd.DataFrame(ops)
                df_result.to_csv(os.path.join(RESULTADOS_DIR, f"{symbol}_{estrategia}_bt.csv"), index=False)
                logger.info(f"{symbol} - {estrategia} backtest OK con {len(ops)} operaciones")
            else:
                logger.info(f"{symbol} - {estrategia} sin operaciones")
        except Exception as e:
            logger.error(f"Fallo backtest {archivo}: {str(e)}")

# === Paso 3: Calculo de metricas ===
registros = []
for archivo in os.listdir(RESULTADOS_DIR):
    if archivo.endswith("_bt.csv"):
        ruta = os.path.join(RESULTADOS_DIR, archivo)
        try:
            df = pd.read_csv(ruta)
            if df.empty:
                continue
            symbol = archivo.split("_")[0]
            estrategia = "_".join(archivo.replace("_bt.csv", "").split("_")[1:])
            total_ops = len(df)
            ganadoras = df[df["retorno_pct"] > 0]
            perdedoras = df[df["retorno_pct"] <= 0]
            promedio = df["retorno_pct"].mean()
            mediana = df["retorno_pct"].median()
            ganancia_total = ganadoras["retorno_pct"].sum()
            perdida_total = perdedoras["retorno_pct"].sum()
            profit_factor = round((ganancia_total / abs(perdida_total)) if perdida_total != 0 else float("inf"), 2)
            win_rate = round(len(ganadoras) / total_ops * 100, 2)
            payoff_ratio = round(ganadoras["retorno_pct"].mean() / abs(perdedoras["retorno_pct"].mean()), 2) if not perdedoras.empty else float("inf")
            std = df["retorno_pct"].std()
            sharpe = round(promedio / std, 2) if std > 0 else float("inf")
            drawdown = round(df["retorno_pct"].cumsum().cummax() - df["retorno_pct"].cumsum(), 2).max()
            registros.append({
                "Simbolo": symbol,
                "Estrategia": estrategia,
                "Operaciones": total_ops,
                "WinRate_%": win_rate,
                "RetornoPromedio_%": round(promedio, 2),
                "MedianaRetorno_%": round(mediana, 2),
                "ProfitFactor": profit_factor,
                "PayoffRatio": payoff_ratio,
                "SharpeSimplificado": sharpe,
                "DrawdownMax_%": drawdown
            })
        except Exception as e:
            logger.warning(f"Error leyendo resultados de {archivo}: {e}")

# === Guardar resumen y estado ===
if registros:
    df_metricas = pd.DataFrame(registros)
    df_metricas.to_csv(RESUMEN_PATH, index=False)
    logger.info(f"Resumen guardado en {RESUMEN_PATH}")
    guardar_estado("backtest_heuristico", "OK", f"{len(registros)} combinaciones evaluadas")
else:
    logger.warning("No se encontraron resultados para generar resumen")
    guardar_estado("backtest_heuristico", "ERROR", "No se generaron resultados de backtest heuristico")
