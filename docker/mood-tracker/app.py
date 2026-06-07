import os
from flask import Flask, render_template, request, redirect, flash, url_for
import psycopg2

app = Flask(__name__)

# SECURITY BEST PRACTICE: Secret key pulled from environment
app.secret_key = os.getenv("APP_SECRET_KEY", "dev_secret_key_low_security")

# Database configuration pulled from environment variables
DB_CONFIG = {
    "host": "127.0.0.1",
    "database": os.getenv("DB_NAME", "homelab_db"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "REPLACE_WITH_ACTUAL_PASSWORD")
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    mood = request.form.get('mood')
    comment = request.form.get('comment')
    
    if not mood:
        flash("Pick a face!", "error")
        return redirect('/')
        
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # Using parameterized queries to prevent SQL Injection (OWASP Best Practice)
        cur.execute("INSERT INTO daily_mood (current_mood, comment) VALUES (%s, %s)", (mood, comment))
        conn.commit()
        cur.close()
        conn.close()
        flash("Saved to SSD!", "success")
        return redirect('/')
    except Exception as e:
        # Logging error to console but returning generic error to user
        print(f"Database Error: {e}")
        return "Internal Server Error", 500

if __name__ == '__main__':
    # Listening on Port 8003
    app.run(host='0.0.0.0', port=8003)