"""
===========================================================================
 Estrategia: Soporte y Resistencia - v2
===========================================================================

Descripción:
------------
Genera señales cuando el precio rompe niveles de soporte o resistencia
definidos por los extremos de los últimos N días. Esta versión incluye
confirmaciones adicionales y filtros de robustez.

Mejoras implementadas:
-----------------------
- Ordenamiento por fecha
- Validación de longitud mínima
- Parámetro configurable para ventana de soporte/resistencia
- Filtro por porcentaje mínimo de ruptura
- Filtro opcional por volatilidad (ATR ratio)
- Filtro opcional por cuerpo de vela (confirmación técnica)

Parámetros:
-----------
- window: int = 10
- ruptura_pct_min: float = 0.01 (1%)
- usar_filtro_volatilidad: bool = False
- usar_filtro_cuerpo: bool = False

Salida:
-------
['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("soporte_resistencia_v2")

def generar_senales(df: pd.DataFrame,
                    window: int = 10,
                    ruptura_pct_min: float = 0.01,
                    usar_filtro_volatilidad: bool = False,
                    usar_filtro_cuerpo: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req_cols = {"fecha", "close", "high", "low", "open"}
        if not req_cols.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req_cols - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < window + 1:
            return df_as_hold(df, "datos insuficientes")

        # Cálculo de soporte y resistencia con shift para evitar lookahead
        df["soporte"] = df["low"].rolling(window).min().shift(1)
        df["resistencia"] = df["high"].rolling(window).max().shift(1)

        # Cálculo de ruptura relativa
        df["break_res"] = (df["close"] - df["resistencia"]) / df["resistencia"]
        df["break_sup"] = (df["soporte"] - df["close"]) / df["soporte"]

        df["buy_cond"] = (df["close"] > df["resistencia"]) & (df["break_res"] > ruptura_pct_min)
        df["sell_cond"] = (df["close"] < df["soporte"]) & (df["break_sup"] > ruptura_pct_min)

        # Filtro por volatilidad
        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["buy_cond"] &= df["vol_ok"]
            df["sell_cond"] &= df["vol_ok"]

        # Filtro por cuerpo de vela
        if usar_filtro_cuerpo:
            df["rango_cuerpo"] = (df["close"] - df["open"]).abs()
            df["cuerpo_prom"] = df["rango_cuerpo"].rolling(window).mean()
            df["cuerpo_ok"] = df["rango_cuerpo"] > df["cuerpo_prom"]
            df["buy_cond"] &= df["cuerpo_ok"]
            df["sell_cond"] &= df["cuerpo_ok"]

        # Generar señales
        df["signal"] = "hold"
        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"
        df["estrategia"] = "soporte_resistencia_v2"

        logger.info(f"Señales generadas: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "soporte_resistencia_v2"
    return df[["fecha", "signal", "estrategia"]]
