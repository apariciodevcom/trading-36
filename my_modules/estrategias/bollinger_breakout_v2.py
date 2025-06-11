"""
===========================================================================
 Estrategia: Bollinger Breakout (dinámico por volatilidad) - LeanTech Trading
===========================================================================

Descripcion:
------------
Detecta rupturas sobre/bajo bandas de Bollinger con un umbral `s`
configurable, que puede ser dinámicamente ajustado segun la volatilidad 
del mercado (medida por ATR).

- Señal BUY:  close > upper_band
- Señal SELL: close < lower_band
- Señal HOLD en otros casos

Parametros:
-----------
- s: factor multiplicador de desviación estándar (float, default=2.0)
- ajuste_volatilidad: bool (si True, `s` se ajusta dinámicamente por ATR)

Columnas requeridas:
---------------------
- 'fecha', 'close', 'high', 'low'

Salida:
-------
DataFrame con columnas: ['fecha', 'signal', 'estrategia']

=========================================================================== 
"""

import pandas as pd
from my_modules.logger_estrategia import configurar_logger
import ta

logger = configurar_logger("bollinger_breakout_voladj")

def generar_senales(df: pd.DataFrame, s: float = 2.0, ajuste_volatilidad: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        columnas = {"fecha", "close", "high", "low"}
        if not columnas.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {columnas - set(df.columns)}")
            return df_as_hold(df, razon="faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < 25:
            logger.warning("Datos insuficientes")
            return df_as_hold(df, razon="datos insuficientes")

        df["ma20"] = df["close"].rolling(20).mean()
        df["std"] = df["close"].rolling(20).std()

        if ajuste_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            vol_relativa = (df["atr"] / df["close"]).clip(0, 0.1)  # limitar extremos
            s_dynamic = (s - 0.5) + vol_relativa * 20  # ej: s ~ 1.5 - 3.5
            df["upper"] = df["ma20"] + s_dynamic * df["std"]
            df["lower"] = df["ma20"] - s_dynamic * df["std"]
        else:
            df["upper"] = df["ma20"] + s * df["std"]
            df["lower"] = df["ma20"] - s * df["std"]

        df["signal"] = "hold"
        df.loc[df["close"] > df["upper"], "signal"] = "buy"
        df.loc[df["close"] < df["lower"], "signal"] = "sell"

        df["estrategia"] = "bollinger_breakout_voladj"
        logger.info(f"Señales - buy: {sum(df['signal']=='buy')}, sell: {sum(df['signal']=='sell')}")

        return df[["fecha", "signal", "estrategia"]]

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return df_as_hold(df, razon="exception")

def df_as_hold(df: pd.DataFrame, razon: str) -> pd.DataFrame:
    logger.info(f"Retornando HOLD por: {razon}")
    df = df.copy()
    if "fecha" not in df.columns:
        return pd.DataFrame(columns=["fecha", "signal", "estrategia"])
    df["signal"] = "hold"
    df["estrategia"] = "bollinger_breakout_voladj"
    return df[["fecha", "signal", "estrategia"]]
