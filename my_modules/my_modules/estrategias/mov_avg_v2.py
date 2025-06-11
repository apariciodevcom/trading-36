"""
===========================================================================
 Estrategia: Cruce de Medias Móviles Simples (SMA 5 vs SMA 20) - v2
===========================================================================

Descripción:
------------
Genera señales de compra cuando SMA rápida (5) cruza hacia arriba a SMA
lenta (20) y de venta cuando cruza hacia abajo. Versión mejorada con
filtros y validaciones adicionales.

Mejoras implementadas:
-----------------------
- Ordenamiento temporal por fecha
- Validación de longitud mínima
- Confirmación opcional al día siguiente
- Filtro opcional de volatilidad basada en ATR
- Parámetros ajustables

Parámetros:
-----------
- confirmar_al_dia_siguiente: bool = False
- usar_filtro_volatilidad: bool = False

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("mov_avg_v2")

def generar_senales(df: pd.DataFrame,
                    confirmar_al_dia_siguiente: bool = False,
                    usar_filtro_volatilidad: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "high", "low"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)

        if len(df) < 21:
            return df_as_hold(df, "datos insuficientes")

        # Calcular medias móviles
        df["sma_5"] = df["close"].rolling(5).mean()
        df["sma_20"] = df["close"].rolling(20).mean()

        # Cruces
        df["cruce_alcista"] = (df["sma_5"] > df["sma_20"]) & (df["sma_5"].shift(1) <= df["sma_20"].shift(1))
        df["cruce_bajista"] = (df["sma_5"] < df["sma_20"]) & (df["sma_5"].shift(1) >= df["sma_20"].shift(1))

        if confirmar_al_dia_siguiente:
            df["cruce_alcista"] &= df["sma_5"].shift(-1) > df["sma_20"].shift(-1)
            df["cruce_bajista"] &= df["sma_5"].shift(-1) < df["sma_20"].shift(-1)

        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["cruce_alcista"] &= df["vol_ok"]
            df["cruce_bajista"] &= df["vol_ok"]

        df["signal"] = "hold"
        df.loc[df["cruce_alcista"], "signal"] = "buy"
        df.loc[df["cruce_bajista"], "signal"] = "sell"
        df["estrategia"] = "mov_avg_v2"

        logger.info(f"Señales SMA: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")

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
    df["estrategia"] = "mov_avg_v2"
    return df[["fecha", "signal", "estrategia"]]
