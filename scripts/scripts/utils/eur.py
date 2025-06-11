# =========================================================================== 
# Script: top50_heuristicas.py - Seleccion de Oportunidades Heuristicas Top 50
# ===========================================================================
#
# Este script analiza historicos recientes y exporta un top 50 heuristico.
#
# Historicos: /home/ubuntu/tr/data/historic_reciente/
# Resultados: /home/ubuntu/tr/reports/senales_heuristicas/exploracion/
# Logs:       /home/ubuntu/tr/logs/utils/oportunidades_YYYY-MM-DD.log
# ===========================================================================

import os
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from datetime import datetime
import logging
import json
from ta.momentum import RSIIndicator
from ta.trend import MACD

# === CONFIGURACION ===
DATA_PATH = Path("/home/ubuntu/tr/data/historic_reciente")
OUTPUT_DIR = Path("/home/ubuntu/tr/reports/senales_heuristicas/exploracion")
LOG_DIR = Path("/home/ubuntu/tr/logs/utils")
STATUS_PATH = Path("/home/ubuntu/tr/config/system_status.json")

fecha_hoy = datetime.now().strftime("%Y-%m-%d")
log_file = LOG_DIR / f"oportunidades_{fecha_hoy}.log"

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def main():
    resumen = []

    historicos = {
        archivo.stem: pd.read_parquet(archivo)
        for archivo in DATA_PATH.glob("*.parquet")
    }

    for simbolo, df in historicos.items():
        try:
            if len(df) < 60:
                continue

            df_ultimos = df.sort_values("fecha").tail(60)
            precios = df_ultimos["close"].reset_index(drop=True)
            volumenes = df_ultimos["volume"].reset_index(drop=True)
            p25, p75 = np.percentile(precios, [25, 75])
            v25, v75 = np.percentile(volumenes, [25, 75])
            canal_pct = (p75 - p25) / ((p75 + p25) / 2) * 100

            # Nuevas métricas
            close_ult = precios.iloc[-1]
            close_ant = precios.iloc[-2]
            vol_ult = volumenes.iloc[-1]
            vol_ant = volumenes.iloc[-2]
            pct_var = ((close_ult - close_ant) / close_ant * 100) if close_ant != 0 else np.nan

            vol_media_60 = round(volumenes.mean(), 3)
            score_vol = 0 if vol_ult < v25 else 9 if vol_ult > v75 else int((vol_ult - v25) / (v75 - v25) * 8) + 1
            score_precio = 0 if close_ult < p25 else 9 if close_ult > p75 else int((close_ult - p25) / (p75 - p25) * 8) + 1

            z_close = round((close_ult - precios.mean()) / precios.std(), 2)
            z_vol = (vol_ult - volumenes.mean()) / volumenes.std()
            ret_5d = (close_ult / precios.iloc[-6] - 1) * 100
            ma20 = precios.rolling(20).mean().iloc[-1]
            ma20_pos = (close_ult - ma20) / ma20 * 100
            volat_60d = precios.pct_change().std() * np.sqrt(252) * 100

            high = df_ultimos["high"].reset_index(drop=True)
            low = df_ultimos["low"].reset_index(drop=True)
            atr = (high - low).rolling(14).mean().iloc[-1]
            atr_pct = atr / close_ult * 100 if close_ult != 0 else 0

            open_ult = df_ultimos["open"].iloc[-1]
            high_ult = df_ultimos["high"].iloc[-1]
            low_ult = df_ultimos["low"].iloc[-1]

            cuerpo = abs(close_ult - open_ult)
            rango_total = high_ult - low_ult
            body_pct = cuerpo / rango_total * 100 if rango_total != 0 else 0
            wick_sup_pct = (high_ult - max(open_ult, close_ult)) / rango_total * 100 if rango_total != 0 else 0
            wick_inf_pct = (min(open_ult, close_ult) - low_ult) / rango_total * 100 if rango_total != 0 else 0

            rsi = RSIIndicator(close=precios).rsi().iloc[-1]
            macd_ind = MACD(close=precios)
            macd_val = macd_ind.macd().iloc[-1]
            macd_signal = macd_ind.macd_signal().iloc[-1]
            macd_prev = macd_ind.macd().iloc[-2]
            signal_prev = macd_ind.macd_signal().iloc[-2]
            macd_cross = "bullish" if (macd_prev < signal_prev and macd_val > macd_signal) else \
                         "bearish" if (macd_prev > signal_prev and macd_val < macd_signal) else None

           # === Retornos logarítmicos ===
            ret_log = np.log(precios / precios.shift(1)).dropna()

            rl_ult = ret_log.iloc[-1] if len(ret_log) >= 1 else np.nan
            rl_5 = ret_log.tail(5).sum() if len(ret_log) >= 5 else np.nan
            rl_60 = ret_log.sum() if len(ret_log) == 59 else np.nan  # 60 días = 59 retornos

            rl_std_60 = ret_log.std() if len(ret_log) >= 10 else np.nan
            rl_std_5 = ret_log.tail(5).std() if len(ret_log) >= 5 else np.nan


            resumen.append({
                "simbolo": simbolo,
                "last_close": round(close_ult, 2),
                "pct_var": round(pct_var, 2),
                "volumen_ant": int(vol_ant),
                "canal_pct": canal_pct,
                "p25": round(p25, 2),
                "p75": round(p75, 2),                
                "score_volumen": score_vol,
                "score_precio": score_precio,
                "vol_media_60": vol_media_60,
                "z_close": round(z_close, 2),
                "z_vol": round(z_vol, 2),
                "ret_5d": round(ret_5d, 2),
                "ma20_pos": round(ma20_pos, 2),
                "volat_60d": round(volat_60d, 2),
                "atr_pct": round(atr_pct, 2),
                "body_pct": round(body_pct, 2),
                "wick_sup_pct": round(wick_sup_pct, 2),
                "wick_inf_pct": round(wick_inf_pct, 2),
                "RSI": round(rsi, 2),
                "MACD": round(macd_val, 2),
                "MACD_signal": round(macd_signal, 2),
                "MACD_cross": macd_cross,
                "rl_ult": round(rl_ult, 5),
                "rl_5": round(rl_5, 5),
                "rl_60": round(rl_60, 5),
                "rl_std_60": round(rl_std_60, 5),
                "rl_std_5": round(rl_std_5, 5)
            })

        except Exception as e:
            logging.error(f"Error procesando {simbolo}: {e}")
            continue

    df = pd.DataFrame(resumen)

    df["volumen_rank"] = pd.qcut(df["vol_media_60"], 10, labels=False)
    df = df[df["volumen_rank"] >= 3]
    df = df[df["score_precio"] <= 8]

    escalar = MinMaxScaler()
    df["canal_pct_norm"] = escalar.fit_transform(df[["canal_pct"]])
    df["body_pct_norm"] = escalar.fit_transform(df[["body_pct"]])
    df["z_vol_clipped"] = df["z_vol"].clip(0, 3)
    df["ret_5d_clipped"] = df["ret_5d"].clip(-5, 5)
    df["rsi_score"] = 100 - abs(df["RSI"] - 50)
    df["macd_score"] = df["MACD"]

    df["score_final"] = (
        3 * df["canal_pct_norm"] +
        2 * df["score_volumen"] +
        2 * df["score_precio"] +
        1 * df["z_vol_clipped"] +
        0.5 * df["ret_5d_clipped"] -
        1 * df["z_close"].abs() +
        1 * df["body_pct_norm"] +
        0.1 * df["rsi_score"] +
        0.1 * df["macd_score"]
    )
    df["score_final"] = round(df["score_final"], 2)

    top50 = df.sort_values("score_final", ascending=False).head(50).copy()
    top50["fecha_senal"] = pd.Timestamp.today().normalize()

    output_file = OUTPUT_DIR / f"top50_oportunidades_{fecha_hoy}.csv"
    top50.to_csv(output_file, index=False)

    logging.info(f"Archivo exportado: {output_file}")

    estado = {
        "fecha": fecha_hoy,
        "status": "OK",
        "mensaje": f"{top50.shape[0]} oportunidades generadas"
    }
    try:
        if STATUS_PATH.exists():
            with open(STATUS_PATH, "r") as f:
                status_json = json.load(f)
        else:
            status_json = {}
        status_json["top50_heuristicas"] = estado
        with open(STATUS_PATH, "w") as f:
            json.dump(status_json, f, indent=2)
    except Exception as e:
        logging.error(f"Error actualizando estado: {e}")

if __name__ == "__main__":
    main()
