"""
===========================================================================
 Estrategia: Breakout por Volumen (versión CORREGIDA)
===========================================================================

Descripción:
------------
Detecta rupturas confirmadas por volumen y cuerpo de vela, 
aplicando ahora un desplazamiento temporal (shift) en los cálculos
para evitar que el valor actual contamine el rolling.

Mejoras:
--------
- Aplicación de .shift(1) para indicadores técnicos (max, min, vol_avg, cuerpo_avg)
- Log de condiciones booleanas para auditoría
- Formato seguro para auditoría y backtesting

Condiciones:
------------
BUY  → close > max_20 (shifted) AND volume > vol_avg (shifted) AND cuerpo > cuerpo_avg (shifted)  
SELL → close < min_20 (shifted) AND volume > vol_avg (shifted) AND cuerpo > cuerpo_avg (shifted)

Salida:
-------
['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("breakout_volumen_fix")

def generar_senales(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "high", "low", "open", "volume"}
        if not req.issubset(df.columns):
            logger.warning(f"Faltan columnas: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < 30:
            return df_as_hold(df, "datos insuficientes")

        # Aplicar .shift(1) para no incluir el día actual en los umbrales
        df["max_20"] = df["high"].shift(1).rolling(20).max()
        df["min_20"] = df["low"].shift(1).rolling(20).min()
        df["vol_avg"] = df["volume"].shift(1).rolling(20).mean()
        df["cuerpo"] = abs(df["close"] - df["open"])
        df["cuerpo_avg"] = df["cuerpo"].shift(1).rolling(20).mean()

        # Condiciones booleanas
        df["buy_cond"] = (df["close"] > df["max_20"]) &                          (df["volume"] > df["vol_avg"]) &                          (df["cuerpo"] > df["cuerpo_avg"])

        df["sell_cond"] = (df["close"] < df["min_20"]) &                           (df["volume"] > df["vol_avg"]) &                           (df["cuerpo"] > df["cuerpo_avg"])

        logger.info(f"BUY cond: {df['buy_cond'].sum()}, SELL cond: {df['sell_cond'].sum()}")

        # Señales
        df["signal"] = "hold"
        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"
        df["estrategia"] = "breakout_volumen_fix"

        return df[["fecha", "signal", "estrategia"]]

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return df_as_hold(df, "exception")

def df_as_hold(df: pd.DataFrame, razon: str) -> pd.DataFrame:
    logger.info(f"HOLD por: {razon}")
    df = df.copy()
    if "fecha" not in df.columns:
        return pd.DataFrame(columns=["fecha", "signal", "estrategia"])
    df["signal"] = "hold"
    df["estrategia"] = "breakout_volumen_fix"
    return df[["fecha", "signal", "estrategia"]]
