"""
===========================================================================
 Estrategia: Gap de Apertura - v2
===========================================================================

Descripción:
------------
Estrategia que detecta gaps de apertura significativos entre el cierre
del día anterior y la apertura actual. Se generan señales de compra o
venta si el gap excede ciertos umbrales.

Mejoras implementadas:
-----------------------
- Ordenamiento por fecha
- Validación mínima de longitud
- Parámetros configurables de umbral y gap mínimo
- Opción de confirmar con dirección del cuerpo de la vela (open < close)
- Señal 'hold' si el gap es insignificante

Parámetros:
-----------
- umbral_gap: float (porcentaje de gap, ej: 0.03 para 3%)
- usar_confirmacion_cuerpo: bool (requiere confirmación con vela alcista/bajista)

Salida:
-------
['fecha', 'signal', 'estrategia']

===========================================================================
"""

import pandas as pd
from my_modules.logger_estrategia import configurar_logger

logger = configurar_logger("gap_open_strategy_v2")

def generar_senales(df: pd.DataFrame,
                    umbral_gap: float = 0.03,
                    usar_confirmacion_cuerpo: bool = False) -> pd.DataFrame:
    try:
        df = df.copy()
        req = {"fecha", "close", "open"}
        if not req.issubset(df.columns):
            logger.warning(f"Columnas faltantes: {req - set(df.columns)}")
            return df_as_hold(df, "faltan columnas")

        df = df.sort_values("fecha").reset_index(drop=True)
        if len(df) < 3:
            return df_as_hold(df, "datos insuficientes")

        df["prev_close"] = df["close"].shift(1)
        df["gap_pct"] = (df["open"] - df["prev_close"]) / df["prev_close"]
        df["gap_abs"] = df["gap_pct"].abs()

        df["signal"] = "hold"

        df["gap_up"] = df["gap_pct"] > umbral_gap
        df["gap_down"] = df["gap_pct"] < -umbral_gap

        if usar_confirmacion_cuerpo:
            df["vela_alcista"] = df["close"] > df["open"]
            df["vela_bajista"] = df["close"] < df["open"]
            df["buy_cond"] = df["gap_up"] & df["vela_alcista"]
            df["sell_cond"] = df["gap_down"] & df["vela_bajista"]
        else:
            df["buy_cond"] = df["gap_up"]
            df["sell_cond"] = df["gap_down"]

        df.loc[df["buy_cond"], "signal"] = "buy"
        df.loc[df["sell_cond"], "signal"] = "sell"

        df["estrategia"] = "gap_open_strategy_v2"
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
    df["estrategia"] = "gap_open_strategy_v2"
    return df[["fecha", "signal", "estrategia"]]
