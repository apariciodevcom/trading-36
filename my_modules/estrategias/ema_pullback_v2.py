"""
===========================================================================
 Estrategia: EMA Pullback - v2 (relajada)
===========================================================================

Descripción:
------------
Detecta retrocesos a la EMA20 dentro de una tendencia alcista, y genera
señal de compra cuando el precio empieza a rebotar desde debajo (o cerca) 
de la media hacia arriba, con lógica más tolerante.

Ajustes específicos:
--------------------
- El "pullback" se permite hasta +1% por encima de la EMA20
- El rebote se relaja a `close >= close.shift(1)`

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("ema_pullback_v2")

def generar_senales(df: pd.DataFrame, usar_filtro_volatilidad: bool = True) -> pd.DataFrame:
    try:
        df = df.copy()
        req_cols = {"fecha", "close", "high", "low"}
        if not req_cols.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req_cols - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)

        if len(df) < 25:
            return df_as_hold(df, "datos insuficientes")

        df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
        df["tendencia_alcista"] = df["ema_20"] > df["ema_20"].shift(1)
        df["pullback"] = df["close"] < df["ema_20"] * 1.01  # relajado: permite hasta +1%
        df["rebote"] = df["close"] >= df["close"].shift(1)  # relajado: >= en lugar de >

        df["buy_cond"] = df["tendencia_alcista"] & df["pullback"] & df["rebote"]

        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["buy_cond"] &= df["atr_ratio"] > 0.008

        df["signal"] = "hold"
        df.loc[df["buy_cond"], "signal"] = "buy"

        df["prev_buy"] = df["buy_cond"].shift(1).astype("bool").fillna(False)
        df["end_buy"] = df["prev_buy"] & ~df["buy_cond"]
        df.loc[df["end_buy"], "signal"] = "sell"

        df["estrategia"] = "ema_pullback_v2"

        logger.info(f"Señales: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "ema_pullback_v2"
    return df[["fecha", "signal", "estrategia"]]
