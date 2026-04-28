import os
import re
import json
import logging
import asyncio
import random
import threading
import gc
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from threading import Lock
from aiohttp import ClientSession, ClientTimeout

from flask import Flask
from bs4 import BeautifulSoup
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes, JobQueue
)

# ---------- Flask for Render ----------
PORT = int(os.environ.get("PORT", 8080))
flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "Bot is running"

def run_flask():
    flask_app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)

threading.Thread(target=run_flask, daemon=True).start()

# ---------- Configuration ----------
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set!")

ADMIN_IDS = [5936431184, 8431995898]   # Replace with your admin user IDs
ORIGINAL_ADMIN_ID = ADMIN_IDS[0] if ADMIN_IDS else 0

CHANNELS = [
    {"id": -1003663859246, "link": "https://t.me/jiomartnumberchecker"}
]

# ---------- Logging ----------
logging.basicConfig(level=logging.WARNING, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)   # Ensure we see backup logs

# ---------- Data File ----------
DATA_FILE = "userdata.txt"
FILE_LOCK = Lock()
SAVE_INTERVAL_SECONDS = 300

def save_data(data: dict):
    with FILE_LOCK:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        default = {"users": {}, "gift_codes": {}, "admins": ADMIN_IDS}
        save_data(default)
        return default
    with FILE_LOCK:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

