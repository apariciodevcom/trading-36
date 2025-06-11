import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

BASE_DIR = "/home/ec2-user/tr"
FEATURES_DIR = f"{BASE_DIR}/data/features"
MODELOS_DIR = f"{BASE_DIR}/modelos/ml"

os.makedirs(MODELOS_DIR, exist_ok=True)

def cargar_datos():
    dfs = []
    for fname in os.listdir(FEATURES_DIR):
        if fname.endswith("_features.parquet"):
            df = pd.read_parquet(os.path.join(FEATURES_DIR, fname))
            if "senal" in df.columns:
                dfs.append(df)
    if not dfs:
        raise ValueError("No se encontraron datos con la columna 'senal'")
    df_all = pd.concat(dfs, ignore_index=True)
    return df_all

def preparar_datos(df):
    df = df[df["senal"].isin(["buy", "hold", "sell"])]
    df["target"] = (df["senal"] == "buy").astype(int)
    print("Total registros:", len(df))
    print("Target positivos (buy):", df["target"].sum())

    # Seleccionar solo columnas numericas utiles
    feature_cols = df.select_dtypes(include=[np.number]).columns.difference(["target"])
    print("Features usados:", list(feature_cols))

    X = df[feature_cols].fillna(method="bfill").fillna(method="ffill")
    y = df["target"]
    return train_test_split(X, y, test_size=0.2, random_state=42)

def entrenar_modelo(X_train, y_train):
    print("Entrenando modelo con", len(X_train), "filas...")
    modelo = RandomForestClassifier(n_estimators=100, random_state=42)
    modelo.fit(X_train, y_train)
    return modelo

def main():
    print("Inicio entrenamiento modelo ML (DEBUG)")
    try:
        df = cargar_datos()
        X_train, X_test, y_train, y_test = preparar_datos(df)
        modelo = entrenar_modelo(X_train, y_train)

        y_pred = modelo.predict(X_test)
        print("\nREPORTE DE CLASIFICACION")
        print(classification_report(y_test, y_pred))

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
        model_path = os.path.join(MODELOS_DIR, f"rf_debug_buy_{timestamp}.pkl")
        joblib.dump(modelo, model_path)
        print("Modelo guardado en:", model_path)

    except Exception as e:
        print("ERROR en entrenamiento:", str(e))

if __name__ == "__main__":
    main()