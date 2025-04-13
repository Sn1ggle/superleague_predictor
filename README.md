# Superleague Prognose – Relegation Risk Predictor

## Überblick

Dieses Projekt prognostiziert die Wahrscheinlichkeit, dass ein Fußballverein der Superleague (Nationalliga A der Schweiz) am Ende der Saison absteigt. Basierend auf historischen Daten, aktuellen Tabellenständen und prognostizierten Restspielen werden ML-Modelle trainiert, um das Risiko für die Plätze 11 (Relegationsspiel) und 12 (direkter Abstieg) abzuschätzen. Die Anwendung kombiniert Webscraping, Datenbankintegration, Machine Learning und ein Flask-Backend zu einer ganzheitlichen Lösung.

## Daten und Verarbeitung

- **Webscraping:**  
  Ein Selenium-basierter Spider extrahiert aggregierte Liga-Tabellen und detaillierte Spielresultate von Transfermarkt.
  
- **Datenbank:**  
  Die gesammelten Daten werden mittels Delta-Import (Upsert) in eine MongoDB (CosmosDB) geladen, um Änderungen effizient zu aktualisieren.

- **Feature Engineering:**  
  Neben Standardstatistiken (z. B. Punkte, Goal-Diff) werden "Restspiele" und "Estimated_Extra_Points" berechnet, um zukünftige Punktchancen abzuschätzen.

## Machine Learning

Mehrere Modelle (Logistische Regression, Random Forest, SVC) werden trainiert und anhand von Accuracy, F1-Score und Brier Score Loss evaluiert. Das beste Modell wird zusammen mit dem zugehörigen Skalierer persistiert und in Azure Blob Storage versioniert, sodass die aktuellsten Modellversionen verfügbar sind.

## Deployment und Containerisierung

- **Flask Backend:**  
  Das Flask-Backend stellt eine API bereit, über die Nutzer die prognostizierte Relegationswahrscheinlichkeit eines Vereins abrufen können.

- **Docker:**  
  Das Projekt wird in einem Docker-Container betrieben. Das bereitgestellte Dockerfile basiert auf einem schlanken Python 3.13-Slim Image und stellt die Flask-App über Port 5000 bereit.

- **CI/CD:**  
  Zwei GitHub Actions Workflows sind implementiert:
  1. **Build & Deploy Workflow:**  
     - Baut das Docker-Image (unter Verwendung von Docker Compose) und deployed es auf Azure.
  2. **Update Model Workflow:**  
     - Führt den Webscraper aus, aktualisiert Daten in der MongoDB, trainiert das Modell neu und lädt Modell sowie Skalierer in Azure Blob Storage hoch.

## Projektstruktur
```
superleague_prognose/
├── .github/
│   └── workflows/
│       ├── modelops_build_deploy.yml     # Workflow for building and deploying the Docker container to Azure Web App
│       └── modelops_update_model.yml     # Workflow for running the scraper, retraining the ML model, and saving it to Blob Storage
├── backend/
│   └── app.py                            # Main Flask application entry point
├── model/
│   ├── model_generator.py                # Script for training and evaluating the ML models
│   ├── save.py                           # Script to upload the model and scaler to Azure Blob Storage with versioning
│   ├── best_model.pkl                    # Persisted ML model (locally stored after training)
│   └── scaler.pkl                        # Persisted scaler (for feature scaling)
├── spider/
│   ├── transfermarkt_spider.py           # Selenium & BeautifulSoup based scraper to extract league and match data from Transfermarkt
├── frontend/
│   ├── build/                            # Build output for static files (HTML, CSS, JS) of the frontend
│   └── templates/                        # Flask HTML templates for rendering the web pages
├── data/
│   ├── df_league_table_raw.csv           # Export of the aggregated league table (CSV)
│   └── df_matches_raw.csv                # Export of detailed match data (CSV)
├── Dockerfile                            # Dockerfile to build the Flask container (using Python 3.13-slim)
├── docker-compose.yml                    # (Optional) Docker Compose file for local multi-container setup (if needed)
├── requirements.in                       # List of Python dependencies for the project (input file for pip-compile)
├── requirements.txt                      # List of all Python dependencies
└── README.md                             # Projektbeschreibung und Dokumentation
```
