import os
import pandas as pd
from datetime import datetime, timedelta

# === CONFIGURACION ===
HOY = datetime.now().strftime("%Y-%m-%d")
ARCHIVO_SENALES = f"/home/ubuntu/tr/reports/senales_heuristicas/diarias/{HOY}.csv"
CARPETA_HIST = "/home/ubuntu/tr/data/historic_reciente"
ARCHIVO_SALIDA = "/home/ubuntu/tr/reports/ordenes/ordenes_diarias_totales.csv"
LOG = f"/home/ubuntu/tr/logs/utils/gen_ordenes_dia_{HOY}.log"

TP = 0.03
SL = -0.01
MAX_DIAS = 10

# === FUNCIONES ===
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG, "a") as f:
        f.write(linea + "\n")

def procesar_ordenes(df_senales, simbolo):
    try:
        df_precio = pd.read_parquet(f"{CARPETA_HIST}/{simbolo}.parquet")
        df_precio["fecha"] = pd.to_datetime(df_precio["fecha"])
        df_precio = df_precio.sort_values("fecha").reset_index(drop=True)

        df_simbolo = df_senales[df_senales["simbolo"] == simbolo]
        df_simbolo = df_simbolo[df_simbolo["signal"].isin(["buy", "sell"])]

        ordenes = []

        for _, fila in df_simbolo.iterrows():
            fecha = pd.to_datetime(fila["fecha"])
            estrategia = fila["estrategia"]
            senal = fila["signal"]

            if fecha not in df_precio["fecha"].values:
                continue

            idx = df_precio[df_precio["fecha"] == fecha].index[0]
            if idx + 1 >= len(df_precio):
                continue  # no hay dia siguiente

            precio_entrada = df_precio.loc[idx + 1, "close"]
            fecha_entrada = df_precio.loc[idx + 1, "fecha"]
            df_sub = df_precio.iloc[idx + 2 : idx + 2 + MAX_DIAS]

            for _, r in df_sub.iterrows():
                precio_actual = r["close"]
                fecha_salida = r["fecha"]
                dias = (fecha_salida - fecha_entrada).days
                cambio = (precio_actual - precio_entrada) / precio_entrada
                if senal == "sell":
                    cambio = -cambio

                if cambio >= TP or cambio <= SL or fecha_salida == df_sub["fecha"].iloc[-1]:
                    ordenes.append({
                        "simbolo": simbolo,
                        "fecha_entrada": fecha_entrada.date(),
                        "fecha_salida": fecha_salida.date(),
                        "senal": senal,
                        "estrategia": estrategia,
                        "resultado": round(cambio, 4),
                        "dias": dias
                    })
                    break

        return ordenes

    except Exception as e:
        log(f"{simbolo} ERROR: {e}")
        return []

# === MAIN ===
def main():
    os.makedirs(os.path.dirname(LOG), exist_ok=True)

    if not os.path.exists(ARCHIVO_SENALES):
        log(f"ERROR: archivo de señales no encontrado: {ARCHIVO_SENALES}")
        return

    df_senales = pd.read_csv(ARCHIVO_SENALES)
    if "signal" in df_senales.columns:
        df_senales.rename(columns={"signal": "senal"}, inplace=True)

    ordenes_totales = []

    for simbolo in df_senales["simbolo"].unique():
        ordenes = procesar_ordenes(df_senales, simbolo)
        if ordenes:
            ordenes_totales.extend(ordenes)
            log(f"OK {simbolo}: {len(ordenes)} ordenes")

    if ordenes_totales:
        df_out = pd.DataFrame(ordenes_totales)
        if os.path.exists(ARCHIVO_SALIDA):
            df_existente = pd.read_csv(ARCHIVO_SALIDA)
            df_final = pd.concat([df_existente, df_out], ignore_index=True)
        else:
            df_final = df_out
        df_final.to_csv(ARCHIVO_SALIDA, index=False)
        log(f"Archivo actualizado: {ARCHIVO_SALIDA} ({len(df_out)} nuevas ordenes)")
    else:
        log("No se generaron ordenes.")

if __name__ == "__main__":
    main()
