import os
import json
import pandas as pd
import numpy as np
import logging
from datetime import datetime

BASE_DIR = "/home/ec2-user/tr"
SENALES_DIR = f"{BASE_DIR}/reports/senales_ml"
RESULTADOS_DIR = f"{BASE_DIR}/reports/backtest_ml"
LOG_DIR = f"{BASE_DIR}/logs/bt"
STATUS_FILE = f"{BASE_DIR}/reports/summary/system_status.json"

os.makedirs(RESULTADOS_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

fecha_hoy = datetime.utcnow().strftime("%Y-%m-%d")
log_file = os.path.join(LOG_DIR, f"bt_{fecha_hoy}.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s,backtest,%(levelname)s,%(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

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

def calcular_metricas(df):
    df = df.copy()
    df = df.sort_values("datetime")
    df["retorno"] = df["close"].pct_change().shift(-1)
    df = df.dropna(subset=["retorno"])

    df["resultado"] = np.where(df["buy"], df["retorno"], 0)
    trades = df["buy"].sum()
    ganancia_total = df["resultado"].sum()
    promedio_op = df["resultado"].mean() if trades > 0 else 0
    winrate = (df["resultado"] > 0).sum() / trades if trades > 0 else 0
    retorno_acum = (df["resultado"] + 1).prod() - 1
    volatilidad = df["resultado"].std()
    sharpe = df["resultado"].mean() / df["resultado"].std() if df["resultado"].std() > 0 else 0
    ganadoras = df[df["resultado"] > 0]["resultado"].sum()
    perdedoras = abs(df[df["resultado"] < 0]["resultado"].sum())
    profit_factor = ganadoras / perdedoras if perdedoras > 0 else np.nan

    curva = (df["resultado"] + 1).cumprod()
    max_acum = curva.cummax()
    drawdown = (curva - max_acum) / max_acum
    max_drawdown = drawdown.min()

    return {
        "trades": int(trades),
        "ganancia_total": float(round(ganancia_total, 4)),
        "promedio_op": float(round(promedio_op, 6)),
        "winrate": float(round(winrate, 4)),
        "retorno_acumulado": float(round(retorno_acum, 4)),
        "volatilidad": float(round(volatilidad, 6)),
        "sharpe": float(round(sharpe, 4)),
        "profit_factor": float(round(profit_factor, 4)) if not np.isnan(profit_factor) else None,
        "max_drawdown": float(round(max_drawdown, 4))
    }

def main():
    logging.info("Inicio del backtesting ML")
    modelos = os.listdir(SENALES_DIR)
    if not modelos:
        logging.error("No hay carpetas de modelos en senales_ml")
        guardar_estado("backtest", "ERROR", "No hay carpetas de modelos en senales_ml")
        return

    modelos_exitosos = 0

    for modelo in modelos:
        path_modelo = os.path.join(SENALES_DIR, modelo)
        if not os.path.isdir(path_modelo):
            continue

        resumen = []
        for file in os.listdir(path_modelo):
            if not file.endswith(".csv"):
                continue
            symbol = file.replace(".csv", "")
            try:
                df = pd.read_csv(os.path.join(path_modelo, file))
                if "datetime" not in df.columns or "close" not in df.columns:
                    raise ValueError("Faltan columnas necesarias")
                columna = "pred_senal" if "pred_senal" in df.columns else "senal"
                df["buy"] = df[columna] == "buy"
                resultado = calcular_metricas(df)
                resultado["symbol"] = symbol
                resumen.append(resultado)
                logging.info("%s - %s OK: %s", modelo, symbol, resultado)
            except Exception as e:
                logging.error("%s - %s ERROR: %s", modelo, symbol, str(e))

        if resumen:
            df_resumen = pd.DataFrame(resumen)
            output_file = os.path.join(RESULTADOS_DIR, f"{modelo}_resumen.csv")
            df_resumen.to_csv(output_file, index=False)
            logging.info("Resumen guardado: %s", output_file)
            modelos_exitosos += 1

    if modelos_exitosos > 0:
        guardar_estado("backtest", "OK", f"{modelos_exitosos} modelos procesados correctamente")
    else:
        guardar_estado("backtest", "ERROR", "No se genero ningun resumen de backtest")

    logging.info("Fin del backtesting")

if __name__ == "__main__":
    main()
