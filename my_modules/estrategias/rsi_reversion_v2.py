"""
===========================================================================
 Estrategia: Reversión basada en RSI - v2
===========================================================================

Descripción:
------------
Genera señales de reversión técnica cuando el RSI se encuentra en zonas
extremas (sobreventa o sobrecompra). Mejora la versión original con
parámetros configurables y filtros de confirmación opcionales.

Mejoras implementadas:
-----------------------
- Orden cronológico garantizado
- Validación de longitud mínima
- Parámetros configurables: ventana RSI, niveles de sobrecompra/sobreventa
- Confirmación por pendiente del RSI (rebote real)
- Filtro por tipo de vela (`close > open`)
- Filtro por volatilidad (ATR ratio)

Parámetros:
-----------
- window: int = 14
- umbral_bajo: int = 30
- umbral_alto: int = 70
- confirmar_rebote_rsi: bool = False
- confirmar_estructura_vela: bool = False
- usar_filtro_volatilidad: bool = False

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("rsi_reversion_v2")

def generar_senales(df: pd.DataFrame,
                    window: int = 14,
                    umbral_bajo: int = 30,
                    umbral_alto: int = 70,
                    confirmar_rebote_rsi: bool = False,
                    confirmar_estructura_vela: bool = False,
                    usar_filtro_volatilidad: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "open", "high", "low"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < window + 1:
            return df_as_hold(df, "datos insuficientes")

        # Calcular RSI
        rsi = ta.momentum.RSIIndicator(df["close"], window=window).rsi()
        df["rsi"] = rsi

        # Señales base por extremos
        df["buy_cond"] = df["rsi"] < umbral_bajo
        df["sell_cond"] = df["rsi"] > umbral_alto

        # Confirmar rebote en RSI
        if confirmar_rebote_rsi:
            df["rsi_up"] = df["rsi"].diff() > 0
            df["rsi_down"] = df["rsi"].diff() < 0
            df["buy_cond"] &= df["rsi_up"]
            df["sell_cond"] &= df["rsi_down"]

        # Confirmar estructura de vela
        if confirmar_estructura_vela:
            df["buy_cond"] &= df["close"] > df["open"]
            df["sell_cond"] &= df["close"] < df["open"]

        # Filtro por volatilidad
        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["buy_cond"] &= df["vol_ok"]
            df["sell_cond"] &= df["vol_ok"]

        # Generar señales finales
        df["signal"] = "hold"
        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"
        df["estrategia"] = "rsi_reversion_v2"

        logger.info(f"RSI señales: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "rsi_reversion_v2"
    return df[["fecha", "signal", "estrategia"]]
