import os
import joblib
from flask import Flask, render_template, request, jsonify, send_file
import pandas as pd
from pymongo import MongoClient
from azure.storage.blob import BlobServiceClient

def download_file_from_blob(container_name, blob_pattern, local_filename):
    """
    Lädt eine Datei aus dem angegebenen Blob-Container herunter, 
    deren Name dem übergebenen Muster (blob_pattern) entspricht, und speichert sie lokal.
    """
    connection_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not connection_str:
        raise ValueError("AZURE_STORAGE_CONNECTION_STRING ist nicht gesetzt!")
    
    blob_service_client = BlobServiceClient.from_connection_string(connection_str)
    container_client = blob_service_client.get_container_client(container_name)
    blobs = list(container_client.list_blobs(name_starts_with=blob_pattern))
    if not blobs:
        raise FileNotFoundError(f"Keine Datei gefunden, die mit '{blob_pattern}' beginnt!")
    
    # Sortieren nach Versionsnummer (angenommen, die Version steht am Ende des Blob-Namens)
    latest_blob = sorted(
        blobs, key=lambda b: int(b.name.split("-")[-1].replace(".pkl", ""))
    )[-1]
    local_path = os.path.join("..", "model", local_filename)
    # Sicherstellen, dass das Verzeichnis existiert
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    with open(local_path, "wb") as f:
        f.write(container_client.download_blob(latest_blob.name).readall())
    return local_path

def download_model_and_scaler():
    """
    Lädt sowohl das aktuellste Modell als auch den Skalierer aus dem Blob Storage herunter
    und gibt die lokalen Pfade zurück.
    """
    container_name = "models"  # Containername, wie im save.py verwendet
    model_path = download_file_from_blob(container_name, "model-", "model.pkl")
    scaler_path = download_file_from_blob(container_name, "scaler-", "scaler.pkl")
    return model_path, scaler_path

def create_app():
    """
    Initialisiert die Flask-Anwendung:
      - Stellt die Verbindung zu MongoDB her und lädt die Liga-Daten.
      - Lädt das aktuellste ML-Modell sowie den Skalierer aus Azure Blob Storage.
      - Definiert Routen für den Haupt-Endpunkt ("/") und Vorhersagen ("/predict").
    """
    app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

    # MongoDB-Verbindung via Umgebungsvariable
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        raise ValueError("MONGODB_URI nicht gesetzt!")
    client = MongoClient(mongodb_uri)
    db = client["mdm-project1"]

    def load_league_data():
        """
        Lädt Liga-Daten aus der "league-tables"-Collection in MongoDB und bereitet den DataFrame vor.
        """
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

    # Laden von Modell und Skalierer aus Azure Blob Storage
    model_path, scaler_path = download_model_and_scaler()
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
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

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
