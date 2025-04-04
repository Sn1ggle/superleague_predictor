import scrapy

class TransfermarktSpider(scrapy.Spider):
    name = "transfermarkt_spider"
    allowed_domains = ["transfermarkt.ch"]
    start_urls = [
        "https://www.transfermarkt.ch/super-league/startseite/wettbewerb/C1"
    ]
    
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'
    }
    
    def parse(self, response):
        # Überprüfe, ob die Tabelle gefunden wird
        rows = response.css("table.items tbody tr")
        if not rows:
            self.logger.info("Keine Zeilen gefunden. Prüfe bitte die CSS-Selektoren.")
        for row in rows:
            position = row.css("td:nth-child(1)::text").get()
            club_name = row.css("td:nth-child(2) a::text").get()
            played = row.css("td:nth-child(3)::text").get()
            won = row.css("td:nth-child(4)::text").get()
            drawn = row.css("td:nth-child(5)::text").get()
            lost = row.css("td:nth-child(6)::text").get()
            goals_for = row.css("td:nth-child(7)::text").get()
            goals_against = row.css("td:nth-child(8)::text").get()
            goal_difference = row.css("td:nth-child(9)::text").get()
            points = row.css("td:nth-child(10)::text").get()
            
            yield {
                "position": position.strip() if position else None,
                "club_name": club_name.strip() if club_name else None,
                "played": played.strip() if played else None,
                "won": won.strip() if won else None,
                "drawn": drawn.strip() if drawn else None,
                "lost": lost.strip() if lost else None,
                "goals_for": goals_for.strip() if goals_for else None,
                "goals_against": goals_against.strip() if goals_against else None,
                "goal_difference": goal_difference.strip() if goal_difference else None,
                "points": points.strip() if points else None,
            }
