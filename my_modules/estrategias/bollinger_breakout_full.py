"""
===========================================================================
 Estrategia: Bollinger Breakout Avanzada (con filtros de confirmación)
===========================================================================

Descripcion:
------------
Detecta rupturas sobre/bajo bandas de Bollinger (MA ± s*STD) y aplica 
filtros opcionales para confirmar señales: volatilidad (ATR ratio), 
volumen relativo, y rango de vela.

Parametros:
-----------
- s: desviaciones estándar (default=2.0)
- ajuste_volatilidad: bool (usar ATR para ajustar s)
- usar_atr_ratio: bool (filtra señales por volatilidad relativa)
- usar_volumen: bool (exige volumen > promedio 20 días)
- usar_rango_vela: bool (solo señales si cuerpo > promedio)

Columnas requeridas:
---------------------
- 'fecha', 'close', 'high', 'low', 'open', 'volume'

Salida:
-------
DataFrame con columnas: ['fecha', 'signal', 'estrategia']

=========================================================================== 
"""

import pandas as pd
from my_modules.logger_estrategia import configurar_logger
import ta

logger = configurar_logger("bollinger_breakout_full")

def generar_senales(df: pd.DataFrame, 
                    s: float = 2.0, 
                    ajuste_volatilidad: bool = False,
                    usar_atr_ratio: bool = False,
                    usar_volumen: bool = False,
                    usar_rango_vela: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req_cols = {"fecha", "close", "high", "low", "open", "volume"}
        if not req_cols.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req_cols - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < 30:
            return df_as_hold(df, "datos insuficientes")

        df["ma20"] = df["close"].rolling(20).mean()
        df["std"] = df["close"].rolling(20).std()

        # s fijo o dinamico
        if ajuste_volatilidad:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            vol_rel = (df["atr"] / df["close"]).clip(0, 0.1)
            s_dyn = (s - 0.5) + vol_rel * 20
            df["upper"] = df["ma20"] + s_dyn * df["std"]
            df["lower"] = df["ma20"] - s_dyn * df["std"]
        else:
            df["upper"] = df["ma20"] + s * df["std"]
            df["lower"] = df["ma20"] - s * df["std"]

        # Señales iniciales
        df["signal"] = "hold"
        df["buy_cond"] = df["close"] > df["upper"]
        df["sell_cond"] = df["close"] < df["lower"]

        # Filtros opcionales
        if usar_atr_ratio:
            df["atr"] = ta.volatility.average_true_range(df["high"], df["low"], df["close"], window=14)
            df["atr_ratio"] = df["atr"] / df["close"]
            df["buy_cond"] &= df["atr_ratio"] > 0.01
            df["sell_cond"] &= df["atr_ratio"] > 0.01

        if usar_volumen:
            df["vol_sma"] = df["volume"].rolling(20).mean()
            df["buy_cond"] &= df["volume"] > df["vol_sma"]
            df["sell_cond"] &= df["volume"] > df["vol_sma"]

        if usar_rango_vela:
            df["rango"] = abs(df["close"] - df["open"])
            df["rango_avg"] = df["rango"].rolling(20).mean()
            df["buy_cond"] &= df["rango"] > df["rango_avg"]
            df["sell_cond"] &= df["rango"] > df["rango_avg"]

        # Aplicar condiciones
        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"
        df["estrategia"] = "bollinger_breakout_full"

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
    df["estrategia"] = "bollinger_breakout_full"
    return df[["fecha", "signal", "estrategia"]]
