# %% 
"""
Notwendige Importe und Initialisierung
----------------------------------------
- Import von Standardmodulen (re, time, datetime)
- Import von pandas zur Datenmanipulation
- Import von Selenium (webdriver und Service) und BeautifulSoup zur HTML-Extraktion
- MongoClient aus pymongo zur Verbindung mit der Datenbank
"""
import os
import re
import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
from pymongo import MongoClient

mongodb_uri = os.getenv("MONGODB_URI")
if not mongodb_uri:
    raise ValueError("Die Umgebungsvariable MONGODB_URI ist nicht gesetzt!")

# MongoDB-Verbindung aufbauen
client = MongoClient(mongodb_uri)
db = client["mdm-project1"]

# Pfad zum ChromeDriver (Anpassung nach Bedarf)
CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")

# %%
def get_table_and_match_results(season_id, spieltag):
    """
    Extrahiert die aggregierte Liga-Tabelle und die detaillierten Tagesresultate
    für einen gegebenen Spieltag einer Saison von Transfermarkt.
    
    Parameter:
        season_id (int): Die Saison-ID (z.B. 2024).
        spieltag (int): Die Spieltag-Nummer.
    
    Returns:
        league_table (list): Liste von Einträgen aus der aggregierten Tabelle. Jeder Eintrag enthält:
             [season_id, spieltag, future_flag, Rank, Team, Spiele, G, U, V, Tore, Goal_Diff, Points]
             Für zukünftige Spieltage (future_flag True) werden Tore, Goal_Diff und Points als leere Strings
             bzw. im späteren Preprocessing als -1 abgelegt.
        match_rows (list): Liste von Rohdatenzeilen (TR-Elemente) aus dem detaillierten Resultatbereich.
    """
    # Erstelle die URL anhand der Saison und des Spieltags
    url = f"https://www.transfermarkt.ch/super-league/spieltagtabelle/wettbewerb/C1?saison_id={season_id}&spieltag={spieltag}"
    
    # Selenium-Konfiguration
    service = Service(CHROMEDRIVER_PATH)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(5)  # Wartezeit, bis alle Inhalte geladen sind
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    
    # Extrahiere Datum aus Link-Elementen (Format dd.mm.yyyy)
    date_pattern = re.compile(r'\d{2}\.\d{2}\.\d{4}')
    match_date = None
    for a in soup.find_all("a", href=True):
        if "datum" in a['href']:
            candidate = a.get_text(strip=True)
            if date_pattern.match(candidate):
                try:
                    match_date = datetime.strptime(candidate, "%d.%m.%Y")
                    break
                except Exception:
                    continue
    today = datetime.today()
    future_flag = False
    if match_date:
        if match_date > today:
            print(f"Spieltag {spieltag} für Saison {season_id} liegt in der Zukunft ({match_date.strftime('%d.%m.%Y')}).")
            future_flag = True
        else:
            print(f"Spieltag {spieltag} für Saison {season_id} fand am {match_date.strftime('%d.%m.%Y')} statt.")
    else:
        print("Kein Datum gefunden.")
    
    # Aggregierte Liga-Tabelle extrahieren
    league_table = []
    table = soup.find("table", class_="items")
    if table:
        tbody = table.find("tbody")
        if tbody:
            rows = tbody.find_all("tr")
            for row in rows:
                parsed = parse_league_row(row)
                if parsed:
                    if future_flag:
                        # Für zukünftige Spieltage Ergebnisfelder leeren; diese werden später z.B. mit -1 ersetzt.
                        parsed[6] = ""  # Tore
                        parsed[7] = ""  # Goal_Diff
                        parsed[8] = ""  # Points
                    # Füge season_id, spieltag und das future_flag als erstes ein
                    parsed.insert(0, future_flag)
                    parsed.insert(0, spieltag)
                    parsed.insert(0, season_id)
                    league_table.append(parsed)
    else:
        print("Keine aggregierte Tabelle mit class 'items' gefunden!")
    
    # Extrahiere detaillierte Tagesresultate
    match_rows = []
    responsive_div = soup.find("div", class_="responsive-table")
    if responsive_div:
        table2 = responsive_div.find("table")
        if table2:
            tbody2 = table2.find("tbody")
            if tbody2:
                match_rows = tbody2.find_all("tr")
    else:
        print("Keine detaillierten Tagesresultate gefunden!")
    
    return league_table, match_rows

def parse_league_row(row):
    """
    Parst eine Zeile der aggregierten Tabelle und extrahiert:
      - Rank, Team, Spiele, G, U, V, Tore, Goal_Diff, Points.
    
    Gibt eine Liste zurück, sofern die Zeile ausreichend Daten (mindestens 10 Zellen) enthält,
    ansonsten None.
    """
    cells = row.find_all("td")
    if len(cells) < 10:
        return None
    rank = cells[0].get_text(strip=True)
    team = cells[2].get_text(strip=True)
    spiele = cells[3].get_text(strip=True)
    g = cells[4].get_text(strip=True)
    u = cells[5].get_text(strip=True)
    v = cells[6].get_text(strip=True)
    tore = cells[7].get_text(strip=True)
    goal_diff = cells[8].get_text(strip=True)
    points = cells[9].get_text(strip=True)
    return [rank, team, spiele, g, u, v, tore, goal_diff, points]

