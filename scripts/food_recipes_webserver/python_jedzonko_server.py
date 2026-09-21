import http.server
import socketserver
import psycopg2
import urllib.parse
import os

# Configuration
PORT = 8001
#put proper config
DB_CONFIG = {
    "dbname": "dbname",
    "user": "user",
    "password": "password",
    "host": "localhost",
    "port": "port"
}

# Path to your images (expanduser handles the '~' symbol)
IMAGE_DIR = os.path.expanduser("~/webserver/pics/")

class RecipeHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)

        # 1. Route: Serve Images
        if parsed_path.path.startswith("/pics/"):
            self.serve_image(parsed_path.path)
            return

        # 2. Route: Recipe Details (if 'id' is in URL)
        if "id" in params:
            recipe_id = params["id"][0]
            self.show_recipe_details(recipe_id)
        
        # 3. Route: Home Page (List of recipes)
        else:
            category_filter = params.get("cat", [None])[0]
            self.show_recipe_list(category_filter)

    def show_recipe_list(self,category_id=None):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        categories = self.run_query('SELECT rodzaj_id, rodzaj FROM "Jedzonko".rodzaje_jedzonka ORDER BY rodzaj ASC')

        if category_id:
            query = 'SELECT przepis_id, nazwa FROM "Jedzonko".przepis WHERE rodzaj_id = %s ORDER BY nazwa'
            recipes = self.run_query(query, (category_id,))
        else:
            query = 'SELECT przepis_id, nazwa FROM "Jedzonko".przepis ORDER BY nazwa'
            recipes = self.run_query(query)
        
        # --- Build HTML ---
        html = "<html><head><style>"
        # Add a little style for the filter bar
        html += """
            body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .filter-bar { background: #f4f4f4; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
            .filter-link { 
                display: inline-block; 
                margin-right: 10px; 
                padding: 5px 12px; 
                background: #fff; 
                border: 1px solid #ddd; 
                border-radius: 20px; 
                text-decoration: none; 
                color: #333; 
                font-size: 0.9em;
            }
            .filter-link:hover { background: #e8e8e8; }
            .filter-link.active { background: #4CAF50; color: white; border-color: #4CAF50; }
            ul { list-style: none; padding: 0; }
            li { padding: 10px; border-bottom: 1px solid #eee; }
            li a { text-decoration: none; color: #4CAF50; font-weight: bold; font-size: 1.2em; }
        """
        html += "</style></head><body>"
        html += "<h1>Katalog Przepisów</h1>"

        # 3. Create the Filter UI
        html += '<div class="filter-bar">'
        html += '<strong>Filtruj: </strong>'
        
        # "Show All" link
        active_class = "active" if not category_id else ""
        html += f'<a href="/" class="filter-link {active_class}">Wszystkie</a>'
        
        # Individual category links
        for cat_id, cat_name in categories:
            # If the current link matches the active filter, highlight it
            active_class = "active" if str(cat_id) == str(category_id) else ""
            html += f'<a href="/?cat={cat_id}" class="filter-link {active_class}">{cat_name}</a>'
        html += '</div>'

        # 4. List the Recipes
        html += "<ul>"
        if not recipes:
            html += "<li>Brak przepisów w tej kategorii.</li>"
        else:
            for r_id, r_nazwa in recipes:
                html += f'<li><a href="/?id={r_id}">{r_nazwa}</a></li>'
        html += "</ul>"

        html += "</body></html>"
        self.wfile.write(html.encode("utf-8"))

    def show_recipe_details(self, recipe_id):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()

        # Database fetching
        query_name = 'SELECT nazwa,opis,czas_przygotowania_min,liczba_porcji_w_osobach FROM "Jedzonko".przepis WHERE przepis_id = %s'
        name_data = self.run_query(query_name, (recipe_id,))[0]
        name = name_data[0] if name_data[0] else "Przepis"
        opis = name_data[1] if name_data[1] else "Opis"
        czas = name_data[2] if name_data[2] else "0"
        liczba_p = name_data[3] if name_data[3] else "0"

        skladniki_query = 'SELECT produkt, ilosc, jednostka FROM "Jedzonko".przepis_skladniki WHERE przepis_id = %s'
        skladniki = self.run_query(skladniki_query, (recipe_id,))

        query_steps = 'SELECT krok_nr, opis_kroku, zdjecie_kroku FROM "Jedzonko".przepis_kroki pk WHERE pk.przepis_id = %s ORDER BY krok_nr ASC;'
        steps = self.run_query(query_steps, (recipe_id,))

        zrobione_query = 'select ocena_10, komentarz_zmiany from "Jedzonko".zrobione_dania zd WHERE zd.przepis_id = %s ORDER BY ocena_10 DESC;'
        zrobione = self.run_query(zrobione_query, (recipe_id,))
        try:
           ocena_max = zrobione[0][0]
        except:
           ocena_max = 0

        # --- HTML and Minimal CSS ---
        html = "<html><head><style>"
        html += """
            body { font-family: sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; color: #333; }
            table { border-collapse: collapse; width: 100%; margin: 20px 0; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
            th, td { padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }
            th { background-color: #f4f4f4; color: #555; text-transform: uppercase; font-size: 0.9em; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
            img { border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); margin-top: 10px; }
            .step { background: #fff; padding: 15px; border-left: 4px solid #4CAF50; margin-bottom: 20px; }
            a { color: #4CAF50; text-decoration: none; font-weight: bold; }
            .comment-card { background: #fdfdfd; border: 1px solid #eee; border-radius: 6px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);}
            .rating-badge {background-color: #4CAF50;color: white;padding: 2px 8px;border-radius: 4px;font-weight: bold;font-size: 0.9em;margin-right: 10px;}
            .comment-text {color: #555;font-style: italic;}
        """
        html += "</style></head><body>"
        
        html += f"<a href='/'>← Powrót do listy</a>"
        html += f"<h1>{name}</h1>"
        html += f"<h2>Czas: {czas}m, najwyższa ocena {ocena_max}/10</h2>"
        html += f"<p>{opis}</p>"
        html += f"<p>Liczba porcji w osobach: {liczba_p} </p>"
        
        # Table with Ingredients
        html += "<h3>Składniki</h3>"
        html += "<table>"
        html += "<thead><tr><th>Produkt</th><th>Ilość</th><th>Jednostka</th></tr></thead><tbody>"
        for skladnik in skladniki:
            produkt, ilosc, jednostka = skladnik
            html += f"<tr><td>{produkt}</td><td>{ilosc}</td><td>{jednostka}</td></tr>"
        html += "</tbody></table>"

        # Preparation Steps
        html += "<h3>Przygotowanie</h3>"
        for step in steps:
            krok_nr, opis, foto = step
            html += f"<div class='step'><strong>Krok {krok_nr}</strong><p>{opis}</p>"
            if foto:
                html += f'<img src="/pics/{foto}" style="max-width:100%; height:auto;">'
            html += "</div>"

        #Posible changes
        html += "<h2 style='margin-top: 40px; border-top: 2px solid #eee; padding-top: 20px;'>Komentarze i Uwagi</h2>"
        if not zrobione:
           html += "<p style='color: #888;'>Nie robiono jeszcze tego przepisu.</p>"
        else:
            for zrobienie in zrobione:
                ocena, komentarz = zrobienie
                # Determine badge color based on rating (optional backend logic)
                badge_color = "#4CAF50" if ocena >= 7 else "#f4b400" if ocena >= 5 else "#d93025"
                
                html += f"""
                <div class="comment-card">
                    <span class="rating-badge" style="background-color: {badge_color};">
                        {ocena}/10
                    </span>
                    <span class="comment-text">"{komentarz}"</span>
                </div>
                """

        html += "</body></html>"
        self.wfile.write(html.encode("utf-8"))
    
    def serve_image(self, path):
        # Extract filename from path (e.g., /pics/1.png -> 1.png)
        filename = os.path.basename(path)
        file_path = os.path.join(IMAGE_DIR, filename)

        if os.path.exists(file_path) and os.path.isfile(file_path):
            self.send_response(200)
            # Simple logic to set content type
            if filename.endswith(".png"): self.send_header("Content-type", "image/png")
            elif filename.endswith(".jpg"): self.send_header("Content-type", "image/jpeg")
            self.end_headers()
            
            with open(file_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "Image Not Found")

    def run_query(self, query, params=None):
        data = []
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute(query, params)
            data = cur.fetchall()
            cur.close()
            conn.close()
        except Exception as e:
            print(f"Database error: {e}")
        return data

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), RecipeHandler) as httpd:
        print(f"Server started at http://localhost:{PORT}")
        httpd.serve_forever()
