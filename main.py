import secrets
import string
import time
import os
import threading
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from flask import Flask, jsonify
import requests

# ------------------ Configuration ------------------
WEBHOOK_URLS = [
    "https://discord.com/api/webhooks/1533131974825476156/ua5DRmLZacxJ43VW0NdiXMVUkFMW-j2qUceOjM0XH71HpKgcdzu1fmFpY_l-um2n5p-D",
    "https://discord.com/api/webhooks/1533135055751352360/BM7bx2TvRx0FBxAqN5_9Eij6mhfKLEBk22ObKPnpLvvGPGknP6M0VPtHkqWI9Iq_DFn3"
]
DB_FILE = "gift_codes.db"
CODE_LENGTH = 16
DELAY_PER_CYCLE = 0.01   # 10 milliseconds per cycle (all webhooks sent in parallel)

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
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_unique_code():
    while True:
        code = generate_gift_code()
        if not is_code_used(code):
            mark_code_used(code)
            return code

# ------------------ Webhook Sending (Threaded) ------------------
def send_link_to_webhook(url, link):
    payload = {"content": link}
    try:
        resp = requests.post(url, json=payload)
        resp.raise_for_status()
        print(f"[{time.ctime()}] Sent to {url.split('/')[-1]}: {link}")
    except Exception as e:
        print(f"Error sending to {url}: {e}")

def send_all_links(links):
    """Send each link to its corresponding webhook in parallel using threads."""
    with ThreadPoolExecutor(max_workers=len(WEBHOOK_URLS)) as executor:
        futures = []
        for url, link in zip(WEBHOOK_URLS, links):
            futures.append(executor.submit(send_link_to_webhook, url, link))
        # Optionally wait for all to complete (not required, but we can)
        for f in futures:
            f.result()  # This will raise any exception from the thread

# ------------------ Flask App ------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
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
        # Generate unique links – one per webhook
        links = []
        for _ in WEBHOOK_URLS:
            code = generate_unique_code()
            links.append(f"https://discord.gift/{code}")
        
        # Send all links in parallel
        send_all_links(links)
        
        # Wait 10ms before next cycle
        time.sleep(DELAY_PER_CYCLE)

def main():
    init_db()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print(f"Flask server running on port {os.environ.get('PORT', 8080)}")
    print(f"Gift link generator started – each cycle generates {len(WEBHOOK_URLS)} unique links and sends them in parallel (threaded).")
    print(f"Delay per cycle: {DELAY_PER_CYCLE}s. WARNING: This will exceed Discord rate limit (5 req/sec per webhook)!")
    try:
        gift_loop()
    except KeyboardInterrupt:
        print("\nStopped by user.")

if __name__ == "__main__":
    main()
