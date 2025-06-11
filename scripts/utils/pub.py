import os
import boto3
import pandas as pd
from datetime import datetime
from pathlib import Path

# === CONFIGURACION ===
PROFILE = "ses-trading"
BUCKET_NAME = "apariciodevcom"
S3_KEY = "trading/datos.html"
LOCAL_DIR = "/home/ubuntu/tr/data/historic_reciente"
LOG_FILE = f"/home/ubuntu/tr/logs/utils/pub_{datetime.now().date()}.log"

session = boto3.Session(profile_name=PROFILE)
s3 = session.client("s3")

# === LOG ===
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    linea = f"{ts} | {msg}"
    print(linea)
    with open(LOG_FILE, "a") as f:
        f.write(linea + "\n")

# === FORMATO NUMEROS ===
def formatear_millones(valor):
    try:
        return f"{valor / 1_000_000:.2f}M"
    except:
        return "ND"

def span_color(valor, tipo="numero"):
    try:
        val = float(str(valor).replace('%', ''))
        color = "green" if val > 0 else "red" if val < 0 else "black"
        sufijo = "%" if tipo == "porcentaje" else ""
        simbolo = "+" if val > 0 and tipo == "porcentaje" else ""
        return f'<span style="color:{color}">{simbolo}{val:.2f}{sufijo}</span>'
    except:
        return "ND"

def detectar_tendencia(close_series):
    if len(close_series) < 4:
        return "ND"
    a = close_series.iloc[-4]
    b = close_series.iloc[-1]
    if abs(a - b) < 0.2:
        return "→"
    return "↑" if b > a else "↓"

# === PROCESAR DATOS ===
def procesar_archivos():
    archivos = sorted(Path(LOCAL_DIR).glob("*.parquet"))
    filas = []

    for archivo in archivos:
        simbolo = archivo.stem.upper()
        try:
            df = pd.read_parquet(archivo)
            df = df[df["fecha"].notna()]
            df["fecha"] = pd.to_datetime(df["fecha"])
            df = df.sort_values("fecha")
            df = df[df["close"] > 1]
            df = df[df["volume"] > 0]

            if len(df) < 4:
                continue

            ultima = df.iloc[-1]
            penultima = df.iloc[-2]
            prom_vol = df["volume"].tail(20).mean()
            cambio_dia = (ultima["close"] - penultima["close"]) / penultima["close"] * 100

            filas.append({
                "simbolo": simbolo,
                "fecha": ultima["fecha"].date(),
                "open": round(ultima["open"], 2),
                "high": round(ultima["high"], 2),
                "low": round(ultima["low"], 2),
                "close": span_color(ultima["close"], tipo="numero"),
                "volume": formatear_millones(ultima["volume"]),
                "cambio_dia": span_color(cambio_dia, tipo="porcentaje"),
                "promedio_volumen": formatear_millones(prom_vol),
                "tendencia_3d": detectar_tendencia(df["close"])
            })

        except Exception as e:
            log(f"ERROR {simbolo}: {e}")

    return pd.DataFrame(filas)

# === HTML ===
def generar_html(df):
    hoy = datetime.now().strftime("%Y-%m-%d")
    tabla = df.sort_values("simbolo").to_html(index=False, escape=False, border=0, classes="tabla")
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Datos OHLCV - {hoy}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1 {{ color: #333; }}
            table.tabla {{ border-collapse: collapse; width: 100%; }}
            table.tabla th, td {{ border: 1px solid #999; padding: 8px; text-align: center; }}
            table.tabla th {{ background-color: #eee; }}
        </style>
    </head>
    <body>
        <h1>Datos OHLCV del {hoy}</h1>
        {tabla}
    </body>
    </html>
    """
    return html

# === SUBIDA A S3 ===
def subir_html(html_content):
    try:
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=S3_KEY,
            Body=html_content,
            ContentType="text/html"
        )
        log(f"Archivo HTML subido correctamente a s3://{BUCKET_NAME}/{S3_KEY}")
    except Exception as e:
        log(f"ERROR al subir a S3: {e}")

# === MAIN ===
def main():
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    df = procesar_archivos()
    if df.empty:
        log("No se encontraron datos validos para generar HTML.")
        return
    html = generar_html(df)
    subir_html(html)

if __name__ == "__main__":
    main()