# ---------- Data Manager ----------
class BotData:
    def __init__(self):
        self.data = load_data()
        self._ensure_structure()
        self._dirty = False

    def _ensure_structure(self):
        if "users" not in self.data:
            self.data["users"] = {}
        if "gift_codes" not in self.data:
            self.data["gift_codes"] = {}
        if "admins" not in self.data:
            self.data["admins"] = ADMIN_IDS
        for aid in ADMIN_IDS:
            if aid not in self.data["admins"]:
                self.data["admins"].append(aid)
        for uid, user in self.data["users"].items():
            if "subscription_start" not in user:
                user["subscription_start"] = None
            if "subscription_duration" not in user:
                user["subscription_duration"] = 0
            if "notified_60pct" not in user:
                user["notified_60pct"] = False
            for days in [10,5,3,2,1]:
                if f"notified_{days}d" not in user:
                    user[f"notified_{days}d"] = False
            if "notified_last_day" not in user:
                user["notified_last_day"] = False
            if "last_credit_notify" not in user:
                user["last_credit_notify"] = 0
        self._mark_dirty()

    def _mark_dirty(self):
        self._dirty = True

    def save(self):
        save_data(self.data)
        self._dirty = False

    async def periodic_save(self):
        if self._dirty:
            self.save()

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.data.get("admins", [])

    def add_admin(self, user_id: int) -> bool:
        if user_id in self.data["admins"]:
            return False
        self.data["admins"].append(user_id)
        self._mark_dirty()
        return True

    def get_user(self, user_id: int) -> dict:
        uid = str(user_id)
        if uid not in self.data["users"]:
            self.data["users"][uid] = {
                "credits": 0,
                "credit_batches": [],
                "free_searches_used": 0,
                "referral_count": 0,
                "referred_by": None,
                "subscription_end": None,
                "subscription_start": None,
                "subscription_duration": 0,
                "claimed_gifts": [],
                "total_referrals_given": 0,
                "join_date": datetime.now().timestamp(),
                "notified_60pct": False,
                "notified_10d": False, "notified_5d": False, "notified_3d": False,
                "notified_2d": False, "notified_1d": False, "notified_last_day": False,
                "last_credit_notify": 0
            }
            self._mark_dirty()
        return self.data["users"][uid]

    def update_user(self, user_id: int, updates: dict):
        uid = str(user_id)
        user = self.get_user(user_id)
        user.update(updates)
        self._mark_dirty()

    def add_credits(self, user_id: int, amount: int, expiry_days: int = 30):
        user = self.get_user(user_id)
        expiry = (datetime.now() + timedelta(days=expiry_days)).timestamp()
        user["credit_batches"].append({"amount": amount, "expires": expiry})
        user["credits"] = self._total_credits(user)
        self._mark_dirty()

    def _total_credits(self, user: dict) -> int:
        now = datetime.now().timestamp()
        total = 0
        new_batches = []
        for b in user["credit_batches"]:
            if b["expires"] > now:
                total += b["amount"]
                new_batches.append(b)
        user["credit_batches"] = new_batches
        return total

    def use_credit(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        self._total_credits(user)
        if user["credits"] <= 0:
            return False
        for batch in user["credit_batches"]:
            if batch["amount"] > 0:
                batch["amount"] -= 1
                user["credits"] -= 1
                self._mark_dirty()
                return True
        return False

    def remove_credits(self, user_id: int, amount: int) -> bool:
        if amount <= 0:
            return True
        user = self.get_user(user_id)
        if user["credits"] < amount:
            return False
        remaining = amount
        for batch in user["credit_batches"]:
            if remaining <= 0:
                break
            if batch["amount"] >= remaining:
                batch["amount"] -= remaining
                remaining = 0
            else:
                remaining -= batch["amount"]
                batch["amount"] = 0
        user["credits"] = self._total_credits(user)
        self._mark_dirty()
        return True

    def extend_subscription(self, user_id: int, duration: timedelta):
        user = self.get_user(user_id)
        now = datetime.now()
        if user["subscription_end"]:
            current_end = datetime.fromtimestamp(user["subscription_end"])
            new_end = max(current_end, now) + duration
        else:
            new_end = now + duration
            user["subscription_start"] = now.timestamp()
            user["subscription_duration"] = duration.total_seconds()
        user["subscription_end"] = new_end.timestamp()
        if user["subscription_start"]:
            total_seconds = new_end.timestamp() - user["subscription_start"]
            user["subscription_duration"] = total_seconds
        self._mark_dirty()

    def has_active_subscription(self, user_id: int) -> bool:
        user = self.get_user(user_id)
        if user["subscription_end"] is None:
            return False
        return datetime.fromtimestamp(user["subscription_end"]) > datetime.now()

    def get_subscription_remaining(self, user_id: int) -> Tuple[bool, Optional[timedelta], Optional[float]]:
        user = self.get_user(user_id)
        if not user["subscription_end"]:
            return False, None, None
        now = datetime.now()
        end = datetime.fromtimestamp(user["subscription_end"])
        if now >= end:
            return False, None, 100.0
        remaining = end - now
        percent_used = 0
        if user["subscription_start"] and user["subscription_duration"]:
            start = datetime.fromtimestamp(user["subscription_start"])
            total_seconds = user["subscription_duration"]
            elapsed = (now - start).total_seconds()
            percent_used = (elapsed / total_seconds) * 100 if total_seconds > 0 else 0
        return True, remaining, percent_used

    def generate_gift_code(self, code: str, duration: timedelta):
        self.data["gift_codes"][code] = {
            "duration_seconds": duration.total_seconds(),
            "claimed": False,
            "claimed_by": None,
            "created_at": datetime.now().timestamp()
        }
        self._mark_dirty()

    def claim_gift_code(self, code: str, user_id: int) -> bool:
        gift = self.data["gift_codes"].get(code)
        if not gift or gift["claimed"]:
            return False
        gift["claimed"] = True
        gift["claimed_by"] = user_id
        duration = timedelta(seconds=gift["duration_seconds"])
        self.extend_subscription(user_id, duration)
        user = self.get_user(user_id)
        user["claimed_gifts"].append(code)
        self._mark_dirty()
        return True

    def delete_gift_code(self, code: str) -> bool:
        gift = self.data["gift_codes"].pop(code, None)
        if not gift:
            return False
        if gift["claimed"]:
            user_id = gift["claimed_by"]
            if user_id:
                user = self.get_user(user_id)
                user["subscription_end"] = None
                user["subscription_start"] = None
                self._mark_dirty()
        self._mark_dirty()
        return True

    def get_active_codes(self) -> List[Tuple[str, dict]]:
        return [(c, info) for c, info in self.data["gift_codes"].items() if not info["claimed"]]

    def process_referral(self, new_user_id: int, referrer_id: Optional[int]) -> bool:
        if referrer_id is None or referrer_id == new_user_id:
            return False
        referrer = self.get_user(referrer_id)
        if referrer["referral_count"] >= 50:
            return False
        referrer["referral_count"] += 1
        self.add_credits(referrer_id, 1, 30)
        new_user = self.get_user(new_user_id)
        new_user["referred_by"] = referrer_id
        self._mark_dirty()
        return True

    def get_expiring_credits(self, days_before: int = 10) -> List[Tuple[int, int, datetime]]:
        now = datetime.now()
        threshold = now + timedelta(days=days_before)
        result = []
        for uid_str, user in self.data["users"].items():
            uid = int(uid_str)
            for batch in user["credit_batches"]:
                expiry = datetime.fromtimestamp(batch["expires"])
                if now < expiry <= threshold and batch["amount"] > 0:
                    result.append((uid, batch["amount"], expiry))
        return result

    def get_all_user_ids(self) -> List[int]:
        return [int(uid) for uid in self.data["users"].keys()]

# ---------- Force Join Cache ----------
class LRUCache:
    def __init__(self, maxsize=500):
        self.cache = OrderedDict()
        self.maxsize = maxsize
    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.maxsize:
            self.cache.popitem(last=False)

join_cache = LRUCache(maxsize=500)
JOIN_CACHE_TTL = 30

async def is_user_member_of_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE, force_refresh: bool = False) -> bool:
    if not force_refresh:
        now = datetime.now().timestamp()
        cached = join_cache.get(user_id)
        if cached and (now - cached[0]) < JOIN_CACHE_TTL:
            return all(cached[1].values())
    status = {}
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            status[ch["id"]] = member.status in ["member", "administrator", "creator"]
        except Exception:
            status[ch["id"]] = False
    join_cache.set(user_id, (datetime.now().timestamp(), status))
    return all(status.values())

