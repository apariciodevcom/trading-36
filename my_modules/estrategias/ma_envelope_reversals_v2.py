"""
===========================================================================
 Estrategia: Reversiones por Envolvente de Media Móvil - v2
===========================================================================

Descripción:
------------
Genera señales de reversión cuando el precio se sale de un canal formado
por una media móvil y un margen porcentual configurable.

Mejoras implementadas:
-----------------------
- Orden temporal del DataFrame
- Validación mínima de tamaño
- Parámetros configurables: periodo MA, ancho del canal (en %)
- Confirmación opcional: reversión al alza/baja
- Filtro opcional de volatilidad (ATR ratio)

Parámetros:
-----------
- periodo_ma: int = 20
- margen_pct: float = 0.03
- usar_confirmacion_rebote: bool = False
- usar_filtro_volatilidad: bool = False

Salida:
-------
DataFrame con ['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
import ta
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("ma_envelope_reversals_v2")

def generar_senales(df: pd.DataFrame,
                    periodo_ma: int = 20,
                    margen_pct: float = 0.03,
                    usar_confirmacion_rebote: bool = False,
                    usar_filtro_volatilidad: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "high", "low"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)

        if len(df) < periodo_ma + 1:
            return df_as_hold(df, "datos insuficientes")

        # Media móvil y canal
        df["ma"] = df["close"].rolling(periodo_ma).mean()
        df["upper"] = df["ma"] * (1 + margen_pct)
        df["lower"] = df["ma"] * (1 - margen_pct)

        df["buy_cond"] = df["close"] < df["lower"]
        df["sell_cond"] = df["close"] > df["upper"]

        # Confirmación por rebote al día siguiente
        if usar_confirmacion_rebote:
            df["buy_cond"] &= df["close"].shift(-1) > df["close"]
            df["sell_cond"] &= df["close"].shift(-1) < df["close"]

        # Filtro por volatilidad
        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["buy_cond"] &= df["vol_ok"]
            df["sell_cond"] &= df["vol_ok"]

        df["signal"] = "hold"
        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"
        df["estrategia"] = "ma_envelope_reversals_v2"

        logger.info(f"Señales: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "ma_envelope_reversals_v2"
    return df[["fecha", "signal", "estrategia"]]
