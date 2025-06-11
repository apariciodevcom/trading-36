"""
===========================================================================
 Estrategia: Cruce de MACD - v2
===========================================================================

Descripción:
------------
Detecta cruces entre MACD y su línea de señal para generar señales de
compra y venta. Incluye mejoras para filtrar señales de ruido y
condiciones de mercado con confirmaciones opcionales.

Mejoras implementadas:
-----------------------
- Orden temporal asegurado
- Validación de longitud mínima
- Confirmación opcional de cruce real (sostenido)
- Filtro opcional de volatilidad (ATR ratio)
- Manejo explícito de columnas faltantes y fallback a 'hold'

Parámetros:
-----------
- usar_confirmacion_cruce: bool = False
- usar_filtro_volatilidad: bool = False

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("macd_cruce_v2")

def generar_senales(df: pd.DataFrame,
                    usar_confirmacion_cruce: bool = False,
                    usar_filtro_volatilidad: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "high", "low"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)

        if len(df) < 35:
            return df_as_hold(df, "datos insuficientes")

        # Cálculo del MACD y su señal
        macd_line = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        df["macd"] = macd_line
        df["signal_line"] = signal_line

        # Cruces básicos
        df["cruce_alcista"] = (df["macd"] > df["signal_line"]) & (df["macd"].shift(1) <= df["signal_line"].shift(1))
        df["cruce_bajista"] = (df["macd"] < df["signal_line"]) & (df["macd"].shift(1) >= df["signal_line"].shift(1))

        # Confirmación opcional (sostenido al siguiente día)
        if usar_confirmacion_cruce:
            df["cruce_alcista"] &= df["macd"].shift(-1) > df["signal_line"].shift(-1)
            df["cruce_bajista"] &= df["macd"].shift(-1) < df["signal_line"].shift(-1)

        # Filtro por volatilidad (ATR ratio)
        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["cruce_alcista"] &= df["vol_ok"]
            df["cruce_bajista"] &= df["vol_ok"]

        df["signal"] = "hold"
        df.loc[df["cruce_alcista"], "signal"] = "buy"
        df.loc[df["cruce_bajista"], "signal"] = "sell"
        df["estrategia"] = "macd_cruce_v2"

        logger.info(f"MACD señales: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "macd_cruce_v2"
    return df[["fecha", "signal", "estrategia"]]