def parse_detailed_matches(match_rows):
    """
    Parst detaillierte Zeilen einer Spieltagstabelle.
    
    Header-Zeilen (Klasse "bg_blau_20") enthalten Datum und Uhrzeit, die als Kontext
    für nachfolgende Spielzeilen verwendet werden. Für Spielzeilen wird das Ergebnis
    extrahiert, sofern im Format "x:y". Liegt das Datum in der Zukunft, werden die
    Tore als -1 gesetzt (als Platzhalter für noch nicht gespielte Matches).
    """
    matches = []
    current_date = ""
    current_time = ""
    rank_pattern = re.compile(r'\(\s*(\d+)\s*\.\s*\)')
    
    for row in match_rows:
        classes = row.get("class", [])
        if "bg_blau_20" in classes:
            text = row.get_text(" ", strip=True)
            date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
            time_match = re.search(r'(\d{1,2}:\d{2})', text)
            if date_match:
                current_date = date_match.group(1)
            if time_match:
                current_time = time_match.group(1)
            continue
        cells = row.find_all("td")
        if len(cells) < 11:
            continue
        
        result_text = cells[6].get_text(strip=True)
        # Überprüfe, ob das aktuelle Datum in der Zukunft liegt und setze Ergebnis gegebenenfalls auf -1
        result_available = True
        if current_date:
            try:
                header_date = datetime.strptime(current_date, "%d.%m.%Y")
                if header_date > datetime.today():
                    result_available = False
            except Exception:
                pass
        if result_available and re.match(r'\d+:\d+', result_text):
            try:
                home_goals, away_goals = map(int, result_text.split(":"))
            except Exception:
                home_goals, away_goals = -1, -1
        else:
            home_goals, away_goals = -1, -1
        
        home_info = cells[3].get_text(strip=True)
        home_rank_match = rank_pattern.search(home_info)
        home_rank = int(home_rank_match.group(1)) if home_rank_match else None
        home_team = rank_pattern.sub("", home_info).strip()
        
        away_info = cells[8].get_text(strip=True)
        away_rank_match = rank_pattern.search(away_info)
        away_rank = int(away_rank_match.group(1)) if away_rank_match else None
        away_team = rank_pattern.sub("", away_info).strip()
        
        match_dict = {
            "date": current_date,
            "time": current_time,
            "home_rank": home_rank,
            "home_team": home_team,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "away_rank": away_rank,
            "away_team": away_team
        }
        matches.append(match_dict)
    return matches

def get_all_data(seasons, start_day, end_day):
    """
    Iteriert über alle angegebenen Spieltage für die vorgegebenen Saisons.
    Extrahiert sowohl die aggregierte Liga-Tabelle als auch die detaillierten Spielresultate.
    Fügt für jeden Datensatz Season und Spieltag hinzu.
    """
    league_all = []
    matches_all = []
    for season in seasons:
        for spieltag in range(start_day, end_day + 1):
            print(f"Verarbeite Spieltag {spieltag} für Saison {season}...")
            league_data, raw_match_rows = get_table_and_match_results(season, spieltag)
            if league_data is None:
                print(f"Keine Daten für Spieltag {spieltag} in Saison {season}.")
                continue
            league_all.extend(league_data)
            detailed_matches = parse_detailed_matches(raw_match_rows)
            for match in detailed_matches:
                match["Season"] = season
                match["Spieltag"] = spieltag
                matches_all.append(match)
    return league_all, matches_all

# %% 
# Hauptprogramm – Sammle Daten für einen bestimmten Zeitraum (hier z. B. Spieltag 30 bis 33 der Saison 2024)
league_all_data, matches_all_data = get_all_data([2023 , 2024], 1, 38)

# Erstelle DataFrames für die aggregierte Tabelle und die detaillierten Ergebnisse
league_columns = ["Season", "Spieltag", "Future", "Rank", "Team", "Spiele", "G", "U", "V", "Tore", "Goal_Diff", "Points"]
df_league_table = pd.DataFrame(league_all_data, columns=league_columns)

match_columns = ["Season", "Spieltag", "date", "time", "home_rank", "home_team", "home_goals", "away_goals", "away_rank", "away_team"]
df_matches = pd.DataFrame(matches_all_data, columns=match_columns)

# %% 
# Upsert in MongoDB: Aktualisiert vorhandene Einträge oder fügt neue hinzu basierend auf einem eindeutigen Schlüssel.
def upsert_records(collection, records, key_fields):
    for record in records:
        filter_query = {field: record[field] for field in key_fields}
        collection.update_one(filter_query, {"$set": record}, upsert=True)

# Wandle DataFrames in Listen von Dictionaries um
league_records = df_league_table.to_dict(orient="records")
matches_records = df_matches.to_dict(orient="records")

# Definiere eindeutige Schlüssel für den Delta-Import
league_key_fields = ["Season", "Spieltag", "Team"]
matches_key_fields = ["Season", "Spieltag", "date", "time", "home_team", "away_team"]

# Collections auswählen
league_collection = db["league-tables"]
matches_collection = db["matches"]

# Führe den Upsert durch
upsert_records(league_collection, league_records, league_key_fields)
upsert_records(matches_collection, matches_records, matches_key_fields)

print("Delta-Import: Daten wurden erfolgreich in MongoDB aktualisiert bzw. eingefügt.")

# Exportiere die Ergebnisse auch lokal als CSV
df_matches.to_csv("../data/df_matches_raw.csv", index=False)
df_league_table.to_csv("../data/df_league_table_raw.csv", index=False)
