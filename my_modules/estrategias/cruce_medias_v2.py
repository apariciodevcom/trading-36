"""
===========================================================================
 Estrategia: Cruce de Medias Móviles (EMA10 vs EMA30) - v3 (configurable)
===========================================================================

Descripción:
------------
Estrategia de cruce de medias móviles con parámetros configurables:
- buy: cruce alcista EMA10 > EMA30
- sell: cruce bajista EMA10 < EMA30
- Filtros opcionales: volatilidad mínima, confirmación en cierre siguiente, dirección de tendencia

Parámetros:
-----------
- usar_filtro_volatilidad (default=True): descarta señales con ATR_ratio < 0.01
- confirmar_al_dia_siguiente (default=False): aplica señal solo si cruce se mantiene al cierre siguiente
- usar_sesgo_tendencial (default=False): activa filtro por EMA200 para tomar señales solo a favor de la tendencia

Salida:
-------
['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("cruce_medias_v3")

def generar_senales(df: pd.DataFrame,
                    usar_filtro_volatilidad: bool = True,
                    confirmar_al_dia_siguiente: bool = False,
                    usar_sesgo_tendencial: bool = True) -> pd.DataFrame:
    try:
        df = df.copy()
        req_cols = {"fecha", "close", "high", "low"}
        if not req_cols.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req_cols - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < 35:
            return df_as_hold(df, "datos insuficientes")

        # EMAs principales
        df["ema_10"] = df["close"].ewm(span=10, adjust=False).mean()
        df["ema_30"] = df["close"].ewm(span=30, adjust=False).mean()

        # Cruces iniciales
        df["cruce_alcista"] = df["ema_10"] > df["ema_30"]
        df["cruce_bajista"] = df["ema_10"] < df["ema_30"]
        
        if confirmar_al_dia_siguiente:
            df["cruce_alcista"] &= df["ema_10"].shift(-1) > df["ema_30"].shift(-1)
            df["cruce_bajista"] &= df["ema_10"].shift(-1) < df["ema_30"].shift(-1)

        # Filtro de tendencia (EMA200)
        if usar_sesgo_tendencial:
            df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean()
            df["cruce_alcista"] &= df["close"] > df["ema_200"]
            df["cruce_bajista"] &= df["close"] < df["ema_200"]

        # Filtro de volatilidad
        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.01
            df["cruce_alcista"] &= df["vol_ok"]
            df["cruce_bajista"] &= df["vol_ok"]

        # Aplicar señales
        df["signal"] = "hold"
        df.loc[df["cruce_alcista"], "signal"] = "buy"
        df.loc[df["cruce_bajista"], "signal"] = "sell"
        df["estrategia"] = "cruce_medias_v2"

        logger.info(f"Señales generadas: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")

        return df[["fecha", "signal", "estrategia"]]

    except Exception as e:
        logger.error(f"Error en cruce_medias_v3: {str(e)}")
        return df_as_hold(df, "exception")


def df_as_hold(df: pd.DataFrame, razon: str) -> pd.DataFrame:
    logger.info(f"Retornando HOLD por: {razon}")
    df = df.copy()
    if "fecha" not in df.columns:
        return pd.DataFrame(columns=["fecha", "signal", "estrategia"])
    df["signal"] = "hold"
    df["estrategia"] = "cruce_medias_v3"
    return df[["fecha", "signal", "estrategia"]]
