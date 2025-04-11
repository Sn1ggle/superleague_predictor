# backend/__init__.py

import os
import joblib
from flask import Flask, render_template, request
import pandas as pd
from pymongo import MongoClient
from azure.storage.blob import BlobServiceClient

def download_model():
    """Lädt das aktuellste Modell aus Azure Blob Storage herunter und speichert es lokal."""
    connection_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_str:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING ist nicht gesetzt!")
    blob_service_client = BlobServiceClient.from_connection_string(connection_str)
    container_client = blob_service_client.get_container_client("models")
    # Annahme: Die Blobnamen folgen dem Muster "model-<version>.pkl"
    blobs = list(container_client.list_blobs(name_starts_with="model-"))
    if not blobs:
        raise FileNotFoundError("Keine Modell-Datei im Blob Storage gefunden!")
    latest_blob = sorted(blobs, key=lambda b: int(b.name.split("-")[-1].replace(".pkl", "")))[-1]
    local_model_path = "best_model.pkl"
    with open(local_model_path, "wb") as f:
        f.write(container_client.download_blob(latest_blob.name).readall())
    return local_model_path

def create_app():
    app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

    # MongoDB-Verbindung über Umgebungsvariable
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI nicht gesetzt!")
    client = MongoClient(mongodb_uri)
    db = client["mdm-project1"]

    # Laden Sie Liga-Daten aus MongoDB (Implementierung analog zu vorher)
    def load_league_data():
        cursor = db["league-tables"].find()
        df = pd.DataFrame(list(cursor))
        if '_id' in df.columns:
            df.drop('_id', axis=1, inplace=True)
        numeric_cols = ['Spieltag', 'Rank', 'Spiele', 'G', 'U', 'V', 'Tore', 'Goal_Diff', 'Points']
        for col in numeric_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        df.fillna(-1, inplace=True)
        df = df[df['Future'] == False].copy()
        df['Restspiele'] = 38 - df['Spieltag']
        df['Estimated_Extra_Points'] = df['Restspiele'] * 1.2
        df['relegated'] = df['Rank'].apply(lambda x: 1 if x in [11, 12] else 0)
        return df

    league_df = load_league_data()
    teams = league_df['Team'].unique().tolist()

    # Laden Sie das Modell: Zuerst Modell aus Blob herunterladen, dann laden
    model_path = download_model()
    model = joblib.load(model_path)
    scaler = joblib.load("scaler.pkl")  # Angenommen, Ihr Skalierer wurde lokal persistiert
    features = ['Points', 'Goal_Diff', 'G', 'U', 'V', 'Restspiele', 'Estimated_Extra_Points']

    @app.route("/")
    def index():
        return render_template("index.html", teams=teams)

    @app.route("/predict", methods=["POST"])
    def predict():
        selected_team = request.form.get("team")
        error_message = None
        prediction = None
        details = {}
        try:
            team_data = league_df[league_df['Team'] == selected_team]
            if team_data.empty:
                raise ValueError("Team nicht gefunden.")
            team_data = team_data.sort_values(by="Spieltag", ascending=False).iloc[0]
            X_input = team_data[features].values.reshape(1, -1)
            X_scaled = scaler.transform(X_input)
            prob = model.predict_proba(X_scaled)[0][1]
            prediction = f"Die Wahrscheinlichkeit, dass {selected_team} absteigt, beträgt {prob*100:.2f}%."
            details["Aktuelle Punkte"] = team_data["Points"]
            details["Aktueller Rank"] = team_data["Rank"]
            details["Restspiele"] = team_data["Restspiele"]
            details["Geschätzte Extra-Punkte"] = team_data["Estimated_Extra_Points"]
            details["Aktueller Spieltag"] = team_data["Spieltag"]
            details["Simulation letzte 5 Spiele"] = "Noch in Arbeit"
        except Exception as e:
            error_message = f"Fehler: {str(e)}"
        return render_template("index.html", teams=teams, prediction=prediction, error_message=error_message, details=details)

    return app
