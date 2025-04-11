# %%
import os
import pandas as pd
import numpy as np
from pymongo import MongoClient
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import classification_report, accuracy_score, f1_score, brier_score_loss
import joblib

# -----------------------------------------------------------------------------
# 1. Daten aus MongoDB laden
# -----------------------------------------------------------------------------
# Aufbau der Verbindung zur MongoDB und Laden aller Dokumente aus der "league-tables" Collection
mongodb_uri = os.getenv("MONGODB_URI")
if not mongodb_uri:
    raise ValueError("Die Umgebungsvariable MONGODB_URI ist nicht gesetzt!")

client = MongoClient(mongodb_uri)
db = client["mdm-project1"]
cursor = db["league-tables"].find()
df = pd.DataFrame(list(cursor))
if '_id' in df.columns:
    df.drop('_id', axis=1, inplace=True)
print("Geladene Spalten:", df.columns.tolist())

# -----------------------------------------------------------------------------
# 2. Datenvorbereitung
# -----------------------------------------------------------------------------
# Konvertiere relevante Spalten in numerische Werte
numeric_cols = ['Spieltag', 'Rank', 'Spiele', 'G', 'U', 'V', 'Tore', 'Goal_Diff', 'Points']
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Fülle alle fehlenden Werte in den Spalten mit -1
df.fillna(-1, inplace=True)

# Filter: Für das Modelltraining werden nur bereits abgeschlossene Spieltage verwendet. 
# (Es wird angenommen, dass in der Spalte "Future" bereits ein boolescher Wert vorhanden ist.)
df_train = df[df['Future'] == False].copy()

# Berechne das Feature "Restspiele" (Differenz zur Saisonlänge von 38 Spieltagen), falls nicht vorhanden
if 'Restspiele' not in df_train.columns:
    df_train['Restspiele'] = 38 - df_train['Spieltag']

# Berechne "Estimated_Extra_Points" als Schätzung (zum Beispiel 1.2 Punkte pro verbleibendem Spiel)
if 'Estimated_Extra_Points' not in df_train.columns:
    df_train['Estimated_Extra_Points'] = df_train['Restspiele'] * 1.2

# Zielvariable: Ein Team gilt als gefährdet (relegated = 1), wenn der Rank entweder 11 oder 12 beträgt.
df_train['relegated'] = df_train['Rank'].apply(lambda x: 1 if x in [11, 12] else 0)

# Kontrolle der ersten Zeilen
print("Beispiel-Datensätze (Trainingsdaten):")
print(df_train.head(15))

# -----------------------------------------------------------------------------
# 3. Trainingsdaten definieren und Feature-Vektor erstellen
# -----------------------------------------------------------------------------
# Die Feature-Matrix beinhaltet aktuelle Leistungsdaten und Zukunftsfeatures
features = ['Points', 'Goal_Diff', 'G', 'U', 'V', 'Restspiele', 'Estimated_Extra_Points']
X = df_train[features]
y = df_train['relegated']

# Sicherstellen, dass keine fehlenden Werte in den Features vorliegen
assert X.isna().sum().sum() == 0, "Es gibt noch NaN-Werte in den Features!"

# Aufteilen in Trainings- (80%) und Testdaten (20%)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# -----------------------------------------------------------------------------
# 4. Vorverarbeitung: Skalierung
# -----------------------------------------------------------------------------
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# -----------------------------------------------------------------------------
# 5. Modelltraining und Evaluation
# -----------------------------------------------------------------------------
# Drei Klassifikatoren werden mit der Option class_weight='balanced' trainiert, um der Klassenunbalance entgegenzuwirken.
models = {
    'Logistic Regression': LogisticRegression(max_iter=1000, class_weight='balanced'),
    'Random Forest': RandomForestClassifier(random_state=42, class_weight='balanced'),
    'Support Vector Classifier': SVC(probability=True, class_weight='balanced')
}

model_scores = {}

for name, model in models.items():
    model.fit(X_train_scaled, y_train)
    y_pred = model.predict(X_test_scaled)
    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    brier = brier_score_loss(y_test, model.predict_proba(X_test_scaled)[:, 1])
    print(f"Modell: {name}")
    print(classification_report(y_test, y_pred))
    print(f"Accuracy: {acc:.4f} | F1-Score: {f1:.4f} | Brier Score Loss: {brier:.4f}")
    print("-" * 50)
    model_scores[name] = {"accuracy": acc, "f1": f1, "brier": brier}

# Auswahl des besten Modells basierend auf dem höchsten F1-Score
best_model_name = max(model_scores, key=lambda k: model_scores[k]['f1'])
print(f"Bestes Modell basierend auf F1-Score: {best_model_name}")
best_model = models[best_model_name]

# -----------------------------------------------------------------------------
# 6. Persistierung
# -----------------------------------------------------------------------------
# Speichern des besten Modells und des Skalierers für den späteren Einsatz (z.B. im Flask-Service)
joblib.dump(best_model, 'best_model.pkl')
joblib.dump(scaler, 'scaler.pkl')
print("Bestes Modell und Skalierer wurden gespeichert.")



