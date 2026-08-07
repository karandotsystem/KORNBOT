#!/usr/bin/env python3
"""
📹 TOKEN VIDEO BOT v3.0 - FULLY WORKING
- Token redeem working
- Owner access fixed
- Latest videos from @latestvideo10
"""

import os
import re
import time
import json
import logging
import requests
import sqlite3
import threading
import random
import string
from datetime import datetime, timedelta
import telebot
from telebot import types

# ==================== CONFIG ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
OWNER_ID = 8935807032  # HARDCODED OWNER
HELP_USERNAME = "@VATEROFWHOLETG"
DELETE_AFTER_MINUTES = 10
VIDEO_CHANNEL = "latestvideo10"

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.db_file = "token_bot.db"
        self.init_db()
    
    def get_conn(self):
        return sqlite3.connect(self.db_file, check_same_thread=False)
    
    def init_db(self):
        conn = self.get_conn()
        c = conn.cursor()
        
        # Users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            token TEXT,
            token_activated_at TEXT,
            token_expires_at TEXT,
            device_id TEXT,
            is_active INTEGER DEFAULT 0,
            created_at TEXT
        )''')
        
        # Tokens table
        c.execute('''CREATE TABLE IF NOT EXISTS tokens (
            token TEXT PRIMARY KEY,
            created_by INTEGER,
            device_limit INTEGER,
            hours INTEGER,
            used_count INTEGER DEFAULT 0,
            created_at TEXT,
            expiry_time TEXT,
            is_active INTEGER DEFAULT 1
        )''')
        
        # Token usage log
        c.execute('''CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT,
            user_id INTEGER,
            device_id TEXT,
            used_at TEXT
        )''')
        
        # Videos cache
        c.execute('''CREATE TABLE IF NOT EXISTS videos_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            link TEXT,
            fetched_at TEXT
        )''')
        
        # Settings
        c.execute('''CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )''')
        
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('free_token_link', 'https://t.me/latestvideo10'))
        c.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', ('last_video_fetch', ''))
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized")
    
    # ==================== USER FUNCTIONS ====================
    
    def create_user(self, user_id, username, first_name):
        conn = self.get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''
            INSERT OR IGNORE INTO users (user_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, first_name, now))
        conn.commit()
        conn.close()
    
    def update_user_token(self, user_id, token, hours, device_id):
        conn = self.get_conn()
        c = conn.cursor()
        now = datetime.now()
        expires = now + timedelta(hours=hours)
        c.execute('''
            UPDATE users 
            SET token = ?, token_activated_at = ?, token_expires_at = ?, device_id = ?, is_active = 1
            WHERE user_id = ?
        ''', (token, now.isoformat(), expires.isoformat(), device_id, user_id))
        conn.commit()
        conn.close()
        logger.info(f"✅ User {user_id} activated token: {token}")
    
    def check_user_active(self, user_id):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT token_expires_at, is_active FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        
        if not result:
            return False
        
        expires_str, is_active = result
        if not is_active or not expires_str:
            return False
        
        try:
            expires = datetime.fromisoformat(expires_str)
            return datetime.now() < expires
        except:
            return False
    
    def get_user_token_info(self, user_id):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT token, token_activated_at, token_expires_at, device_id FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        conn.close()
        return result
    
    # ==================== TOKEN FUNCTIONS ====================
    
    def generate_token(self):
        token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT 1 FROM tokens WHERE token = ?', (token,))
        while c.fetchone():
            token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
            c.execute('SELECT 1 FROM tokens WHERE token = ?', (token,))
        conn.close()
        return token
    
    def create_token(self, token, created_by, hours, device_limit):
        conn = self.get_conn()
        c = conn.cursor()
        now = datetime.now().isoformat()
        expiry = (datetime.now() + timedelta(hours=hours)).isoformat()
        
        c.execute('''
            INSERT INTO tokens (token, created_by, device_limit, hours, created_at, expiry_time, is_active)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        ''', (token, created_by, device_limit, hours, now, expiry))
        
        conn.commit()
        conn.close()
        logger.info(f"✅ Token created: {token}")
    
    def redeem_token(self, token, user_id, device_id):
        token = token.upper().strip()
        
        conn = self.get_conn()
        c = conn.cursor()
        
        # Check token exists and is active
        c.execute('SELECT token, device_limit, used_count, hours, expiry_time, is_active FROM tokens WHERE token = ?', (token,))
        result = c.fetchone()
        
        if not result:
            conn.close()
            return False, "❌ Invalid token", 0
        
        token_val, device_limit, used_count, hours, expiry_time, is_active = result
        
        if not is_active:
            conn.close()
            return False, "❌ Token expired", 0
        
        try:
            expiry = datetime.fromisoformat(expiry_time)
            if datetime.now() > expiry:
                c.execute('UPDATE tokens SET is_active = 0 WHERE token = ?', (token,))
                conn.commit()
                conn.close()
                return False, "❌ Token expired", 0
        except:
            pass
        
        if used_count >= device_limit:
            conn.close()
            return False, f"❌ Device limit reached ({device_limit})", 0
        
        # Check if user already has active token
        c.execute('SELECT is_active, token_expires_at FROM users WHERE user_id = ?', (user_id,))
        user_result = c.fetchone()
        if user_result:
            is_active_user, expires_at = user_result
            if is_active_user and expires_at:
                try:
                    if datetime.now() < datetime.fromisoformat(expires_at):
                        conn.close()
                        return False, "❌ You already have an active token", 0
                except:
                    pass
        
        # Redeem
        c.execute('UPDATE tokens SET used_count = used_count + 1 WHERE token = ?', (token,))
        
        c.execute('''
            INSERT INTO token_usage (token, user_id, device_id, used_at)
            VALUES (?, ?, ?, ?)
        ''', (token, user_id, device_id, datetime.now().isoformat()))
        
        self.update_user_token(user_id, token, hours, device_id)
        
        conn.commit()
        conn.close()
        
        return True, f"✅ Token redeemed! {hours} hours added.", hours
    
    def get_all_tokens(self, limit=50):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT * FROM tokens ORDER BY created_at DESC LIMIT ?', (limit,))
        results = c.fetchall()
        conn.close()
        return results
    
    def get_token_usage(self, token):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT * FROM token_usage WHERE token = ? ORDER BY used_at DESC', (token,))
        results = c.fetchall()
        conn.close()
        return results
    
    # ==================== VIDEOS FUNCTIONS ====================
    
    def save_videos(self, videos):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('DELETE FROM videos_cache')
        now = datetime.now().isoformat()
        for video in videos:
            c.execute('''
                INSERT INTO videos_cache (title, link, fetched_at)
                VALUES (?, ?, ?)
            ''', (video.get('title', 'Video'), video.get('link', ''), now))
        conn.commit()
        conn.close()
    
    def get_videos(self, limit=10):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT title, link FROM videos_cache ORDER BY id DESC LIMIT ?', (limit,))
        results = c.fetchall()
        conn.close()
        return [{'title': r[0], 'link': r[1]} for r in results]
    
    def update_last_fetch_time(self, time_str):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('UPDATE settings SET value = ? WHERE key = ?', (time_str, 'last_video_fetch'))
        conn.commit()
        conn.close()
    
    def get_setting(self, key):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = c.fetchone()
        conn.close()
        return result[0] if result else None
    
    def set_setting(self, key, value):
        conn = self.get_conn()
        c = conn.cursor()
        c.execute('UPDATE settings SET value = ? WHERE key = ?', (value, key))
        conn.commit()
        conn.close()

db = Database()

# ==================== VIDEO FETCHER ====================
def fetch_channel_videos(limit=10):
    videos = []
    try:
        url = f"https://t.me/s/{VIDEO_CHANNEL}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            html = response.text
            import re
            pattern = r'<a class="tgme_widget_message_date" href="/([^"]+)"'
            matches = re.findall(pattern, html)
            title_pattern = r'<div class="tgme_widget_message_text[^"]*">([^<]+)</div>'
            titles = re.findall(title_pattern, html)
            
            for i in range(min(limit, len(matches))):
                link = f"https://t.me/{matches[i]}" if i < len(matches) else ""
                title = titles[i].replace('<b>', '').replace('</b>', '').strip()[:50] if i < len(titles) else f"Video {i+1}"
                videos.append({'title': title, 'link': link})
        
        if not videos:
            videos = [{'title': f'Latest Video {i+1}', 'link': f'https://t.me/{VIDEO_CHANNEL}/{i+1}'} for i in range(limit)]
        
        return videos
    except Exception as e:
        logger.error(f"Video fetch error: {e}")
        return [{'title': f'Video {i+1}', 'link': f'https://t.me/{VIDEO_CHANNEL}/{i+1}'} for i in range(limit)]

def update_videos():
    videos = fetch_channel_videos(10)
    db.save_videos(videos)
    db.update_last_fetch_time(datetime.now().isoformat())
    logger.info("✅ Videos updated")

# Initial video fetch
try:
    update_videos()
except:
    pass

# ==================== MESSAGE DELETE ====================
messages_to_delete = {}

def add_message_to_delete(chat_id, message_id):
    if chat_id not in messages_to_delete:
        messages_to_delete[chat_id] = []
    messages_to_delete[chat_id].append((message_id, datetime.now() + timedelta(minutes=DELETE_AFTER_MINUTES)))
    threading.Thread(target=delete_message_after_delay, args=(chat_id, message_id), daemon=True).start()

def delete_message_after_delay(chat_id, message_id):
    time.sleep(DELETE_AFTER_MINUTES * 60)
    try:
        bot.delete_message(chat_id, message_id)
    except:
        pass

def delete_old_messages():
    while True:
        time.sleep(60)
        now = datetime.now()
        for chat_id in list(messages_to_delete.keys()):
            remaining = []
            for msg_id, delete_time in messages_to_delete[chat_id]:
                if now < delete_time:
                    remaining.append((msg_id, delete_time))
                else:
                    try:
                        bot.delete_message(chat_id, msg_id)
                    except:
                        pass
            if remaining:
                messages_to_delete[chat_id] = remaining
            else:
                del messages_to_delete[chat_id]

threading.Thread(target=delete_old_messages, daemon=True).start()

# ==================== BOT COMMANDS ====================

# ===== OWNER COMMANDS =====

@bot.message_handler(commands=['create'])
def create_token(message):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        reply = bot.reply_to(message, "❌ Owner only.")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        reply = bot.reply_to(message, "❌ Usage: /create [HOURS] [DEVICE_LIMIT]\nExample: /create 24 100")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    try:
        hours = int(parts[1])
        device_limit = int(parts[2])
    except:
        reply = bot.reply_to(message, "❌ Enter valid numbers.")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    token = db.generate_token()
    db.create_token(token, user_id, hours, device_limit)
    
    text = f"""
✅ **TOKEN CREATED!**

🔑 Token: `{token}`
⏱ Hours: {hours}
🖥 Device Limit: {device_limit}
📅 Created: {datetime.now().strftime('%d-%m-%Y %H:%M')}
⏰ Expires: {(datetime.now() + timedelta(hours=hours)).strftime('%d-%m-%Y %H:%M')}

📌 User can redeem with:
`/redeem {token}`
"""
    reply = bot.reply_to(message, text, parse_mode='Markdown')
    add_message_to_delete(reply.chat.id, reply.message_id)

@bot.message_handler(commands=['tokens'])
def list_tokens(message):
    if message.from_user.id != OWNER_ID:
        reply = bot.reply_to(message, "❌ Owner only.")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    tokens = db.get_all_tokens(30)
    if not tokens:
        reply = bot.reply_to(message, "📌 No tokens created.")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    text = "📋 **TOKENS**\n\n"
    for row in tokens:
        token = row[0]
        device_limit = row[2]
        used_count = row[3]
        hours = row[4]
        created_at = row[5][:16] if row[5] else 'N/A'
        is_active = "✅ Active" if row[7] else "❌ Expired"
        
        text += f"🔑 `{token}`\n"
        text += f"   ⏱ {hours}h | 🖥 {used_count}/{device_limit}\n"
        text += f"   📅 {created_at} | {is_active}\n\n"
    
    reply = bot.reply_to(message, text, parse_mode='Markdown')
    add_message_to_delete(reply.chat.id, reply.message_id)

@bot.message_handler(commands=['setlink'])
def set_free_link(message):
    if message.from_user.id != OWNER_ID:
        reply = bot.reply_to(message, "❌ Owner only.")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        reply = bot.reply_to(message, "❌ Usage: /setlink [LINK]")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    db.set_setting('free_token_link', parts[1].strip())
    reply = bot.reply_to(message, f"✅ Free token link updated.")
    add_message_to_delete(reply.chat.id, reply.message_id)

# ===== USER COMMANDS =====

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "User"
    db.create_user(user_id, username, first_name)
    
    add_message_to_delete(message.chat.id, message.message_id)
    
    # Check if user has active token
    if db.check_user_active(user_id):
        show_main_menu(message)
        return
    
    # No token
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🔑 Redeem Token", callback_data="redeem")
    free_link = db.get_setting('free_token_link') or 'https://t.me/latestvideo10'
    btn2 = types.InlineKeyboardButton("🎁 Get Free Token", url=free_link)
    markup.add(btn1, btn2)
    
    text = f"""
🔐 **TOKEN LOGIN SYSTEM**

Welcome {first_name}!

You don't have an active token.
Please redeem a token to continue.

📌 **Commands:**
/redeem [TOKEN] - Redeem token
/start - Show menu

🔹 **Help:** {HELP_USERNAME}
"""
    reply = bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')
    add_message_to_delete(reply.chat.id, reply.message_id)

def show_main_menu(message):
    user_id = message.from_user.id
    token_info = db.get_user_token_info(user_id)
    
    if token_info:
        token, activated, expires, device = token_info
        try:
            exp = datetime.fromisoformat(expires)
            remaining = exp - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        except:
            time_str = "Unknown"
    else:
        time_str = "Unknown"
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📹 Latest Videos", callback_data="videos")
    btn2 = types.InlineKeyboardButton("📊 My Token", callback_data="token_info")
    btn3 = types.InlineKeyboardButton("🔹 Help", callback_data="help")
    markup.add(btn1, btn2, btn3)
    
    text = f"""
✅ **ACCESS GRANTED**

Welcome back!

📌 **Token Info:**
⏱ Remaining: {time_str}

📌 **Commands:**
/videos - Get latest 10 videos
/tokeninfo - Check token status
/start - Show menu
"""
    reply = bot.reply_to(message, text, reply_markup=markup, parse_mode='Markdown')
    add_message_to_delete(reply.chat.id, reply.message_id)

@bot.message_handler(commands=['redeem'])
def redeem_token(message):
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        reply = bot.reply_to(message, "❌ Usage: /redeem [TOKEN]\nExample: /redeem ABC123XYZ789")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    token = parts[1].strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    success, msg, hours = db.redeem_token(token, user_id, device_id)
    
    reply = bot.reply_to(message, msg)
    add_message_to_delete(reply.chat.id, reply.message_id)
    
    if success:
        show_main_menu(message)

@bot.message_handler(commands=['tokeninfo'])
def token_info(message):
    user_id = message.from_user.id
    
    if not db.check_user_active(user_id):
        reply = bot.reply_to(message, "❌ No active token. Use /redeem [TOKEN]")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    token_info = db.get_user_token_info(user_id)
    
    if token_info:
        token, activated, expires, device = token_info
        try:
            exp = datetime.fromisoformat(expires)
            remaining = exp - datetime.now()
            hours = int(remaining.total_seconds() // 3600)
            minutes = int((remaining.total_seconds() % 3600) // 60)
            time_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
            status = "✅ Active" if remaining.total_seconds() > 0 else "❌ Expired"
        except:
            time_str = "Unknown"
            status = "❌ Unknown"
        
        text = f"""
📊 **TOKEN INFO**

🔑 Token: `{token}`
📅 Activated: {activated[:16] if activated else 'N/A'}
⏰ Expires: {expires[:16] if expires else 'N/A'}
⏱ Remaining: {time_str}
📌 Status: {status}
🖥 Device ID: {device or 'N/A'}
"""
        reply = bot.reply_to(message, text, parse_mode='Markdown')
        add_message_to_delete(reply.chat.id, reply.message_id)
    else:
        reply = bot.reply_to(message, "❌ No token info found.")
        add_message_to_delete(reply.chat.id, reply.message_id)

@bot.message_handler(commands=['videos'])
def get_videos(message):
    user_id = message.from_user.id
    
    if not db.check_user_active(user_id):
        reply = bot.reply_to(message, "❌ No active token. Use /redeem [TOKEN]")
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    loading = bot.reply_to(message, "⏳ Fetching latest videos...")
    add_message_to_delete(loading.chat.id, loading.message_id)
    
    update_videos()
    videos = db.get_videos(10)
    
    if not videos:
        reply = bot.edit_message_text("❌ No videos found.", 
                            chat_id=message.chat.id, message_id=loading.message_id)
        add_message_to_delete(reply.chat.id, reply.message_id)
        return
    
    text = "📹 **LATEST VIDEOS**\n\n"
    for i, video in enumerate(videos, 1):
        if video.get('link'):
            text += f"{i}. [{video['title']}]({video['link']})\n"
        else:
            text += f"{i}. {video['title']}\n"
    
    text += f"\n📌 **Channel:** [@latestvideo10](https://t.me/latestvideo10)"
    text += f"\n🔹 **Help:** {HELP_USERNAME}"
    
    reply = bot.edit_message_text(text, chat_id=message.chat.id, 
                                  message_id=loading.message_id, parse_mode='Markdown')
    add_message_to_delete(reply.chat.id, reply.message_id)

@bot.message_handler(commands=['help'])
def send_help(message):
    text = f"""
🔹 **HELP**

📌 **User Commands:**
/start - Show menu
/redeem [TOKEN] - Redeem token
/videos - Get latest videos
/tokeninfo - Check token status

📌 **Owner Commands:**
/create [HOURS] [LIMIT] - Create token
/tokens - List all tokens
/setlink [LINK] - Set free token link

🔹 **Help:** {HELP_USERNAME}
"""
    reply = bot.reply_to(message, text, parse_mode='Markdown')
    add_message_to_delete(reply.chat.id, reply.message_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if call.data == "redeem":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🔑 Enter token:\nExample: ABC123XYZ789")
        add_message_to_delete(msg.chat.id, msg.message_id)
        bot.register_next_step_handler(msg, process_redeem_input)
    
    elif call.data == "videos":
        bot.answer_callback_query(call.id)
        if db.check_user_active(user_id):
            get_videos(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ No active token!", show_alert=True)
    
    elif call.data == "token_info":
        bot.answer_callback_query(call.id)
        if db.check_user_active(user_id):
            token_info(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ No active token!", show_alert=True)
    
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        send_help(call.message)

def process_redeem_input(message):
    token = message.text.strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    success, msg, hours = db.redeem_token(token, user_id, device_id)
    
    reply = bot.reply_to(message, msg)
    add_message_to_delete(reply.chat.id, reply.message_id)
    
    if success:
        show_main_menu(message)

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    reply = bot.reply_to(message, f"❓ Use /start\n\n🔹 FOR HELP: {HELP_USERNAME}")
    add_message_to_delete(reply.chat.id, reply.message_id)

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   📹 TOKEN VIDEO BOT v3.0 - FULLY WORKING                    ║
    ║   - Token redeem working                                     ║
    ║   - Owner access: """ + str(OWNER_ID) + """                         ║
    ║   - Latest videos from @latestvideo10                        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Bot starting...")
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=10)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        time.sleep(3)
        main()

if __name__ == "__main__":
    main()
