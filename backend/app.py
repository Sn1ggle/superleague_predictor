from flask import Flask, render_template, request
import joblib
import pandas as pd
from pymongo import MongoClient
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. Initialisierung und MongoDB-Verbindung
# -----------------------------------------------------------------------------
app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

# MongoDB-Verbindung (passen Sie den Connection-String ggf. an)
client = MongoClient("mongodb://localhost:27017/")
db = client["mdm-project1"]

# -----------------------------------------------------------------------------
# 2. Laden und Vorbereiten der Liga-Daten aus MongoDB
# -----------------------------------------------------------------------------
def load_league_data():
    """
    Lädt alle Dokumente aus der "league-tables"-Collection der MongoDB und bereitet die Daten vor:
      - Entfernt den MongoDB-Index (_id)
      - Konvertiert relevante Spalten in numerische Werte
      - Füllt fehlende Werte mit -1
      - Berechnet das Feature 'Restspiele' (Differenz zwischen 38 Spieltagen und dem aktuellen Spieltag)
      - Berechnet 'Estimated_Extra_Points' als Schätzung (Restspiele * 1.2)
      - Setzt die Zielvariable 'relegated' auf 1, wenn Rank 11 oder 12 ist
    Returns:
        df (DataFrame): Vorbereiteter DataFrame, der als Eingabe für Vorhersagen dient.
    """
    cursor = db["league-tables"].find()
    df = pd.DataFrame(list(cursor))
    if '_id' in df.columns:
        df.drop('_id', axis=1, inplace=True)

    # Konvertiere relevante Spalten in numerische Werte
    numeric_cols = ['Spieltag', 'Rank', 'Spiele', 'G', 'U', 'V', 'Tore', 'Goal_Diff', 'Points']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Fehlende Werte mit -1 füllen
    df.fillna(-1, inplace=True)

    # Nur abgeschlossene Spieltage verwenden (Future == False)
    df = df[df['Future'] == False].copy()

    # Berechne Restspiele basierend auf einer Saisonlänge von 38 Spieltagen (falls nicht vorhanden)
    if 'Restspiele' not in df.columns:
        df['Restspiele'] = 38 - df['Spieltag']

    # Berechne geschätzte Extra-Punkte, z. B. 1.2 Punkte pro verbleibendem Spiel
    if 'Estimated_Extra_Points' not in df.columns:
        df['Estimated_Extra_Points'] = df['Restspiele'] * 1.2

    # Zielvariable: Ein Team gilt als gefährdet (relegated = 1), wenn Rank 11 oder 12
    df['relegated'] = df['Rank'].apply(lambda x: 1 if x in [11, 12] else 0)
    
    return df

# Laden der Daten aus MongoDB
league_df = load_league_data()
print("Vorbereitete Datensätze (Trainingsbasis):")
print(league_df.head(10))

# Erstellen der Dropdown-Liste basierend auf dem Teamnamen (alle eindeutigen Teams)
teams = league_df['Team'].unique().tolist()

# -----------------------------------------------------------------------------
# 3. Laden des persistierten Modells und Skalierers
# -----------------------------------------------------------------------------
model = joblib.load('../model/best_model.pkl')
scaler = joblib.load('../model/scaler.pkl')

# Definierter Feature-Vektor, der auch Zukunftsfeatures umfasst
features = ['Points', 'Goal_Diff', 'G', 'U', 'V', 'Restspiele', 'Estimated_Extra_Points']

# -----------------------------------------------------------------------------
# 4. Flask-Routen
# -----------------------------------------------------------------------------
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
        # Wähle alle Datensätze des ausgewählten Teams aus.
        # Um den aktuellen Stand zu berücksichtigen, sortieren wir nach "Spieltag" (absteigend) und wählen den neuesten Eintrag.
        team_data = league_df[league_df['Team'] == selected_team]
        if team_data.empty:
            raise ValueError("Das ausgewählte Team wurde nicht im Datensatz gefunden.")
        team_data = team_data.sort_values(by='Spieltag', ascending=False).iloc[0]

        # Erstelle den Input-Feature-Vektor und skaliere ihn.
        X_input = team_data[features].values.reshape(1, -1)
        X_scaled = scaler.transform(X_input)

        # Vorhersage: Berechne die Wahrscheinlichkeit, dass das Team absteigt.
        prob = model.predict_proba(X_scaled)[0][1]
        prediction = f"Die Wahrscheinlichkeit, dass {selected_team} am heutigen Tag am Saisonende absteigt, beträgt {prob*100:.2f}%."

        # Zusätzliche Details: Zeigt aktuellen Punktestand, Rank, Restspiele, geschätzte Extra-Punkte und aktuellen Spieltag.
        details['Aktuelle Punkte'] = team_data['Points']
        details['Aktueller Rank'] = team_data['Rank']
        details['Restspiele'] = team_data['Restspiele']
        details['Geschätzte Extra-Punkte'] = team_data['Estimated_Extra_Points']
        details['Aktueller Spieltag'] = team_data['Spieltag']

        # Hinweis: Zur weiteren Modellierung könnten auch simulierte Paarungen für die letzten 5 Spiele berechnet werden.
        details['Simulierte Paarungen der letzten 5 Spiele'] = "Noch nicht implementiert"

    except Exception as e:
        error_message = f"Fehler bei der Vorhersage: {str(e)}"
    
    return render_template("index.html", teams=teams, prediction=prediction, error_message=error_message, details=details)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
