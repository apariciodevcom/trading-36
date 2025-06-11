"""
===========================================================================
 Estrategia: ADX Filter Trend (versión mejorada) - LeanTech Trading
===========================================================================

Descripcion:
------------
Esta estrategia evalúa fuerza de tendencia usando el ADX real
y cruces sobre la media móvil simple de 20 días para detectar señales
de compra y venta. Se generan señales:

- BUY  → close > sma_20 y adx > 20
- SELL → close < sma_20 y adx > 20
- HOLD en otros casos

Columnas requeridas:
---------------------
- 'fecha', 'close', 'high', 'low'

Salida:
-------
DataFrame con columnas: ['fecha', 'signal', 'estrategia']

Notas:
------
- Calcula ADX real con 'ta.trend.adx'
- Ordena por 'fecha' antes de aplicar cálculos
- Siempre devuelve un DataFrame completo con señal por fila

=========================================================================== 
"""

import pandas as pd
from my_modules.logger_estrategia import configurar_logger
import ta

logger = configurar_logger("adx_filter_trend")

def generar_senales(df: pd.DataFrame) -> pd.DataFrame:
    try:
        df = df.copy()

        # Validacion de columnas requeridas
        columnas_necesarias = {"fecha", "close", "high", "low"}
        if not columnas_necesarias.issubset(df.columns):
            faltantes = columnas_necesarias - set(df.columns)
            logger.warning(f"Columnas faltantes: {faltantes}")
            return df_as_hold(df, estrategia="adx_filter_trend", razon="faltan columnas")

        # Ordenar por fecha ascendente
        df = df.sort_values("fecha").reset_index(drop=True)

        # Validar cantidad mínima
        if len(df) < 20:
            logger.warning("Datos insuficientes para aplicar ADX")
            return df_as_hold(df, estrategia="adx_filter_trend", razon="datos insuficientes")

        # Calculo ADX real
        df["adx"] = ta.trend.adx(df["high"], df["low"], df["close"], window=14)
        df["sma_20"] = df["close"].rolling(20).mean()

        # Señales
        df["signal"] = "hold"
        df.loc[(df["close"] > df["sma_20"]) & (df["adx"] > 20), "signal"] = "buy"
        df.loc[(df["close"] < df["sma_20"]) & (df["adx"] > 20), "signal"] = "sell"

        df["estrategia"] = "adx_filter_trend"

        logger.info(f"Señales: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
        return df[["fecha", "signal", "estrategia"]]

    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return df_as_hold(df, estrategia="adx_filter_trend", razon="exception")

def df_as_hold(df: pd.DataFrame, estrategia: str, razon: str) -> pd.DataFrame:
    logger.info(f"Retornando HOLD por: {razon}")
    df = df.copy()
    df["signal"] = "hold"
    df["estrategia"] = estrategia
    return df[["fecha", "signal", "estrategia"]] if "fecha" in df.columns else pd.DataFrame(columns=["fecha", "signal", "estrategia"])
