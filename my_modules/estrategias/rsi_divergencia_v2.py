"""
===========================================================================
 Estrategia: Divergencias RSI (v2)
===========================================================================

Descripción:
------------
Genera señales de reversión basadas en condiciones extremas del RSI
y comportamiento divergente del precio. Mejora la versión original
con filtros y parámetros adicionales.

Mejoras implementadas:
-----------------------
- Orden cronológico del DataFrame
- Validación mínima de longitud
- Parámetros ajustables: ventana RSI, niveles de sobrecompra/sobreventa
- Confirmación opcional de pendiente RSI (cambia dirección)
- Confirmación de rebote con dirección del cuerpo (close > open)
- Filtro opcional por volatilidad (ATR ratio)

Parámetros:
-----------
- window: int = 14
- sobreventa: int = 30
- sobrecompra: int = 70
- confirmar_direccion_rsi: bool = False
- confirmar_rebote_cuerpo: bool = False
- usar_filtro_volatilidad: bool = False

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("rsi_divergencia_v2")

def generar_senales(df: pd.DataFrame,
                    window: int = 14,
                    sobreventa: int = 30,
                    sobrecompra: int = 70,
                    confirmar_direccion_rsi: bool = False,
                    confirmar_rebote_cuerpo: bool = False,
                    usar_filtro_volatilidad: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "high", "low", "open"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < window + 1:
            return df_as_hold(df, "datos insuficientes")

        # RSI y extremos
        rsi = ta.momentum.RSIIndicator(df["close"], window=window).rsi()
        df["rsi"] = rsi
        df["min_rolling"] = df["close"].rolling(window).min()
        df["max_rolling"] = df["close"].rolling(window).max()

        df["buy_cond"] = (df["rsi"] < sobreventa) & (df["close"] > df["min_rolling"])
        df["sell_cond"] = (df["rsi"] > sobrecompra) & (df["close"] < df["max_rolling"])

        # Confirmar pendiente del RSI
        if confirmar_direccion_rsi:
            df["rsi_up"] = df["rsi"].diff() > 0
            df["rsi_down"] = df["rsi"].diff() < 0
            df["buy_cond"] &= df["rsi_up"]
            df["sell_cond"] &= df["rsi_down"]

        # Confirmar con vela
        if confirmar_rebote_cuerpo:
            df["buy_cond"] &= df["close"] > df["open"]
            df["sell_cond"] &= df["close"] < df["open"]

        # Filtro por volatilidad (opcional)
        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["buy_cond"] &= df["vol_ok"]
            df["sell_cond"] &= df["vol_ok"]

        # Señales
        df["signal"] = "hold"
        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"
        df["estrategia"] = "rsi_divergencia_v2"

        logger.info(f"Señales RSI div: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "rsi_divergencia_v2"
    return df[["fecha", "signal", "estrategia"]]
