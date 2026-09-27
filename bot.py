#!/usr/bin/env python3
"""
👑 THE KING OF INFORMATION
Vehicle Info Bot - Owner Only
"""

import re, time, json, requests
from datetime import datetime
import telebot

# ==================== CONFIG ====================
BOT_TOKEN = "8415742587:AAFtsM3XYynwaWUhX_EgV4Wx2phx11uUK6U"
OWNER_ID = 8935807032
OWNER_USERNAME = "@VATEROFWHOLETG"

# Vehicle API (public)
VEHICLE_API = "http://161.248.163.233:1080/{vehicle}"
API_TIMEOUT = 25

# ==================== BOT ====================
bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
    print("✅ Webhook removed")
except Exception as e:
    print(f"⚠️ Webhook: {e}")

print("✅ Bot initialized")

# ==================== HELPERS ====================
def is_owner(user_id):
    return user_id == OWNER_ID

def now_str():
    return datetime.now().strftime("%d %b %Y, %I:%M %p")

def fetch_vehicle(vehicle):
    vehicle = vehicle.strip().upper().replace(" ", "")
    url = VEHICLE_API.format(vehicle=vehicle)
    try:
        r = requests.get(url, timeout=API_TIMEOUT)
        if r.status_code == 200:
            try:
                return True, r.json()
            except:
                return True, r.text
        return False, f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)

def format_vehicle(data):
    if isinstance(data, dict):
        out = "🚗 VEHICLE INFORMATION\n"
        out += f"📅 {now_str()}\n"
        out += "─" * 28 + "\n\n"
        for k, v in data.items():
            if v in (None, "", "NA", "N/A", "null"):
                continue
            if isinstance(v, (dict, list)):
                continue
            out += f"🔹 {k.replace('_', ' ').title()}: {v}\n"
        if len(out) < 100:
            out += "\n" + json.dumps(data, indent=2, ensure_ascii=False)[:3500]
        return out
    return str(data)[:3500]

# ==================== HANDLERS ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    try:
        if not is_owner(message.from_user.id):
            bot.reply_to(message, f"❌ Unauthorized.\n\n📌 Contact: {OWNER_USERNAME}")
            return
        bot.reply_to(message, f"""👑 <b>THE KING OF INFORMATION</b>

✅ Bot is working!
🆔 Owner: <code>{OWNER_ID}</code>

<b>Commands:</b>
/search HR26AB1234 - Vehicle info
/help - Show commands

Send any vehicle number directly (e.g. <code>PB31AM0008</code>) and bot will reply with info.
""", parse_mode='HTML')
    except Exception as e:
        print(f"❌ /start error: {e}")

@bot.message_handler(commands=['help'])
def cmd_help(message):
    try:
        if not is_owner(message.from_user.id):
            return
        bot.reply_to(message, """📖 <b>COMMANDS</b>

/search HR26AB1234 - Vehicle info
/help - This menu

Or just send vehicle number directly.""", parse_mode='HTML')
    except Exception as e:
        print(f"❌ /help error: {e}")

@bot.message_handler(commands=['search'])
def cmd_search(message):
    try:
        if not is_owner(message.from_user.id):
            bot.reply_to(message, "❌ Unauthorized.")
            return
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /search HR26AB1234")
            return
        vehicle = parts[1].strip().upper().replace(" ", "")
        if not re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}$', vehicle):
            bot.reply_to(message, "❌ Invalid vehicle number.")
            return
        loading = bot.reply_to(message, f"🔍 Searching {vehicle}...")
        ok, data = fetch_vehicle(vehicle)
        if ok:
            out = format_vehicle(data)
        else:
            out = f"❌ API Error: {data}"
        bot.edit_message_text(out, message.chat.id, loading.message_id)
    except Exception as e:
        print(f"❌ /search error: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(func=lambda m: True)
def fallback(message):
    try:
        if not is_owner(message.from_user.id):
            bot.reply_to(message, f"❌ Unauthorized.\n\n📌 Contact: {OWNER_USERNAME}")
            return
        text = (message.text or "").strip().upper().replace(" ", "")
        if re.match(r'^[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}$', text):
            # Treat as vehicle number
            loading = bot.reply_to(message, f"🔍 Searching {text}...")
            ok, data = fetch_vehicle(text)
            if ok:
                out = format_vehicle(data)
            else:
                out = f"❌ API Error: {data}"
            bot.edit_message_text(out, message.chat.id, loading.message_id)
        else:
            bot.reply_to(message, "❓ Unknown command. Use /help")
    except Exception as e:
        print(f"❌ fallback error: {e}")

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════╗
    ║   👑 THE KING OF INFORMATION                ║
    ║   Owner Only                                ║
    ╚═══════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Bot starting...")
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=10)
        except Exception as e:
            print(f"❌ Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
