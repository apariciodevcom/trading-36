"""
===========================================================================
 Estrategia: Cruce de Medias Móviles SMA10 vs SMA50 - v2
===========================================================================

Descripción:
------------
Detecta cruces de la SMA10 sobre o bajo la SMA50 como señales de compra
o venta. Versión mejorada con filtros configurables y validaciones robustas.

Mejoras implementadas:
-----------------------
- Orden cronológico de datos
- Validación mínima de longitud
- Parámetros configurables para ventanas móviles
- Confirmación opcional del cruce al día siguiente
- Filtro opcional por volatilidad (ATR)
- Filtro opcional por estructura de vela (cuerpo)

Parámetros:
-----------
- window_corto: int = 10
- window_largo: int = 50
- confirmar_al_dia_siguiente: bool = False
- usar_filtro_volatilidad: bool = False
- confirmar_cuerpo_vela: bool = False

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("sma_10_50_cruce_v2")

def generar_senales(df: pd.DataFrame,
                    window_corto: int = 10,
                    window_largo: int = 50,
                    confirmar_al_dia_siguiente: bool = False,
                    usar_filtro_volatilidad: bool = False,
                    confirmar_cuerpo_vela: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "high", "low", "open"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < window_largo + 1:
            return df_as_hold(df, "datos insuficientes")

        # Cálculo de medias
        df["sma_c"] = df["close"].rolling(window_corto).mean()
        df["sma_l"] = df["close"].rolling(window_largo).mean()

        # Cruces
        df["cruce_alcista"] = (df["sma_c"] > df["sma_l"]) & (df["sma_c"].shift(1) <= df["sma_l"].shift(1))
        df["cruce_bajista"] = (df["sma_c"] < df["sma_l"]) & (df["sma_c"].shift(1) >= df["sma_l"].shift(1))

        if confirmar_al_dia_siguiente:
            df["cruce_alcista"] &= df["sma_c"].shift(-1) > df["sma_l"].shift(-1)
            df["cruce_bajista"] &= df["sma_c"].shift(-1) < df["sma_l"].shift(-1)

        if confirmar_cuerpo_vela:
            df["cruce_alcista"] &= df["close"] > df["open"]
            df["cruce_bajista"] &= df["close"] < df["open"]

        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["cruce_alcista"] &= df["vol_ok"]
            df["cruce_bajista"] &= df["vol_ok"]

        # Generar señales
        df["signal"] = "hold"
        df.loc[df["cruce_alcista"], "signal"] = "buy"
        df.loc[df["cruce_bajista"], "signal"] = "sell"
        df["estrategia"] = "sma_10_50_cruce_v2"

        logger.info(f"Señales SMA10/50: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "sma_10_50_cruce_v2"
    return df[["fecha", "signal", "estrategia"]]