# ---------- Async Jio Checker ----------
async def check_jio_status_async(mobile_number: str) -> str:
    url = "https://acczone.xyz/checker/jio.php"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://acczone.xyz",
        "Referer": "https://acczone.xyz/checker/jio.php",
    }
    data = {"number": mobile_number}
    timeout = ClientTimeout(total=10)
    try:
        async with ClientSession(timeout=timeout) as session:
            async with session.post(url, headers=headers, data=data) as resp:
                text = await resp.text()
    except Exception as e:
        logger.error(f"Jio check error: {e}")
        return f"Network error: {str(e)}"

    soup = BeautifulSoup(text, "html.parser")
    result_div = soup.find("div", id="result-display")
    if not result_div:
        if "Registered" in text and "✅" in text:
            return "Registered ✅"
        elif "Unregistered" in text and "❌" in text:
            return "Unregistered ❌"
        return "Could not parse result."
    value_div = result_div.find("div", class_="result-value")
    if value_div:
        text_val = value_div.get_text(strip=True)
        if "Registered" in text_val:
            return "Registered ✅"
        elif "Unregistered" in text_val:
            return "Unregistered ❌"
        return text_val
    return "Result format not found."

# ---------- UI Helpers ----------
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📞 JioMart", callback_data="action_jiomart")],
        [InlineKeyboardButton("💰 Balance", callback_data="action_balance"),
         InlineKeyboardButton("🎫 Claim Code", callback_data="action_claim")],
        [InlineKeyboardButton("🔗 Referral", callback_data="action_referral"),
         InlineKeyboardButton("💎 Buy", callback_data="action_buy")],
        [InlineKeyboardButton("📖 Help", callback_data="action_help")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def get_user_status_text(user_id: int) -> str:
    user = data_manager.get_user(user_id)
    credits = user["credits"]
    free_left = 2 - user["free_searches_used"]
    if free_left < 0:
        free_left = 0
    referral_count = user["referral_count"]
    active, remaining, _ = data_manager.get_subscription_remaining(user_id)
    if active:
        if remaining.days > 0:
            time_left = f"{remaining.days} days"
        else:
            hours = remaining.seconds // 3600
            time_left = f"{hours} hours"
        sub_text = f"✅ Active (expires in {time_left})"
    else:
        sub_text = "❌ Inactive"
    status = (
        f"🌟 *𝗝𝗜𝗢𝗠𝗔𝗥𝗧 𝗡𝗨𝗠𝗕𝗘𝗥 𝗖𝗛𝗘𝗖𝗞𝗘𝗥*\n"
        f"👤 *User Dashboard*\n"
        f"💎 Credits: `{credits}`\n"
        f"🎁 Free searches left: `{free_left}`\n"
        f"🔗 Referrals: `{referral_count}/50`\n"
        f"🛡️ Subscription: {sub_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✨ *Main Menu* ✨\n"
        f"Choose an option below:"
    )
    return status

async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, message=None, query=None):
    user_id = update.effective_user.id if update.effective_user else query.from_user.id
    status_text = await get_user_status_text(user_id)
    if query:
        await query.edit_message_text(status_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    elif message:
        await message.edit_text(status_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    else:
        await update.message.reply_text(status_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# ---------- Bot Handlers ----------
data_manager = BotData()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    if not data_manager.is_admin(user_id) and not await is_user_member_of_channels(user_id, context):
        keyboard = [[InlineKeyboardButton("🔓 Join Channel", url=ch["link"])] for ch in CHANNELS]
        keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data="force_join_check")])
        await update.message.reply_text(
            "👋 *Welcome!*\n\nPlease join our channel(s) to use the bot.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    ref_param = context.args[0] if context.args else None
    referrer_id = None
    if ref_param and ref_param.startswith("ref_"):
        try:
            referrer_id = int(ref_param.split("_")[1])
        except ValueError:
            pass

    data_manager.get_user(user_id)

    if referrer_id and data_manager.get_user(user_id).get("referred_by") is None:
        credited = data_manager.process_referral(user_id, referrer_id)
        if credited:
            await update.message.reply_text("🎉 You were referred! Your referrer earned 1 credit.")
            try:
                await context.bot.send_message(referrer_id, f"✅ New user (ID: {user_id}) joined via your link! +1 credit.")
            except Exception:
                pass

    await show_main_menu(update, context)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        query = update.callback_query
        help_text = (
            "📖 *Help & Commands*\n\n"
            "• Send a **10-digit number** to check Jio status.\n"
            "• Use the buttons below to navigate.\n\n"
            "*Admin commands:* (text only)\n"
            "/gengiftcode, /codestats, /delcode, /addcredit, /removecredit, /addadmin, /broadcast, /backup, /sendbackup, /restore, /stats"
        )
        await query.edit_message_text(help_text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
        ]))
    else:
        user_id = update.effective_user.id
        if not data_manager.is_admin(user_id) and not await is_user_member_of_channels(user_id, context):
            await show_force_join_prompt(update, context)
            return
        help_text = (
            "📖 *Help & Commands*\n\n"
            "• Send a **10-digit number** to check Jio status.\n"
            "• Use the buttons below to navigate.\n\n"
            "*Admin commands:* (text only)\n"
            "/gengiftcode, /codestats, /delcode, /addcredit, /removecredit, /addadmin, /broadcast, /backup, /sendbackup, /restore, /stats"
        )
        await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not data_manager.is_admin(user_id) and not await is_user_member_of_channels(user_id, context):
        await show_force_join_prompt(update, context)
        return
    active, remaining, _ = data_manager.get_subscription_remaining(user_id)
    user = data_manager.get_user(user_id)
    credits = user["credits"]
    sub_text = "Unlimited ✅" if active else "Inactive ❌"
    if active:
        if remaining.days > 0:
            sub_text += f" (expires in {remaining.days} days)"
        else:
            hours = remaining.seconds // 3600
            sub_text += f" (expires in {hours} hours)"
    text = (
        f"💰 *Your Balance*\n\n"
        f"💎 Credits: `{credits}`\n"
        f"🛡️ Subscription: {sub_text}\n"
        f"🎁 Free searches used: `{user['free_searches_used']}/2`\n"
        f"🔗 Referrals: `{user['referral_count']}/50`"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]))

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not data_manager.is_admin(user_id) and not await is_user_member_of_channels(user_id, context):
        await show_force_join_prompt(update, context)
        return
    bot_username = context.bot.username
    if not bot_username:
        bot_username = "YourBotUsername"
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"Each friend who joins gives you **1 credit** (max 50).\n"
        f"Current referrals: `{data_manager.get_user(user_id)['referral_count']}/50`"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]))

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not data_manager.is_admin(user_id) and not await is_user_member_of_channels(user_id, context):
        await show_force_join_prompt(update, context)
        return
    keyboard = [
        [InlineKeyboardButton("10₹ → 7 credits", callback_data="buy_10")],
        [InlineKeyboardButton("20₹ → 18 credits", callback_data="buy_20")],
        [InlineKeyboardButton("30₹ → 39 credits", callback_data="buy_30")],
        [InlineKeyboardButton("40₹ → 42 credits", callback_data="buy_40")],
        [InlineKeyboardButton("50₹ → 120 credits", callback_data="buy_50")],
        [InlineKeyboardButton("80₹ → 1 month unlimited", callback_data="buy_80")],
        [InlineKeyboardButton("📞 Buy via DM", url="https://t.me/afkchatgpt998")],
        [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
    ]
    await update.message.reply_text(
        "💎 *Purchase Credits*\n\nSelect a plan:\nAfter payment, admin will activate.\nSupport: @afkchatgpt998",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def claimcode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not data_manager.is_admin(user_id) and not await is_user_member_of_channels(user_id, context):
        await show_force_join_prompt(update, context)
        return
    await update.message.reply_text(
        "🎫 *Claim Gift Code*\n\nPlease send the **10-digit gift code**.\nExample: `1234567890`",
        parse_mode="Markdown"
    )
    context.user_data["expecting_code"] = True

# ---------- Button Callbacks ----------
async def balance_action(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    user_id = query.from_user.id
    active, remaining, _ = data_manager.get_subscription_remaining(user_id)
    user = data_manager.get_user(user_id)
    credits = user["credits"]
    sub_text = "Unlimited ✅" if active else "Inactive ❌"
    if active:
        if remaining.days > 0:
            sub_text += f" (expires in {remaining.days} days)"
        else:
            hours = remaining.seconds // 3600
            sub_text += f" (expires in {hours} hours)"
    text = (
        f"💰 *Your Balance*\n\n"
        f"💎 Credits: `{credits}`\n"
        f"🛡️ Subscription: {sub_text}\n"
        f"🎁 Free searches used: `{user['free_searches_used']}/2`\n"
        f"🔗 Referrals: `{user['referral_count']}/50`"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]))

async def claim_action(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    await query.edit_message_text(
        "🎫 *Claim Gift Code*\n\nPlease send the **10-digit gift code**.\nExample: `1234567890`",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
    )
    context.user_data["expecting_code"] = True

async def referral_action(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    user_id = query.from_user.id
    bot_username = context.bot.username
    if not bot_username:
        bot_username = "YourBotUsername"
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"Each friend who joins gives you **1 credit** (max 50).\n"
        f"Current referrals: `{data_manager.get_user(user_id)['referral_count']}/50`"
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]))

