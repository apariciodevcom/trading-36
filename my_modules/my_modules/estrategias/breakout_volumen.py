"""
===========================================================================
 Estrategia: Breakout por Volumen (original con ordenamiento)
===========================================================================

Descripción:
------------
Detecta señales de ruptura cuando el precio supera el máximo/mínimo de
los últimos 20 días, confirmadas por volumen superior al promedio.

Mejora aplicada:
----------------
- Se asegura el orden cronológico por fecha antes de aplicar rolling()

Condiciones:
------------
BUY  → close > max_20.shift(1) AND volume > vol_avg_20  
SELL → close < min_20.shift(1) AND volume > vol_avg_20

Salida:
-------
['fecha', 'signal', 'estrategia']

=========================================================================== 
"""

import pandas as pd
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("breakout_volumen_ordered")

def generar_senales(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df = df.copy()
        columnas = {"fecha", "close", "high", "low", "volume"}
        if not columnas.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {columnas - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        # Ordenar por fecha para evitar errores en rolling
        df = df.sort_values("fecha").reset_index(drop=True)

        df["max_20"] = df["high"].rolling(20).max().shift(1)
        df["min_20"] = df["low"].rolling(20).min().shift(1)
        df["vol_avg_20"] = df["volume"].rolling(20).mean()

        df["signal"] = "hold"
        df.loc[(df["close"] > df["max_20"]) & (df["volume"] > df["vol_avg_20"]), "signal"] = "buy"
        df.loc[(df["close"] < df["min_20"]) & (df["volume"] > df["vol_avg_20"]), "signal"] = "sell"

        df["estrategia"] = "breakout_volumen_ordered"
        return df[["fecha", "signal", "estrategia"]]

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return df_as_hold(df, "exception")

def df_as_hold(df: pd.DataFrame, razon: str) -> pd.DataFrame:
    logger.info(f"Retornando HOLD por: {razon}")
    df = df.copy()
    if "fecha" not in df.columns:
        return pd.DataFrame(columns=["fecha", "signal", "estrategia"])
    df["signal"] = "hold"
    df["estrategia"] = "breakout_volumen_ordered"
    return df[["fecha", "signal", "estrategia"]]
