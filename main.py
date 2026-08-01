import secrets
import string
import time
import os
import threading
import sqlite3
from flask import Flask, jsonify
import requests

# ------------------ Configuration ------------------
WEBHOOK_URL = "https://discord.com/api/webhooks/1533131974825476156/ua5DRmLZacxJ43VW0NdiXMVUkFMW-j2qUceOjM0XH71HpKgcdzu1fmFpY_l-um2n5p-D"
DB_FILE = "gift_codes.db"
CODE_LENGTH = 16
BATCH_SIZE = 10
SEND_INTERVAL = 1  # seconds

# ------------------ Database Setup ------------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS codes (
                    code TEXT PRIMARY KEY,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    conn.commit()
    conn.close()

def is_code_used(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT 1 FROM codes WHERE code = ?", (code,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

def mark_code_used(code):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO codes (code) VALUES (?)", (code,))
    conn.commit()
    conn.close()

# ------------------ Gift Code Generation ------------------
def generate_gift_code(length=CODE_LENGTH):
    """Generate cryptographically secure random alphanumeric string."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_unique_code():
    """Generate a code that is guaranteed unique in the database."""
    while True:
        code = generate_gift_code()
        if not is_code_used(code):
            mark_code_used(code)
            return code

# ------------------ Webhook Sending ------------------
def send_links(links):
    content = "🎁 **New Gift Links**\n" + "\n".join(links)
    payload = {"content": content}
    try:
        resp = requests.post(WEBHOOK_URL, json=payload)
        resp.raise_for_status()
        print(f"[{time.ctime()}] Sent {len(links)} links.")
    except Exception as e:
        print(f"Error sending webhook: {e}")

# ------------------ Flask App ------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    # Count total generated codes
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM codes")
    count = c.fetchone()[0]
    conn.close()
    return jsonify({
        "status": "Bot Running",
        "time": time.time(),
        "total_generated": count
    })

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# ------------------ Main Loop ------------------
def gift_loop():
    while True:
        batch_links = []
        for _ in range(BATCH_SIZE):
            code = generate_unique_code()
            batch_links.append(f"https://discord.gift/{code}")
        send_links(batch_links)
        time.sleep(SEND_INTERVAL)

def main():
    init_db()
    # Start Flask thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"Flask server running on port {os.environ.get('PORT', 8080)}")
    print("Gift link generator started. Press Ctrl+C to stop.")
    try:
        gift_loop()
    except KeyboardInterrupt:
        print("\nStopped by user.")

if __name__ == "__main__":
    main()