async def buy_action(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    keyboard = [
        [InlineKeyboardButton("10₹ → 7 credits", callback_data="buy_10")],
        [InlineKeyboardButton("20₹ → 18 credits", callback_data="buy_20")],
        [InlineKeyboardButton("30₹ → 39 credits", callback_data="buy_30")],
        [InlineKeyboardButton("40₹ → 42 credits", callback_data="buy_40")],
        [InlineKeyboardButton("50₹ → 120 credits", callback_data="buy_50")],
        [InlineKeyboardButton("80₹ → 1 month unlimited", callback_data="buy_80")],
        [InlineKeyboardButton("📞 Buy via DM", url="https://t.me/afkchatgpt998")],
        [InlineKeyboardButton("🔙 Back", callback_data="main_menu")]
    ]
    await query.edit_message_text(
        "💎 *Purchase Credits*\n\nSelect a plan:\nAfter payment, admin will activate.\nSupport: @afkchatgpt998",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def jiomart_action(update: Update, context: ContextTypes.DEFAULT_TYPE, query):
    await query.edit_message_text(
        "📞 *Jio Number Checker*\n\nPlease send a **10-digit mobile number**.\nExample: `9876543210`\n\nWe will check if it's Registered or Unregistered.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
    )
    context.user_data["expecting_number"] = True

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    user_id = update.effective_user.id

    if not data_manager.is_admin(user_id) and not await is_user_member_of_channels(user_id, context):
        await show_force_join_prompt(update, context)
        return

    if context.user_data.get("expecting_code"):
        if re.fullmatch(r"\d{10}", user_input):
            success = data_manager.claim_gift_code(user_input, user_id)
            if success:
                await update.message.reply_text("🎉 *Code claimed successfully!* Subscription extended.", parse_mode="Markdown")
            else:
                await update.message.reply_text("❌ Invalid, expired, or already used code.")
        else:
            await update.message.reply_text("❌ Invalid code. Must be 10 digits.")
        context.user_data.pop("expecting_code", None)
        await show_main_menu(update, context)
        return

    if context.user_data.get("expecting_number"):
        if re.fullmatch(r"\d{10}", user_input):
            user = data_manager.get_user(user_id)

            if data_manager.has_active_subscription(user_id):
                await update.message.chat.send_action(action="typing")
                status = await check_jio_status_async(user_input)
                await update.message.reply_text(
                    f"📱 *Jio Number:* `{user_input}`\n📡 *Status:* {status}\n✨ (Unlimited subscription active)",
                    parse_mode="Markdown"
                )
            elif user["free_searches_used"] < 2:
                user["free_searches_used"] += 1
                data_manager._mark_dirty()
                await update.message.chat.send_action(action="typing")
                status = await check_jio_status_async(user_input)
                remaining = 2 - user["free_searches_used"]
                await update.message.reply_text(
                    f"📱 *Number:* `{user_input}`\n📡 *Status:* {status}\n🎁 (Free search, {remaining} left)",
                    parse_mode="Markdown"
                )
            elif user["credits"] > 0:
                success = data_manager.use_credit(user_id)
                if success:
                    await update.message.chat.send_action(action="typing")
                    status = await check_jio_status_async(user_input)
                    remaining = data_manager.get_user(user_id)["credits"]
                    await update.message.reply_text(
                        f"📱 *Number:* `{user_input}`\n📡 *Status:* {status}\n💎 (1 credit used, {remaining} left)",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text("❌ Error using credit. Try again.")
            else:
                await update.message.reply_text(
                    "❌ *No credits left!*\nUse /buy or /referral to get more.",
                    parse_mode="Markdown"
                )
        else:
            await update.message.reply_text("❌ Invalid number. Send a 10-digit number.")
        context.user_data.pop("expecting_number", None)
        await show_main_menu(update, context)
        return

    await update.message.reply_text("🤔 Use the buttons below.", reply_markup=main_menu_keyboard())

async def show_force_join_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🔓 Join Channel", url=ch["link"])] for ch in CHANNELS]
    keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data="force_join_check")])
    await update.message.reply_text(
        "🚫 *Access Denied*\nYou must join our channel(s) to use the bot.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data != "force_join_check" and not data_manager.is_admin(user_id):
        if not await is_user_member_of_channels(user_id, context):
            keyboard = [[InlineKeyboardButton("🔓 Join Channel", url=ch["link"])] for ch in CHANNELS]
            keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data="force_join_check")])
            await query.edit_message_text(
                "🚫 *Access Denied*\nYou must join our channel(s).",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

    if data == "main_menu":
        await show_main_menu(update, context, query=query)
    elif data == "action_balance":
        await balance_action(update, context, query)
    elif data == "action_claim":
        await claim_action(update, context, query)
    elif data == "action_referral":
        await referral_action(update, context, query)
    elif data == "action_buy":
        await buy_action(update, context, query)
    elif data == "action_help":
        await help_command(update, context)
    elif data == "action_jiomart":
        await jiomart_action(update, context, query)
    elif data.startswith("buy_"):
        if data == "buy_cancel":
            await query.edit_message_text("Purchase cancelled.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]]))
            return
        plan_map = {
            "buy_10": ("10₹", 7, "credits"),
            "buy_20": ("20₹", 18, "credits"),
            "buy_30": ("30₹", 39, "credits"),
            "buy_40": ("40₹", 42, "credits"),
            "buy_50": ("50₹", 120, "credits"),
            "buy_80": ("80₹", 1, "month_unlimited")
        }
        price, value, ptype = plan_map[data]
        for admin_id in data_manager.data.get("admins", []):
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🛒 *Purchase request*\nUser: {user_id} (@{query.from_user.username or 'no username'})\nPlan: {price}\nValue: {value} {ptype}\nUse `/addcredit {user_id} {value}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass
        await query.edit_message_text(
            f"✅ Request sent to admins for *{price}* plan.\n\nFor instant purchase, DM @afkchatgpt998",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])
        )
    elif data == "force_join_check":
        if await is_user_member_of_channels(user_id, context, force_refresh=True):
            join_cache.set(user_id, (datetime.now().timestamp(), {ch["id"]: True for ch in CHANNELS}))
            await query.edit_message_text("✅ Thank you for joining! You can now use the bot.")
            await show_main_menu(update, context, query=query)
        else:
            keyboard = [[InlineKeyboardButton("🔓 Join Channel", url=ch["link"])] for ch in CHANNELS]
            keyboard.append([InlineKeyboardButton("✅ I've Joined", callback_data="force_join_check")])
            await query.edit_message_text("❌ You haven't joined all required channels yet.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await query.edit_message_text("Unknown action.", reply_markup=main_menu_keyboard())

# ---------- Admin Handlers ----------
async def admin_check(update: Update) -> bool:
    if not data_manager.is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return False
    return True

async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update) or update.effective_user.id != ORIGINAL_ADMIN_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    try:
        new_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Invalid user ID.")
        return
    if data_manager.add_admin(new_id):
        await update.message.reply_text(f"✅ {new_id} is now admin.")
        try:
            await context.bot.send_message(new_id, "🎉 You are now an admin.")
        except Exception:
            pass
    else:
        await update.message.reply_text("Already admin.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = " ".join(context.args)
    users = data_manager.get_all_user_ids()
    success = 0
    for uid in users:
        try:
            await context.bot.send_message(uid, f"📢 *Broadcast:*\n{msg}", parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await update.message.reply_text(f"Broadcast sent to {success} users.")

async def gen_gift_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /gengiftcode <duration> (e.g., 24hrs, 5d, 1m)")
        return
    dur = context.args[0].lower()
    match = re.match(r"(\d+)(hrs?|d|m)$", dur)
    if not match:
        await update.message.reply_text("Invalid format.")
        return
    val = int(match.group(1))
    unit = match.group(2)
    if unit.startswith("hr"):
        delta = timedelta(hours=val)
    elif unit == "d":
        delta = timedelta(days=val)
    else:
        delta = timedelta(days=val*30)
    code = str(random.randint(10**9, 10**10 - 1))
    data_manager.generate_gift_code(code, delta)
    await update.message.reply_text(f"✅ Code: `{code}`\nDuration: {dur}", parse_mode="Markdown")

async def codestats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    active = data_manager.get_active_codes()
    if not active:
        await update.message.reply_text("No active codes.")
        return
    text = "\n".join([f"`{c}` - {timedelta(seconds=info['duration_seconds'])}" for c, info in active[:10]])
    await update.message.reply_text(f"*Active codes (first 10):*\n{text}", parse_mode="Markdown")

async def delcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    if not context.args:
        await update.message.reply_text("Usage: /delcode <code>")
        return
    code = context.args[0]
    if data_manager.delete_gift_code(code):
        await update.message.reply_text(f"Deleted `{code}`.", parse_mode="Markdown")
    else:
        await update.message.reply_text("Code not found.")

async def addcredit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addcredit <user_id> <amount>")
        return
    try:
        uid = int(context.args[0])
        amt = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid arguments.")
        return
    data_manager.add_credits(uid, amt, 30)
    await update.message.reply_text(f"Added {amt} credits to {uid}.")
    try:
        await context.bot.send_message(uid, f"🎉 You received {amt} credits! Use /balance.")
    except Exception:
        pass

async def removecredit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /removecredit <user_id> <amount>")
        return
    try:
        uid = int(context.args[0])
        amt = int(context.args[1])
    except ValueError:
        await update.message.reply_text("Invalid arguments.")
        return
    if data_manager.remove_credits(uid, amt):
        await update.message.reply_text(f"Removed {amt} credits from {uid}.")
        try:
            await context.bot.send_message(uid, f"⚠️ {amt} credits removed from your account.")
        except Exception:
            pass
    else:
        await update.message.reply_text("Insufficient credits.")

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    data_manager.save()
    with open(DATA_FILE, "rb") as f:
        await update.message.reply_document(f, filename="userdata_backup.json")

async def sendbackup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    await send_backup_to_admins(context.bot)
    await update.message.reply_text("✅ Backup sent to all admins.")

async def restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    await update.message.reply_text("Send the JSON backup file.")

async def handle_restore_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not data_manager.is_admin(update.effective_user.id):
        return
    doc = update.message.document
    if not doc or not doc.file_name.endswith(".json"):
        await update.message.reply_text("Send a JSON file.")
        return
    file = await context.bot.get_file(doc.file_id)
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        await file.download_to_drive(tmp.name)
        with open(tmp.name, "r") as f:
            new_data = json.load(f)
    data_manager.data = new_data
    data_manager._ensure_structure()
    for uid_str, user in data_manager.data["users"].items():
        user["credits"] = data_manager._total_credits(user)
    data_manager.save()
    await update.message.reply_text("✅ Data restored.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_check(update):
        return
    users = data_manager.data["users"]
    total = len(users)
    active_codes = len(data_manager.get_active_codes())
    total_credits = sum(u["credits"] for u in users.values())
    subs = sum(1 for u in users.values() if u.get("subscription_end") and datetime.fromtimestamp(u["subscription_end"]) > datetime.now())
    await update.message.reply_text(f"📊 *Stats*\nUsers: {total}\nActive codes: {active_codes}\nCredits: {total_credits}\nSubscriptions: {subs}", parse_mode="Markdown")

# ---------- Automatic Backup (FIXED) ----------
async def send_backup_to_admins(bot):
    """Save and send userdata_backup.json to all admins with stats caption."""
    try:
        # Force save latest data
        data_manager.save()
        if not os.path.exists(DATA_FILE):
            logger.error("Backup failed: userdata.txt does not exist")
            return

        total_users = len(data_manager.data.get("users", {}))
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        caption = f"📦 Hourly Backup\nUsers: {total_users}\nTime: {current_time}"
        admins = data_manager.data.get("admins", [])
        if not admins:
            logger.warning("No admins found to send backup")
            return

        logger.info(f"Sending hourly backup to {len(admins)} admins. Users: {total_users}")
        with open(DATA_FILE, "rb") as f:
            for admin_id in admins:
                try:
                    await bot.send_document(
                        chat_id=admin_id,
                        document=f,
                        filename="userdata_backup.json",
                        caption=caption
                    )
                    f.seek(0)  # important: rewind for next admin
                    logger.info(f"Backup sent to admin {admin_id}")
                except Exception as e:
                    logger.error(f"Failed to send backup to admin {admin_id}: {e}")
    except Exception as e:
        logger.error(f"send_backup_to_admins error: {e}")

async def hourly_backup_job(context: ContextTypes.DEFAULT_TYPE):
    """Job that runs every hour to send backup to admins."""
    logger.info("Running hourly backup job...")
    await send_backup_to_admins(context.bot)

# ---------- Expiry Notifications ----------
async def check_subscription_expirations(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    for uid_str, user in data_manager.data["users"].items():
        uid = int(uid_str)
        end_ts = user.get("subscription_end")
        if not end_ts:
            continue
        end = datetime.fromtimestamp(end_ts)
        if now >= end:
            continue
        remaining = end - now
        days_left = remaining.days
        percent_used = 0
        if user.get("subscription_start") and user.get("subscription_duration"):
            start = datetime.fromtimestamp(user["subscription_start"])
            total = user["subscription_duration"]
            elapsed = (now - start).total_seconds()
            percent_used = (elapsed / total) * 100 if total > 0 else 0
        send_notify = False
        message = ""
        if percent_used >= 60 and not user.get("notified_60pct"):
            user["notified_60pct"] = True
            send_notify = True
            message = f"⚠️ *60% of your subscription period has passed!* You have {remaining.days} days left. Renew soon to avoid interruption."
        elif days_left in [10,5,3,2,1] and not user.get(f"notified_{days_left}d"):
            user[f"notified_{days_left}d"] = True
            send_notify = True
            message = f"⏰ *Your subscription expires in {days_left} days!* Please renew via /buy to continue enjoying unlimited checks."
        elif days_left == 0 and remaining.seconds <= 86400 and not user.get("notified_last_day"):
            user["notified_last_day"] = True
            send_notify = True
            message = "⚠️ *Your subscription ends TODAY!* Renew immediately to keep using unlimited checks."
        if send_notify:
            try:
                await context.bot.send_message(uid, message, parse_mode="Markdown")
                data_manager._mark_dirty()
            except Exception:
                pass
    data_manager.save()

async def check_credit_expirations(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    expiring = data_manager.get_expiring_credits(10)
    for uid, amount, expiry in expiring:
        days = (expiry - now).days
        user = data_manager.get_user(uid)
        last_notify = user.get("last_credit_notify", 0)
        if now.timestamp() - last_notify > 86400:
            try:
                await context.bot.send_message(
                    uid,
                    f"⚠️ *Credit Expiry Warning*\n{amount} credit(s) will expire on {expiry.strftime('%Y-%m-%d')} (in {days} days).\nUse them before they expire!",
                    parse_mode="Markdown"
                )
                user["last_credit_notify"] = now.timestamp()
                data_manager._mark_dirty()
            except Exception:
                pass
    data_manager.save()

# ---------- Periodic Jobs ----------
async def periodic_save_job(context: ContextTypes.DEFAULT_TYPE):
    await data_manager.periodic_save()

async def hourly_admin_update(context: ContextTypes.DEFAULT_TYPE):
    if not data_manager.data.get("admins"):
        return
    users = data_manager.data["users"]
    total = len(users)
    active_codes = len(data_manager.get_active_codes())
    subs = sum(1 for u in users.values() if u.get("subscription_end") and datetime.fromtimestamp(u["subscription_end"]) > datetime.now())
    msg = f"⏰ *Hourly Stats*\nUsers: {total}\nCodes: {active_codes}\nSubscriptions: {subs}"
    for aid in data_manager.data["admins"]:
        try:
            await context.bot.send_message(aid, msg, parse_mode="Markdown")
        except Exception:
            pass

async def gc_job(context: ContextTypes.DEFAULT_TYPE):
    gc.collect()
    logger.info("Garbage collection executed")

# ---------- Main ----------
def main():
    gc.collect()
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("claimcode", claimcode_command))

    # Admin commands
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("gengiftcode", gen_gift_code))
    app.add_handler(CommandHandler("codestats", codestats))
    app.add_handler(CommandHandler("delcode", delcode))
    app.add_handler(CommandHandler("addcredit", addcredit))
    app.add_handler(CommandHandler("removecredit", removecredit))
    app.add_handler(CommandHandler("backup", backup))
    app.add_handler(CommandHandler("sendbackup", sendbackup))
    app.add_handler(CommandHandler("restore", restore))
    app.add_handler(CommandHandler("stats", stats))

    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_restore_file))

    # Callback handler
    app.add_handler(CallbackQueryHandler(callback_handler))

    # Job queue
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(periodic_save_job, interval=SAVE_INTERVAL_SECONDS, first=10)
        job_queue.run_repeating(hourly_admin_update, interval=3600, first=60)
        # Run backup every hour (first run after 60 seconds)
        job_queue.run_repeating(hourly_backup_job, interval=3600, first=60)
        job_queue.run_repeating(check_subscription_expirations, interval=43200, first=60)
        job_queue.run_repeating(check_credit_expirations, interval=86400, first=300)
        job_queue.run_repeating(gc_job, interval=3600, first=3600)

    # Send startup message to all admins
    async def startup_notification():
        await asyncio.sleep(5)
        for admin_id in data_manager.data.get("admins", []):
            try:
                await app.bot.send_message(admin_id, "🤖 *Bot started!*\nHourly backup job is active.", parse_mode="Markdown")
                logger.info(f"Startup notification sent to admin {admin_id}")
            except Exception as e:
                logger.error(f"Could not send startup message to {admin_id}: {e}")
    loop = asyncio.get_event_loop()
    loop.create_task(startup_notification())

    logger.info("Bot started with automatic hourly backup (file: userdata_backup.json) to all admins.")
    app.run_polling()

if __name__ == "__main__":
    main()
