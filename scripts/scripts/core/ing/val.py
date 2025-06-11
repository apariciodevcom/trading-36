# ruta: /home/ubuntu/tr/scripts/core/val.py

import os
import pandas as pd
from datetime import datetime
from pathlib import Path

BASE_PATH = "/home/ubuntu/tr/data/historic"
TIPOS_ESPERADOS = {
    "fecha": "object",
    "open": "float64",
    "high": "float64",
    "low": "float64",
    "close": "float64",
    "volume": "int64"
}

errores = []
total_archivos = 0
rangos_fechas = []

def validar_archivo(parquet_path):
    global total_archivos
    simbolo = parquet_path.stem
    total_archivos += 1
    print(f"\n=== Validando {simbolo} ===")
    try:
        df = pd.read_parquet(parquet_path)

        print(f"Columnas: {list(df.columns)}")

        errores_tipo = []
        for col, tipo in TIPOS_ESPERADOS.items():
            if col not in df.columns:
                errores_tipo.append(f"FALTA {col}")
            elif df[col].dtype != tipo:
                errores_tipo.append(f"{col} tipo invalido: {df[col].dtype} (esperado {tipo})")

        if errores_tipo:
            print("ERRORES de tipo o columnas:", errores_tipo)
            errores.append((simbolo, errores_tipo))
        else:
            print("Tipos de datos OK")

        if "fecha" in df.columns:
            df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
            df = df.dropna(subset=["fecha"])
            df = df.sort_values("fecha").reset_index(drop=True)
            min_f, max_f = df["fecha"].min().date(), df["fecha"].max().date()
            rangos_fechas.append((simbolo, min_f, max_f))
            print(f"Fechas ordenadas. Rango: {min_f} a {max_f}")
        else:
            print("No se puede ordenar: falta columna 'fecha'")
            errores.append((simbolo, ["sin columna 'fecha'"]))
            return

        df.to_parquet(parquet_path, index=False)
        print(f"{simbolo} actualizado correctamente.")

    except Exception as e:
        errores.append((simbolo, [str(e)]))
        print(f"ERROR procesando {simbolo}: {e}")

def main():
    archivos = sorted(Path(BASE_PATH).glob("*.parquet"))
    print(f"Total archivos encontrados: {len(archivos)}")
    for f in archivos:
        validar_archivo(f)

    print("\n=== RESUMEN FINAL ===")
    print(f"Archivos analizados: {total_archivos}")
    print(f"Errores encontrados: {len(errores)}")
    if errores:
        print("Detalle de errores:")
        for simb, err in errores:
            print(f"  - {simb}: {err}")
    print(f"Rangos de fechas por simbolo:")
    for simb, start, end in rangos_fechas:
        print(f"  - {simb}: {start} a {end}")

if __name__ == "__main__":
    main()
