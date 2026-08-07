#!/usr/bin/env python3
"""
📹 TOKEN VIDEO BOT - TRANSACTION FIXED
"""

import os
import time
import logging
import random
import string
import pg8000
from datetime import datetime, timedelta
import telebot
from telebot import types

# ==================== CONFIG ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
OWNER_ID = 8935807032

# ==================== DATABASE CONNECTION ====================
DB_HOST = "reseau.proxy.rlwy.net"
DB_PORT = 29905
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASSWORD = "dOkCcwkemyQRRXGnyOGBwlJloyjSyMqa"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== DATABASE CLASS ====================
class Database:
    def __init__(self):
        self.conn = None
        self.connect()
    
    def connect(self):
        try:
            self.conn = pg8000.connect(
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                database=DB_NAME,
                timeout=30
            )
            self.conn.autocommit = True  # IMPORTANT: Auto-commit mode
            print("✅ Database connected successfully!")
            self.init_tables()
        except Exception as e:
            print(f"❌ DB Error: {e}")
            time.sleep(5)
            self.connect()
    
    def init_tables(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    token TEXT,
                    token_activated_at TIMESTAMP,
                    token_expires_at TIMESTAMP,
                    device_id TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tokens (
                    token TEXT PRIMARY KEY,
                    created_by BIGINT,
                    device_limit INTEGER,
                    hours INTEGER,
                    used_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT NOW(),
                    expiry_time TIMESTAMP,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS token_usage (
                    id SERIAL PRIMARY KEY,
                    token TEXT,
                    user_id BIGINT,
                    device_id TEXT,
                    used_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos_cache (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    link TEXT,
                    fetched_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            cursor.execute("INSERT INTO settings (key, value) VALUES ('free_token_link', 'https://t.me/latestvideo10') ON CONFLICT (key) DO NOTHING")
            self.conn.commit()
            print("✅ Tables ready!")
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Table creation error: {e}")
    
    def execute_query(self, query, params=None):
        """Execute query with proper transaction handling"""
        cursor = self.conn.cursor()
        try:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            self.conn.commit()
            return cursor
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Query error: {e}")
            raise e
    
    def fetch_one(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchone()
    
    def fetch_all(self, query, params=None):
        cursor = self.execute_query(query, params)
        return cursor.fetchall()
    
    def create_user(self, user_id, username, first_name):
        try:
            self.execute_query('''
                INSERT INTO users (user_id, username, first_name, created_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id) DO NOTHING
            ''', (user_id, username, first_name))
        except Exception as e:
            print(f"❌ create_user error: {e}")
    
    def create_token(self, token, created_by, hours, device_limit):
        try:
            expiry = datetime.now() + timedelta(hours=hours)
            self.execute_query('''
                INSERT INTO tokens (token, created_by, device_limit, hours, created_at, expiry_time, is_active)
                VALUES (%s, %s, %s, %s, NOW(), %s, 1)
            ''', (token, created_by, device_limit, hours, expiry))
        except Exception as e:
            print(f"❌ create_token error: {e}")
    
    def redeem_token(self, token, user_id, device_id):
        token = token.upper().strip()
        try:
            cursor = self.conn.cursor()
            
            cursor.execute('SELECT token, device_limit, used_count, hours, expiry_time, is_active FROM tokens WHERE token = %s', (token,))
            result = cursor.fetchone()
            
            if not result:
                self.conn.commit()
                return False, "❌ Invalid token", 0
            
            token_val, device_limit, used_count, hours, expiry_time, is_active = result
            
            if not is_active:
                self.conn.commit()
                return False, "❌ Token expired", 0
            
            if datetime.now() > expiry_time:
                cursor.execute('UPDATE tokens SET is_active = 0 WHERE token = %s', (token,))
                self.conn.commit()
                return False, "❌ Token expired", 0
            
            if used_count >= device_limit:
                self.conn.commit()
                return False, f"❌ Device limit reached ({device_limit})", 0
            
            cursor.execute('SELECT is_active, token_expires_at FROM users WHERE user_id = %s', (user_id,))
            user_result = cursor.fetchone()
            if user_result:
                is_active_user, expires_at = user_result
                if is_active_user and expires_at:
                    if datetime.now() < expires_at:
                        self.conn.commit()
                        return False, "❌ You already have an active token", 0
            
            cursor.execute('UPDATE tokens SET used_count = used_count + 1 WHERE token = %s', (token,))
            cursor.execute('INSERT INTO token_usage (token, user_id, device_id, used_at) VALUES (%s, %s, %s, NOW())', (token, user_id, device_id))
            
            expiry = datetime.now() + timedelta(hours=hours)
            cursor.execute('''
                UPDATE users 
                SET token = %s, token_activated_at = NOW(), token_expires_at = %s, device_id = %s, is_active = 1
                WHERE user_id = %s
            ''', (token, expiry, device_id, user_id))
            
            self.conn.commit()
            return True, f"✅ Token redeemed! {hours} hours added.", hours
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ redeem_token error: {e}")
            return False, f"❌ Error: {str(e)}", 0
    
    def check_user_active(self, user_id):
        try:
            result = self.fetch_one('SELECT token_expires_at, is_active FROM users WHERE user_id = %s', (user_id,))
            if not result or not result[1] or not result[0]:
                return False
            return datetime.now() < result[0]
        except Exception as e:
            print(f"❌ check_user_active error: {e}")
            return False
    
    def get_user_token(self, user_id):
        try:
            return self.fetch_one('SELECT token, token_activated_at, token_expires_at, device_id FROM users WHERE user_id = %s', (user_id,))
        except Exception as e:
            print(f"❌ get_user_token error: {e}")
            return None
    
    def get_all_tokens(self):
        try:
            return self.fetch_all('SELECT * FROM tokens ORDER BY created_at DESC')
        except Exception as e:
            print(f"❌ get_all_tokens error: {e}")
            return []
    
    def get_setting(self, key):
        try:
            result = self.fetch_one('SELECT value FROM settings WHERE key = %s', (key,))
            return result[0] if result else None
        except Exception as e:
            print(f"❌ get_setting error: {e}")
            return None
    
    def set_setting(self, key, value):
        try:
            self.execute_query('UPDATE settings SET value = %s WHERE key = %s', (value, key))
        except Exception as e:
            print(f"❌ set_setting error: {e}")

# ==================== INIT DATABASE ====================
print("[*] Connecting to database...")
db = Database()
print("[*] Database ready!")

# ==================== VIDEO FETCHER ====================
def fetch_channel_videos(limit=10):
    videos = []
    try:
        import requests
        import re
        url = "https://t.me/s/latestvideo10"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            html = response.text
            pattern = r'<a class="tgme_widget_message_date" href="/([^"]+)"'
            matches = re.findall(pattern, html)
            title_pattern = r'<div class="tgme_widget_message_text[^"]*">([^<]+)</div>'
            titles = re.findall(title_pattern, html)
            
            for i in range(min(limit, len(matches))):
                link = f"https://t.me/{matches[i]}" if i < len(matches) else ""
                title = titles[i].replace('<b>', '').replace('</b>', '').strip()[:50] if i < len(titles) else f"Video {i+1}"
                videos.append({'title': title, 'link': link})
        
        if not videos:
            videos = [{'title': f'Latest Video {i+1}', 'link': f'https://t.me/latestvideo10/{i+1}'} for i in range(limit)]
        
        return videos
    except Exception as e:
        print(f"❌ Video fetch error: {e}")
        return [{'title': f'Video {i+1}', 'link': f'https://t.me/latestvideo10/{i+1}'} for i in range(limit)]

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "User"
    db.create_user(user_id, username, first_name)
    
    if user_id == OWNER_ID:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔑 Create Token", callback_data="owner_create"),
            types.InlineKeyboardButton("📋 My Tokens", callback_data="owner_tokens"),
            types.InlineKeyboardButton("🔗 Change Free Link", callback_data="owner_link"),
            types.InlineKeyboardButton("📹 Latest Videos", callback_data="owner_videos")
        )
        bot.reply_to(message, "👑 **WELCOME BOSS!**\n\nSelect an option:", reply_markup=markup, parse_mode='Markdown')
        return
    
    if db.check_user_active(user_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📹 Latest Videos", callback_data="user_videos"),
            types.InlineKeyboardButton("📊 My Token", callback_data="user_token")
        )
        bot.reply_to(message, "✅ **ACCESS GRANTED**\n\nSelect an option:", reply_markup=markup, parse_mode='Markdown')
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        link = db.get_setting('free_token_link') or 'https://t.me/latestvideo10'
        markup.add(
            types.InlineKeyboardButton("🔑 Redeem Token", callback_data="user_redeem"),
            types.InlineKeyboardButton("🎁 Get Free Token", url=link)
        )
        bot.reply_to(message, "🔐 **TOKEN LOGIN**\n\nUse /redeem [TOKEN] to login.", reply_markup=markup, parse_mode='Markdown')

# ===== OWNER COMMANDS =====

@bot.message_handler(commands=['create'])
def create_token(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only.")
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        bot.reply_to(message, "❌ /create [HOURS] [DEVICE_LIMIT]\nExample: /create 24 100")
        return
    
    try:
        hours = int(parts[1])
        device_limit = int(parts[2])
    except:
        bot.reply_to(message, "❌ Enter valid numbers.")
        return
    
    token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    db.create_token(token, OWNER_ID, hours, device_limit)
    
    bot.reply_to(message, 
        f"✅ **TOKEN CREATED!**\n\n"
        f"🔑 Token: `{token}`\n"
        f"⏱ Hours: {hours}\n"
        f"🖥 Device Limit: {device_limit}\n\n"
        f"User can redeem with:\n`/redeem {token}`",
        parse_mode='Markdown')

@bot.message_handler(commands=['change'])
def change_link(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ /change [LINK]\nExample: /change https://t.me/newchannel")
        return
    
    db.set_setting('free_token_link', parts[1].strip())
    bot.reply_to(message, f"✅ Free token link updated!")

@bot.message_handler(commands=['tokens'])
def list_tokens(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only.")
        return
    
    tokens = db.get_all_tokens()
    if not tokens:
        bot.reply_to(message, "📌 No tokens created.")
        return
    
    text = "📋 **TOKENS**\n\n"
    for t in tokens:
        status = "✅ Active" if t[7] else "❌ Expired"
        text += f"🔑 `{t[0]}` - {t[3]}h - {t[4]}/{t[2]} used - {status}\n"
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ===== USER COMMANDS =====

@bot.message_handler(commands=['redeem'])
def redeem_token(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ /redeem [TOKEN]\nExample: /redeem ABC123XYZ789")
        return
    
    token = parts[1].strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    success, msg, hours = db.redeem_token(token, user_id, device_id)
    bot.reply_to(message, msg)
    if success:
        start(message)

@bot.message_handler(commands=['tokeninfo'])
def token_info(message):
    user_id = message.from_user.id
    
    if not db.check_user_active(user_id):
        bot.reply_to(message, "❌ No active token.")
        return
    
    info = db.get_user_token(user_id)
    if info:
        token, activated, expires, device = info
        remaining = expires - datetime.now() if expires else None
        if remaining and remaining.total_seconds() > 0:
            time_str = f"{int(remaining.total_seconds() // 3600)}h {int((remaining.total_seconds() % 3600) // 60)}m"
            status = "✅ Active"
        else:
            time_str = "Expired"
            status = "❌ Expired"
        
        bot.reply_to(message, f"📊 **TOKEN INFO**\n\n🔑 Token: `{token}`\n⏱ Remaining: {time_str}\n📌 Status: {status}", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ No token info.")

@bot.message_handler(commands=['videos'])
def get_videos(message):
    user_id = message.from_user.id
    
    if not db.check_user_active(user_id):
        bot.reply_to(message, "❌ No active token.")
        return
    
    loading = bot.reply_to(message, "⏳ Fetching videos...")
    videos = fetch_channel_videos(10)
    
    if not videos:
        bot.edit_message_text("❌ No videos found.", chat_id=message.chat.id, message_id=loading.message_id)
        return
    
    text = "📹 **LATEST VIDEOS**\n\n"
    for i, video in enumerate(videos, 1):
        text += f"{i}. {video['title']}\n"
        if video.get('link'):
            text += f"   🔗 {video['link']}\n"
    
    text += f"\n📌 [@latestvideo10](https://t.me/latestvideo10)"
    bot.edit_message_text(text, chat_id=message.chat.id, message_id=loading.message_id, parse_mode='Markdown')

# ===== CALLBACKS =====

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "owner_create":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📌 /create [HOURS] [LIMIT]")
    
    elif call.data == "owner_tokens":
        bot.answer_callback_query(call.id)
        list_tokens(call.message)
    
    elif call.data == "owner_link":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📌 /change [LINK]")
    
    elif call.data == "owner_videos":
        bot.answer_callback_query(call.id)
        get_videos(call.message)
    
    elif call.data == "user_redeem":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔑 Enter token:")
        bot.register_next_step_handler(call.message, process_redeem)
    
    elif call.data == "user_videos":
        bot.answer_callback_query(call.id)
        get_videos(call.message)
    
    elif call.data == "user_token":
        bot.answer_callback_query(call.id)
        token_info(call.message)

def process_redeem(message):
    token = message.text.strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    success, msg, hours = db.redeem_token(token, user_id, device_id)
    bot.reply_to(message, msg)
    if success:
        start(message)

@bot.message_handler(commands=['help'])
def help_command(message):
    if message.from_user.id == OWNER_ID:
        text = "👑 **OWNER HELP**\n\n/create [HOURS] [LIMIT]\n/tokens\n/change [LINK]\n/videos"
    else:
        text = "🔹 **USER HELP**\n\n/redeem [TOKEN]\n/videos\n/tokeninfo"
    bot.reply_to(message, text, parse_mode='Markdown')

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    bot.reply_to(message, "❓ Use /start")

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   📹 TOKEN VIDEO BOT - TRANSACTION FIXED                    ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Database: Connected")
    print(f"✅ Bot starting...")
    
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=10)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()
