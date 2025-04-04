import re
import time
import json
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup

# Funktion zum Abrufen aller Matches einer Spieltagseite
def get_all_matches_for_day(season_id, spieltag):
    base_url = "https://www.transfermarkt.ch/super-league/spieltag/wettbewerb/C1/plus/"
    url = f"{base_url}?saison_id={season_id}&spieltag={spieltag}"
    
    # Konfiguration des ChromeDrivers – passe den Pfad zum ChromeDriver an
    service = Service("../drivers/chromedriver.exe")  # Beispiel: 'drivers/chromedriver.exe'
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Headless-Modus
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(url)
    time.sleep(5)  # Warten, bis JavaScript den Inhalt geladen hat
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    
    matches = []
    # Sammle alle <div class="box">, die ein Element mit "matchresult finished" enthalten
    for box in soup.find_all("div", class_="box"):
        if box.find("span", class_="matchresult finished"):
            # Falls in der Box ein <table> existiert, versuche, alle Zeilen zu extrahieren
            table = box.find("table")
            if table:
                rows = table.find_all("tr")
                for row in rows:
                    if row.find("span", class_="matchresult finished"):
                        cells = row.find_all("td")
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        matches.append({
                            "season_id": season_id,
                            "spieltag": spieltag,
                            "cells": cell_texts
                        })
    return matches

# Funktion, die den Inhalt der Zellen parst und in strukturierte Daten überführt
def parse_match_cells(cells):
    # Annahme: Wir erwarten mindestens 9 Zellen mit folgender grober Struktur:
    # cells[0]: Home-Team-Info (z.B. "(5.)FC Lugano")
    # cells[1]: Home-Team-Short (z.B. "(5.)Lugano")
    # cells[4]: Ergebnis (z.B. "2:1")
    # cells[7]: Away-Team-Info (z.B. "Grasshoppers(11.)")
    # cells[8]: Away-Team-Short (z.B. "GCZ(11.)")
    rank_pattern = re.compile(r'\((\d+)\)')
    
    # Home Team
    home_info = cells[0] if len(cells) > 0 else ""
    home_rank_match = rank_pattern.search(home_info)
    home_rank = int(home_rank_match.group(1)) if home_rank_match else None
    home_team_long = rank_pattern.sub("", home_info).strip()
    
    home_team_short = rank_pattern.sub("", cells[1]).strip() if len(cells) > 1 else ""
    
    # Ergebnis
    result = cells[4] if len(cells) > 4 else ""
    try:
        home_goals, away_goals = map(int, result.split(":"))
    except Exception as e:
        home_goals, away_goals = None, None
    
    # Away Team
    away_info = cells[7] if len(cells) > 7 else ""
    away_rank_match = rank_pattern.search(away_info)
    away_rank = int(away_rank_match.group(1)) if away_rank_match else None
    away_team_long = rank_pattern.sub("", away_info).strip()
    
    away_team_short = rank_pattern.sub("", cells[8]).strip() if len(cells) > 8 else ""
    
    return {
        "home_rank": home_rank,
        "home_team_long": home_team_long,
        "home_team_short": home_team_short,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "away_team_long": away_team_long,
        "away_team_short": away_team_short,
        "away_rank": away_rank
    }

# Funktion zum Iterieren über alle Spieltage einer Saison
def get_all_matchdays(season_id, start_day, end_day):
    all_matches = []
    for spieltag in range(start_day, end_day+1):
        print(f"Verarbeite Spieltag {spieltag} für Saison {season_id}...")
        matches = get_all_matches_for_day(season_id, spieltag)
        for match in matches:
            try:
                parsed = parse_match_cells(match["cells"])
                parsed["season_id"] = season_id
                parsed["spieltag"] = spieltag
                all_matches.append(parsed)
            except Exception as e:
                print(f"Fehler beim Parsen von Spieltag {spieltag}: {e}")
    return all_matches

# Beispiel: Alle Spieltage der Saison 24/25 (saison_id=2024) von Spieltag 1 bis 38 abrufen
all_data = get_all_matchdays(2024, 1, 38)

# Erstelle einen pandas DataFrame
df = pd.DataFrame(all_data)
print(df.head())

# Speichere den DataFrame als CSV (optional)
df.to_csv("season_2425_data.csv", index=False)

# Optional: Speichere den DataFrame als Excel-Datei
df.to_excel("season_2425_data.xlsx", index=False)
