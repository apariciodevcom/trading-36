import os
import json
import pandas as pd
from datetime import datetime
import boto3
from pathlib import Path

# === CONFIGURACION ===
AGENTS_DIR = Path("/home/ubuntu/tr/trading_agents")
TEMPLATE_PATH = Path("/home/ubuntu/tr/web/templates/reporte_agente_base.html")
BUCKET_NAME = "apariciodevcom"
S3_PREFIX = "trading"
FECHA_HOY = datetime.now().strftime("%Y-%m-%d")

# === CARGAR PLANTILLA HTML ===
if not TEMPLATE_PATH.exists():
    raise FileNotFoundError(f"Plantilla no encontrada: {TEMPLATE_PATH}")
with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
    BASE_TEMPLATE = f.read()

# === FUNCIONES ===
def to_html_section(df, title):
    if df.empty:
        return f"<section><h2>{title}</h2><p>No hay datos.</p></section>"
    return f"<section><h2>{title}</h2>{df.to_html(index=False, border=0, classes='tabla')}</section>"

s3 = boto3.client("s3")

# === RECORRER AGENTES ===
for agent_dir in AGENTS_DIR.iterdir():
    if not agent_dir.is_dir():
        continue

    agent_name = agent_dir.name
    print(f"[INFO] Procesando agente: {agent_name}")
    tablas = []

    try:
        archivos = {
            # Prioriza el nombre correcto, pero permite estado_cuenta.csv como fallback
            "estado_de_cuenta.csv": agent_dir / "estado_de_cuenta.csv",
            "estado_cuenta.csv": agent_dir / "estado_cuenta.csv",
            "ordenes.csv": agent_dir / "ordenes.csv",
            f"ordenes_{agent_name}_{FECHA_HOY}.csv": agent_dir / f"ordenes_{agent_name}_{FECHA_HOY}.csv",
            "posiciones_abiertas.json": agent_dir / "posiciones_abiertas.json"
        }

        # Si no hay ningún archivo, omite agente
        if all(not p.exists() for p in archivos.values()):
            print(f"[SKIP] {agent_name}: no hay archivos disponibles.")
            continue

        # === Estado de Cuenta ===
        estado_path = archivos["estado_de_cuenta.csv"]
        if not estado_path.exists() and archivos["estado_cuenta.csv"].exists():
            estado_path = archivos["estado_cuenta.csv"]

        if estado_path.exists():
            df1 = pd.read_csv(estado_path, on_bad_lines='skip')
            tablas.append(to_html_section(df1, "Estado de Cuenta"))
        else:
            tablas.append("<section><h2>Estado de Cuenta</h2><p>No disponible.</p></section>")

        # === Órdenes ===
        if archivos["ordenes.csv"].exists():
            df2 = pd.read_csv(archivos["ordenes.csv"], on_bad_lines='skip')
            tablas.append(to_html_section(df2, "Órdenes ejecutadas"))
        else:
            tablas.append("<section><h2>Órdenes ejecutadas</h2><p>No disponible.</p></section>")

        ord_hoy = archivos[f"ordenes_{agent_name}_{FECHA_HOY}.csv"]
        if ord_hoy.exists():
            df3 = pd.read_csv(ord_hoy, on_bad_lines='skip')
            tablas.append(to_html_section(df3, f"Órdenes {FECHA_HOY}"))
        else:
            tablas.append(f"<section><h2>Órdenes {FECHA_HOY}</h2><p>No disponible.</p></section>")

        # === Posiciones Abiertas ===
        pos_path = archivos["posiciones_abiertas.json"]
        if pos_path.exists():
            with open(pos_path, "r") as f:
                data = json.load(f)
            filas = []
            for simbolo, campos in data.items():
                if isinstance(campos, dict):
                    fila = {"simbolo": simbolo}
                    fila.update(campos)
                    filas.append(fila)
            df4 = pd.DataFrame(filas)
            if "fecha" in df4.columns:
                df4["fecha"] = pd.to_datetime(df4["fecha"])
                df4 = df4.sort_values("fecha").reset_index(drop=True)
                df4["fecha"] = df4["fecha"].dt.strftime("%Y-%m-%d")
            tablas.append(to_html_section(df4, "Posiciones Abiertas"))
        else:
            tablas.append("<section><h2>Posiciones Abiertas</h2><p>No disponible.</p></section>")

        # === GENERAR Y SUBIR HTML ===
        html_out = BASE_TEMPLATE\
            .replace("{{agent_name}}", agent_name)\
            .replace("{{tablas_html}}", "\n".join(tablas))\
            .replace("{{fecha}}", FECHA_HOY)\
            .replace("{{year}}", str(datetime.now().year))

        s3_key = f"{S3_PREFIX}/{agent_name}.html"
        s3.put_object(
            Bucket=BUCKET_NAME,
            Key=s3_key,
            Body=html_out.encode("utf-8"),
            ContentType="text/html"
        )
        print(f"[OK] Reporte subido: s3://{BUCKET_NAME}/{s3_key}")

    except Exception as e:
        print(f"[ERROR] {agent_name}: {e}")
