"""
===========================================================================
 Estrategia: Cruce de Medias Móviles EMA 9 y 21 - v2
===========================================================================

Descripción:
------------
Estrategia mejorada basada en cruce de medias exponenciales:
- Señal de compra si EMA9 > EMA21 y persiste al menos 2 días
- Señal de venta si EMA9 < EMA21 y persiste al menos 2 días
- Opción de filtrar señales si no hay suficiente volatilidad

Mejoras:
--------
- Ordenamiento cronológico del DataFrame
- Validación mínima de tamaño de muestra
- Confirmación de cruce con duración mínima
- Filtro de volatilidad por ATR_ratio
- Logging detallado de señales

Parámetros:
-----------
- usar_filtro_volatilidad: bool (default=True)

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("ema_9_21_cruce_v2")

def generar_senales(df: pd.DataFrame, usar_filtro_volatilidad: bool = True) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "high", "low"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)

        if len(df) < 30:
            return df_as_hold(df, "datos insuficientes")

        # Calcular EMAs
        df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
        df["ema_21"] = df["close"].ewm(span=21, adjust=False).mean()

        # Confirmación de cruce que dura al menos 2 días consecutivos
        df["ema_up"] = (df["ema_9"] > df["ema_21"])
        df["ema_down"] = (df["ema_9"] < df["ema_21"])
        df["ema_up_2d"] = df["ema_up"] & df["ema_up"].shift(1)
        df["ema_down_2d"] = df["ema_down"] & df["ema_down"].shift(1)

        # Filtro por volatilidad
        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["ema_up_2d"] &= df["vol_ok"]
            df["ema_down_2d"] &= df["vol_ok"]

        # Asignar señales
        df["signal"] = "hold"
        df.loc[df["ema_up_2d"], "signal"] = "buy"
        df.loc[df["ema_down_2d"], "signal"] = "sell"
        df["estrategia"] = "ema_9_21_cruce_v2"

        logger.info(f"Señales generadas: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
        return df[["fecha", "signal", "estrategia"]]

    except Exception as e:
        logger.error(f"Error en ema_9_21_cruce_v2: {str(e)}")
        return df_as_hold(df, "exception")

def df_as_hold(df: pd.DataFrame, razon: str) -> pd.DataFrame:
    logger.info(f"Retornando HOLD por: {razon}")
    df = df.copy()
    if "fecha" not in df.columns:
        return pd.DataFrame(columns=["fecha", "signal", "estrategia"])
    df["signal"] = "hold"
    df["estrategia"] = "ema_9_21_cruce_v2"
    return df[["fecha", "signal", "estrategia"]]
