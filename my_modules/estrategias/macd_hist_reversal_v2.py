"""
===========================================================================
 Estrategia: Reversión por Histograma de MACD - v2
===========================================================================

Descripción:
------------
Genera señales cuando el histograma del MACD cruza de negativo a positivo
o viceversa, con pendiente creciente o decreciente respectivamente. Mejora
la versión original filtrando señales débiles o ruidosas.

Mejoras implementadas:
-----------------------
- Orden cronológico asegurado
- Validación mínima de longitud
- Parámetro `min_diff` para ignorar fluctuaciones menores
- Confirmación opcional en la siguiente vela
- Filtro opcional de volatilidad (ATR ratio)

Parámetros:
-----------
- min_diff: float = 0.001
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

logger = configurar_logger("macd_hist_reversal_v2")

def generar_senales(df: pd.DataFrame,
                    min_diff: float = 0.001,
                    confirmar_al_dia_siguiente: bool = False,
                    usar_filtro_volatilidad: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req_cols = {"fecha", "close", "high", "low"}
        if not req_cols.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req_cols - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < 35:
            return df_as_hold(df, "datos insuficientes")

        # Calcular MACD y señal
        macd = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
        signal = macd.ewm(span=9, adjust=False).mean()
        df["macd_hist"] = macd - signal

        # Calcular pendiente y aplicar umbral mínimo
        df["hist_diff"] = df["macd_hist"].diff()
        df["hist_valido"] = df["hist_diff"].abs() > min_diff

        df["buy_cond"] = (df["macd_hist"] > 0) & (df["hist_diff"] > 0) & df["hist_valido"]
        df["sell_cond"] = (df["macd_hist"] < 0) & (df["hist_diff"] < 0) & df["hist_valido"]

        if confirmar_al_dia_siguiente:
            df["buy_cond"] &= df["macd_hist"].shift(-1) > df["macd_hist"]
            df["sell_cond"] &= df["macd_hist"].shift(-1) < df["macd_hist"]

        if usar_filtro_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["vol_ok"] = df["atr_ratio"] > 0.008
            df["buy_cond"] &= df["vol_ok"]
            df["sell_cond"] &= df["vol_ok"]

        df["signal"] = "hold"
        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"
        df["estrategia"] = "macd_hist_reversal_v2"

        logger.info(f"MACD-H señales: buy={sum(df['signal']=='buy')}, sell={sum(df['signal']=='sell')}, total={len(df)}")
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
    df["estrategia"] = "macd_hist_reversal_v2"
    return df[["fecha", "signal", "estrategia"]]
