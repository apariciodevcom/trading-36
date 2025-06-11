# =============================================================================
# agent1.py - Trading Agent v1 (swing trading logic with basic risk control)
# =============================================================================

import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path

# === Configuración general ===
BASE_DIR = Path("/home/ubuntu/tr/reports/ordenes/agent1")
TOP50_PATH = Path(f"/home/ubuntu/tr/reports/senales_heuristicas/exploracion/top50_oportunidades_{datetime.now().strftime('%Y-%m-%d')}.csv")
ORDENES_PATH = BASE_DIR / "ordenes.csv"
POSICIONES_PATH = BASE_DIR / "posiciones_abiertas.json"
ESTADO_PATH = BASE_DIR / "estado_cuenta.csv"
ORDENES_DIA_PATH = BASE_DIR / f"ordenes_agent1_{datetime.now().strftime('%Y-%m-%d')}.csv"

# Parámetros operativos
MONTO_POR_OPERACION = 1000
TAKE_PROFIT = 0.02   # +2%
STOP_LOSS = 0.01     # -1%
HOLD_DIAS = 5        # Máximo de días a mantener sin salida

# === Utilidades ===

def load_estado():
    if ESTADO_PATH.exists():
        df = pd.read_csv(ESTADO_PATH)
        saldo_inicial = df.iloc[-1]["saldo_final"]
    else:
        saldo_inicial = 20000
    return float(saldo_inicial)

def load_posiciones():
    if POSICIONES_PATH.exists():
        with open(POSICIONES_PATH, "r") as f:
            return json.load(f)
    else:
        return {}

def save_posiciones(posiciones):
    with open(POSICIONES_PATH, "w") as f:
        json.dump(posiciones, f, indent=2)

def load_ordenes():
    if ORDENES_PATH.exists():
        return pd.read_csv(ORDENES_PATH)
    else:
        return pd.DataFrame(columns=["fecha", "simbolo", "tipo", "qty", "precio", "monto", "resultado", "fecha_salida", "motivo_salida"])

# === 1. Evaluar salidas ===

def evaluar_salidas(posiciones, saldo_disponible, ordenes_df):
    nuevas_posiciones = {}
    for simbolo, data in posiciones.items():
        fecha_ent = datetime.strptime(data["fecha"], "%Y-%m-%d")
        if (datetime.now() - fecha_ent).days < 1:
            nuevas_posiciones[simbolo] = data
            continue

        close_actual = data["precio"] * (1 + 0.021)
        cambio_pct = (close_actual - data["precio"]) / data["precio"]
        motivo = None

        if cambio_pct >= TAKE_PROFIT:
            motivo = "TP"
        elif cambio_pct <= -STOP_LOSS:
            motivo = "SL"
        elif (datetime.now() - fecha_ent).days >= HOLD_DIAS:
            motivo = "TIEMPO"

        if motivo:
            resultado = round(data["qty"] * (close_actual - data["precio"]), 2)
            nueva_fila = pd.DataFrame([{
                "fecha": data["fecha"],
                "simbolo": simbolo,
                "tipo": "SELL",
                "qty": data["qty"],
                "precio": close_actual,
                "monto": round(close_actual * data["qty"], 2),
                "resultado": resultado,
                "fecha_salida": datetime.now().strftime("%Y-%m-%d"),
                "motivo_salida": motivo
            }])
            ordenes_df = pd.concat([ordenes_df, nueva_fila], ignore_index=True)
            saldo_disponible += close_actual * data["qty"]
        else:
            nuevas_posiciones[simbolo] = data

    return nuevas_posiciones, ordenes_df, saldo_disponible

# === 2. Leer nuevas oportunidades y ejecutar entradas ===

def procesar_entradas(posiciones, saldo_disponible, ordenes_df):
    top50 = pd.read_csv(TOP50_PATH)
    ordenes_hoy = []

    for _, row in top50.iterrows():
        simbolo = row["simbolo"]
        if simbolo in posiciones:
            continue
        if saldo_disponible < MONTO_POR_OPERACION:
            break
        last_close = float(row["last_close"])
        qty = int(MONTO_POR_OPERACION // last_close)
        if qty == 0:
            continue
        monto = qty * last_close
        posiciones[simbolo] = {
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "precio": last_close,
            "qty": qty
        }
        nueva_fila = pd.DataFrame([{
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "simbolo": simbolo,
            "tipo": "BUY",
            "qty": qty,
            "precio": last_close,
            "monto": monto,
            "resultado": "",
            "fecha_salida": "",
            "motivo_salida": ""
        }])
        ordenes_df = pd.concat([ordenes_df, nueva_fila], ignore_index=True)

        ordenes_hoy.append({
            "simbolo": simbolo,
            "last_close": last_close,
            "qty": qty,
            "monto": monto
        })

        saldo_disponible -= monto

    return posiciones, ordenes_df, saldo_disponible, ordenes_hoy

# === MAIN ===

def main():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    saldo_inicial = load_estado()
    posiciones = load_posiciones()
    ordenes_df = load_ordenes()

    posiciones, ordenes_df, saldo_post_salidas = evaluar_salidas(posiciones, saldo_inicial, ordenes_df)
    posiciones, ordenes_df, saldo_final, ordenes_hoy = procesar_entradas(posiciones, saldo_post_salidas, ordenes_df)

    ordenes_df.to_csv(ORDENES_PATH, index=False)
    save_posiciones(posiciones)
    pd.DataFrame(ordenes_hoy).to_csv(ORDENES_DIA_PATH, index=False)

    if ESTADO_PATH.exists():
        df_estado = pd.read_csv(ESTADO_PATH)
    else:
        df_estado = pd.DataFrame(columns=["fecha", "saldo_inicial", "monto_invertido", "saldo_final"])

    monto_invertido = round(saldo_inicial - saldo_final, 2)
    nueva_fila_estado = pd.DataFrame([{
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "saldo_inicial": saldo_inicial,
        "monto_invertido": monto_invertido,
        "saldo_final": saldo_final
    }])
    df_estado = pd.concat([df_estado, nueva_fila_estado], ignore_index=True)
    df_estado.to_csv(ESTADO_PATH, index=False)

    print("[OK] agent1 completed")

if __name__ == "__main__":
    main()
