# =============================================================================
# pub_1.py - Publicación HTML de oportunidades heurísticas diarias
# =============================================================================
#
# Este script automatiza 3 tareas clave:
#
# 1. Lee el CSV diario con las top 50 oportunidades heurísticas generado
#    en la carpeta de exploración del proyecto.
#
# 2. Reemplaza dinámicamente solo el <tbody> del archivo HTML base
#    `opportunities.html`, manteniendo intactos: estilos, GTM, header, footer.
#
# 3. Publica el HTML generado en un bucket web S3 (WEB_BUCKET_NAME).
#    Y adicionalmente envía el mismo contenido por email a EMAIL_TRADING.
#
# Dependencias:
#   - pandas, boto3, bs4 (beautifulsoup4)
#   - entorno configurado con .env o .keys.sh
# =============================================================================

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
import boto3
from bs4 import BeautifulSoup
from dotenv import load_dotenv

WEB_BUCKET_NAME = os.getenv("WEB_BUCKET_NAME")
EMAIL_DESTINO = os.getenv("EMAIL_TRADING")
TEMPLATE_HTML = Path("/home/ubuntu/tr/web/templates/opportunities.html")

# === PATHS Y FECHAS ===
fecha_hoy = datetime.now().strftime("%Y-%m-%d")
CSV_FILE = Path(f"/home/ubuntu/tr/reports/senales_heuristicas/exploracion/top50_oportunidades_{fecha_hoy}.csv")
S3_HTML_KEY = "trading/opportunities.html"

# === FUNCIONES ===
sys.path.append("/home/ubuntu/tr")
from my_modules.email_sender import enviar_email


def generar_nuevo_tbody():
    df = pd.read_csv(CSV_FILE)
    df["volumen_ant"] = (df["volumen_ant"] / 1_000_000).round(0).astype(int)
    df["vol_media_60"] = (df["vol_media_60"] / 1_000_000).round(0).astype(int)
    df["canal_pct"] = df["canal_pct"].round(2)

    columnas = [
        "simbolo", "last_close", "pct_var", "p25", "p75", "score_precio", "canal_pct", "volumen_ant", "vol_media_60",
        "RSI", "MACD", "MACD_signal", "MACD_cross",
        "rl_5", "rl_std_5", "rl_60", "rl_std_60",
        "score_volumen", "score_final", "fecha_senal"
    ]
    df = df[[c for c in columnas if c in df.columns]]
    tabla_html = df.to_html(index=False, header=False, border=0, classes="dataframe tabla")
    return BeautifulSoup(tabla_html, "html.parser").find("tbody")


def generar_html_final():
    if not TEMPLATE_HTML.exists():
        raise FileNotFoundError(f"Template base no encontrado: {TEMPLATE_HTML}")
    with open(TEMPLATE_HTML, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    # Reemplazar tbody
    tabla = soup.find("table", class_="tabla")
    tabla.find("tbody").replace_with(generar_nuevo_tbody())

    # Actualizar encabezado
    encabezado = soup.find("h3")
    if encabezado:
        encabezado.string = f"Top 50 Heuristic Opportunities — {fecha_hoy}"

    # Insertar marca de tiempo
    marca = soup.new_tag("p", **{"class": "marca-actualizacion"})
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    marca.string = f"Última actualización: {timestamp}"
    tabla.insert_after(marca)

    return str(soup)



def enviar_por_email(html_str):
    if not EMAIL_DESTINO:
        print("[ERROR] EMAIL_TRADING no está definido.")
        return
    exito = enviar_email(
        asunto=f"Top oportunidades heurísticas - {fecha_hoy}",
        cuerpo=html_str,
        destinatario=EMAIL_DESTINO,
        html=True
    )
    print("[OK] Correo enviado." if exito else f"[ERROR] Fallo al enviar: {exito}")


def publicar_en_s3(html_str):
    s3 = boto3.client("s3")
    s3.put_object(
        Bucket=WEB_BUCKET_NAME,
        Key=S3_HTML_KEY,
        Body=html_str.encode("utf-8"),
        ContentType="text/html"
    )
    print(f"[OK] HTML publicado en S3: https://{WEB_BUCKET_NAME}.s3.amazonaws.com/{S3_HTML_KEY}")


# === MAIN ===
def main():
    if not CSV_FILE.exists():
        print(f"[ERROR] CSV no encontrado: {CSV_FILE}")
        return

    html = generar_html_final()
    enviar_por_email(html)
    publicar_en_s3(html)


if __name__ == "__main__":
    main()
