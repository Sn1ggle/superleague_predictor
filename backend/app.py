from flask import Flask, render_template, request
import joblib
import pandas as pd
import os

# Konfiguration des Flask-Apps – passe die Pfade zu Templates und statischen Dateien ggf. an
app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")

# Liga-Datensatz laden
league_path = '../data/df_league_table_raw.csv'
league_df = pd.read_csv(league_path)

# Überprüfe kurz die Spalten – es sollten folgende vorhanden sein:
# Season, Spieltag, Rank, Team, Spiele, G, U, V, Tore, Goal_Diff, Points
print("Spalten im Raw DataFrame:", league_df.columns.tolist())

# Wir gehen davon aus, dass die relevanten Input-Features für unser Modell folgende sind:
features = ['Points', 'Goal_Diff', 'G', 'U', 'V']

# Lade das trainierte Modell und den Skalierer
model = joblib.load('../model/best_model.pkl')
scaler = joblib.load('../model/scaler.pkl')

# Erstelle eine Liste der Teams für das Dropdown – hier verwenden wir die Spalte "Team"
teams = league_df['Team'].unique().tolist()

@app.route("/")
def index():
    # Übergib die Liste der Teams an das Template
    return render_template("index.html", teams=teams)

@app.route("/predict", methods=["POST"])
def predict():
    selected_team = request.form.get("team")
    error_message = None
    prediction = None

    try:
        # Suche den Datensatz für den ausgewählten Verein. Falls mehrere Einträge vorhanden sind,
        # nehmen wir hier einfach den ersten (z. B. den aktuellen Stand).
        team_data = league_df[league_df['Team'] == selected_team].iloc[0]
        # Extrahiere die benötigten Features
        X = team_data[features].values.reshape(1, -1)
        # Skaliere die Features
        X_scaled = scaler.transform(X)
        # Hole die Wahrscheinlichkeit, dass der Verein absteigt (Klasse 1)
        prob = model.predict_proba(X_scaled)[0][1]
        prediction = f"Die Wahrscheinlichkeit, dass {selected_team} absteigt, beträgt {prob*100:.2f}%."
    except Exception as e:
        error_message = f"Fehler bei der Vorhersage: {str(e)}"

    return render_template("index.html", teams=teams, prediction=prediction, error_message=error_message)
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
