#!/usr/bin/env python3
"""
📹 TOKEN VIDEO BOT - FIRST VIDEO FIXED
"""

import os
import time
import logging
import random
import string
import pg8000
import requests
import re
import threading
from datetime import datetime, timedelta
import telebot
from telebot import types

# ==================== CONFIG ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
OWNER_ID = 8935807032
VIDEO_CHANNEL = "latestvideo10"
DELETE_AFTER_MINUTES = 10

# ==================== DATABASE CONNECTION ====================
DB_HOST = "reseau.proxy.rlwy.net"
DB_PORT = 29905
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASSWORD = "dOkCcwkemyQRRXGnyOGBwlJloyjSyMqa"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
    print("✅ Webhook removed")
except:
    pass

# ==================== MESSAGE DELETE TRACKER ====================
messages_to_delete = {}

def add_message_to_delete(chat_id, message_id, delay_minutes=DELETE_AFTER_MINUTES):
    if chat_id not in messages_to_delete:
        messages_to_delete[chat_id] = []
    delete_time = datetime.now() + timedelta(minutes=delay_minutes)
    messages_to_delete[chat_id].append((message_id, delete_time))
    threading.Thread(target=delete_message_after_delay, args=(chat_id, message_id, delay_minutes), daemon=True).start()

def delete_message_after_delay(chat_id, message_id, delay_minutes):
    time.sleep(delay_minutes * 60)
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
            self.conn.autocommit = True
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
                CREATE TABLE IF NOT EXISTS sent_videos (
                    id SERIAL PRIMARY KEY,
                    video_id TEXT,
                    sent_to INTEGER,
                    sent_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            cursor.execute("INSERT INTO settings (key, value) VALUES ('free_token_link', 'https://t.me/latestvideo10') ON CONFLICT (key) DO NOTHING")
            cursor.execute("INSERT INTO settings (key, value) VALUES ('last_video_id', '') ON CONFLICT (key) DO NOTHING")
            self.conn.commit()
            print("✅ Tables ready!")
        except Exception as e:
            self.conn.rollback()
            print(f"❌ Table creation error: {e}")
    
    def execute_query(self, query, params=None):
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
            print(f"✅ Token stored in DB: {token}")
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
            print(f"✅ Token redeemed: {token} by user {user_id}")
            return True, f"✅ Token redeemed! {hours} hours added.", hours
            
        except Exception as e:
            self.conn.rollback()
            print(f"❌ redeem_token error: {e}")
            return False, f"❌ Error: {str(e)}", 0
    
    def check_user_active(self, user_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT is_active, token_expires_at FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            self.conn.commit()
            
            if not result:
                return False
            
            is_active, expires_at = result
            
            if is_active != 1:
                return False
            
            if not expires_at:
                return False
            
            return datetime.now() < expires_at
            
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
    
    def mark_video_sent(self, video_id, user_id):
        try:
            self.execute_query('''
                INSERT INTO sent_videos (video_id, sent_to, sent_at)
                VALUES (%s, %s, NOW())
            ''', (video_id, user_id))
        except Exception as e:
            print(f"❌ mark_video_sent error: {e}")
    
    def is_video_sent(self, video_id, user_id):
        try:
            result = self.fetch_one('SELECT id FROM sent_videos WHERE video_id = %s AND sent_to = %s', (video_id, user_id))
            return result is not None
        except Exception as e:
            print(f"❌ is_video_sent error: {e}")
            return False
    
    def get_last_video_id(self):
        result = self.fetch_one('SELECT value FROM settings WHERE key = %s', ('last_video_id',))
        return result[0] if result else None
    
    def set_last_video_id(self, video_id):
        self.set_setting('last_video_id', video_id)

# ==================== INIT DATABASE ====================
db = Database()
print("[*] Database ready!")

# ==================== VIDEO FETCHER ====================
def get_channel_videos(limit=10):
    """Get latest video links from channel"""
    videos = []
    try:
        url = f"https://t.me/s/{VIDEO_CHANNEL}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            html = response.text
            
            pattern = r'<a class="tgme_widget_message_date" href="/([^"]+)"'
            matches = re.findall(pattern, html)
            
            title_pattern = r'<div class="tgme_widget_message_text[^"]*">([^<]+)</div>'
            titles = re.findall(title_pattern, html)
            
            has_media_pattern = r'class="tgme_widget_message_photo_wrap"'
            has_media = re.findall(has_media_pattern, html)
            
            for i in range(min(limit, len(matches))):
                link = f"https://t.me/{matches[i]}" if i < len(matches) else ""
                title = titles[i].replace('<b>', '').replace('</b>', '').strip()[:50] if i < len(titles) else f"Video {i+1}"
                video_id = matches[i] if i < len(matches) else f"video_{i}"
                has_video = i < len(has_media)
                videos.append({
                    'title': title,
                    'link': link,
                    'video_id': video_id,
                    'has_video': has_video
                })
        
        if not videos:
            for i in range(limit):
                videos.append({
                    'title': f'Video {i+1}',
                    'link': f'https://t.me/{VIDEO_CHANNEL}/{i+1}',
                    'video_id': f'video_{i+1}',
                    'has_video': True
                })
        
        return videos
    except Exception as e:
        print(f"❌ Video fetch error: {e}")
        return [{'title': f'Video {i+1}', 'link': f'https://t.me/{VIDEO_CHANNEL}/{i+1}', 'video_id': f'video_{i+1}', 'has_video': True} for i in range(limit)]

def send_videos_to_user(chat_id, user_id):
    """Send latest videos directly to user - FIXED"""
    is_active = db.check_user_active(user_id)
    
    if not is_active:
        msg = bot.send_message(chat_id, "❌ No active token. Use /redeem [TOKEN]")
        add_message_to_delete(chat_id, msg.message_id)
        return
    
    loading = bot.send_message(chat_id, "📹 Fetching latest videos...")
    add_message_to_delete(chat_id, loading.message_id)
    
    videos = get_channel_videos(10)
    
    if not videos:
        msg = bot.edit_message_text("❌ No videos found.", chat_id=chat_id, message_id=loading.message_id)
        add_message_to_delete(chat_id, msg.message_id)
        return
    
    # Filter new videos
    new_videos = []
    for v in videos:
        if not db.is_video_sent(v['video_id'], user_id):
            new_videos.append(v)
    
    if not new_videos:
        msg = bot.edit_message_text("✅ No new videos available.", chat_id=chat_id, message_id=loading.message_id)
        add_message_to_delete(chat_id, msg.message_id)
        return
    
    msg = bot.edit_message_text("📹 **Sending videos...**", chat_id=chat_id, message_id=loading.message_id, parse_mode='Markdown')
    add_message_to_delete(chat_id, msg.message_id)
    
    for i, video in enumerate(new_videos[:10], 1):
        try:
            caption = f"📹 Video {i}\n{video['title']}"
            
            # DIRECT VIDEO SEND - With retry
            video_msg = None
            for attempt in range(3):
                try:
                    # Try sending as video directly
                    video_msg = bot.send_video(
                        chat_id, 
                        video['link'], 
                        caption=caption, 
                        supports_streaming=True,
                        timeout=30
                    )
                    break
                except Exception as e:
                    print(f"❌ Attempt {attempt+1} failed for video {i}: {e}")
                    time.sleep(2)
            
            if video_msg:
                add_message_to_delete(chat_id, video_msg.message_id)
                db.mark_video_sent(video['video_id'], user_id)
                db.set_last_video_id(video['video_id'])
            else:
                # Fallback: send as document
                try:
                    video_msg = bot.send_document(chat_id, video['link'], caption=caption)
                    add_message_to_delete(chat_id, video_msg.message_id)
                    db.mark_video_sent(video['video_id'], user_id)
                except Exception as e:
                    print(f"❌ Fallback failed for video {i}: {e}")
                    # Final fallback: send link
                    msg = bot.send_message(chat_id, f"📹 **Video {i}:** {video['title']}\n[Watch Here]({video['link']})", parse_mode='Markdown')
                    add_message_to_delete(chat_id, msg.message_id)
            
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error sending video {i}: {e}")
            msg = bot.send_message(chat_id, f"📹 **Video {i}:** {video['title']}\n[Watch Here]({video['link']})", parse_mode='Markdown')
            add_message_to_delete(chat_id, msg.message_id)

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    first_name = message.from_user.first_name or "User"
    db.create_user(user_id, username, first_name)
    
    add_message_to_delete(message.chat.id, message.message_id)
    
    if user_id == OWNER_ID:
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🔑 Create Token", callback_data="owner_create"),
            types.InlineKeyboardButton("📋 My Tokens", callback_data="owner_tokens"),
            types.InlineKeyboardButton("🔗 Change Free Link", callback_data="owner_link")
        )
        msg = bot.reply_to(message, "👑 **WELCOME BOSS!**\n\nSelect an option:", reply_markup=markup, parse_mode='Markdown')
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    is_active = db.check_user_active(user_id)
    
    if is_active:
        info = db.get_user_token(user_id)
        if info:
            token = info[0]
            expires = info[2]
            remaining = expires - datetime.now() if expires else None
            time_str = f"{int(remaining.total_seconds() // 3600)}h {int((remaining.total_seconds() % 3600) // 60)}m" if remaining and remaining.total_seconds() > 0 else "Expiring soon"
        else:
            time_str = "Unknown"
        
        msg = bot.reply_to(message, f"✅ **ACCESS GRANTED**\nToken valid for: {time_str}\n\n📹 Sending latest videos...", parse_mode='Markdown')
        add_message_to_delete(message.chat.id, msg.message_id)
        send_videos_to_user(message.chat.id, user_id)
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        link = db.get_setting('free_token_link') or 'https://t.me/latestvideo10'
        markup.add(
            types.InlineKeyboardButton("🔑 Redeem Token", callback_data="user_redeem"),
            types.InlineKeyboardButton("🎁 Get Free Token", url=link)
        )
        msg = bot.reply_to(message, "🔐 **TOKEN LOGIN**\n\nUse /redeem [TOKEN] to login.", reply_markup=markup, parse_mode='Markdown')
        add_message_to_delete(message.chat.id, msg.message_id)

# ===== OWNER COMMANDS =====

@bot.message_handler(commands=['create'])
def create_token(message):
    if message.from_user.id != OWNER_ID:
        msg = bot.reply_to(message, "❌ Owner only.")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    parts = message.text.split()
    if len(parts) < 3:
        msg = bot.reply_to(message, "❌ /create [HOURS] [DEVICE_LIMIT]\nExample: /create 24 100")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    try:
        hours = int(parts[1])
        device_limit = int(parts[2])
    except:
        msg = bot.reply_to(message, "❌ Enter valid numbers.")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    token = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    db.create_token(token, OWNER_ID, hours, device_limit)
    
    msg = bot.reply_to(message, 
        f"✅ **TOKEN CREATED!**\n\n"
        f"🔑 Token: `{token}`\n"
        f"⏱ Hours: {hours}\n"
        f"🖥 Device Limit: {device_limit}\n\n"
        f"User can redeem with:\n`/redeem {token}`",
        parse_mode='Markdown')
    add_message_to_delete(message.chat.id, msg.message_id)

@bot.message_handler(commands=['change'])
def change_link(message):
    if message.from_user.id != OWNER_ID:
        msg = bot.reply_to(message, "❌ Owner only.")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        msg = bot.reply_to(message, "❌ /change [LINK]\nExample: /change https://t.me/newchannel")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    db.set_setting('free_token_link', parts[1].strip())
    msg = bot.reply_to(message, f"✅ Free token link updated!")
    add_message_to_delete(message.chat.id, msg.message_id)

@bot.message_handler(commands=['tokens'])
def list_tokens(message):
    if message.from_user.id != OWNER_ID:
        msg = bot.reply_to(message, "❌ Owner only.")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    tokens = db.get_all_tokens()
    if not tokens:
        msg = bot.reply_to(message, "📌 No tokens created.")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    text = "📋 **TOKENS**\n\n"
    for t in tokens:
        status = "✅ Active" if t[7] else "❌ Expired"
        text += f"🔑 `{t[0]}` - {t[3]}h - {t[4]}/{t[2]} used - {status}\n"
    
    msg = bot.reply_to(message, text, parse_mode='Markdown')
    add_message_to_delete(message.chat.id, msg.message_id)

# ===== USER COMMANDS =====

@bot.message_handler(commands=['redeem'])
def redeem_token(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        msg = bot.reply_to(message, "❌ /redeem [TOKEN]\nExample: /redeem ABC123XYZ789")
        add_message_to_delete(message.chat.id, msg.message_id)
        return
    
    token = parts[1].strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    success, msg_text, hours = db.redeem_token(token, user_id, device_id)
    msg = bot.reply_to(message, msg_text)
    add_message_to_delete(message.chat.id, msg.message_id)
    
    if success:
        send_videos_to_user(message.chat.id, user_id)

@bot.message_handler(commands=['tokeninfo'])
def token_info(message):
    user_id = message.from_user.id
    
    if not db.check_user_active(user_id):
        msg = bot.reply_to(message, "❌ No active token. Use /redeem [TOKEN]")
        add_message_to_delete(message.chat.id, msg.message_id)
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
        
        msg = bot.reply_to(message, f"📊 **TOKEN INFO**\n\n🔑 Token: `{token}`\n⏱ Remaining: {time_str}\n📌 Status: {status}", parse_mode='Markdown')
        add_message_to_delete(message.chat.id, msg.message_id)
    else:
        msg = bot.reply_to(message, "❌ No token info.")
        add_message_to_delete(message.chat.id, msg.message_id)

@bot.message_handler(commands=['videos'])
def get_videos_command(message):
    user_id = message.from_user.id
    send_videos_to_user(message.chat.id, user_id)

# ===== CALLBACKS =====

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    is_active = db.check_user_active(user_id)
    
    if call.data == "owner_create":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📌 /create [HOURS] [LIMIT]")
        add_message_to_delete(call.message.chat.id, msg.message_id)
    
    elif call.data == "owner_tokens":
        bot.answer_callback_query(call.id)
        list_tokens(call.message)
    
    elif call.data == "owner_link":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📌 /change [LINK]")
        add_message_to_delete(call.message.chat.id, msg.message_id)
    
    elif call.data == "user_redeem":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🔑 Enter token:")
        add_message_to_delete(call.message.chat.id, msg.message_id)
        bot.register_next_step_handler(call.message, process_redeem)

def process_redeem(message):
    token = message.text.strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    success, msg_text, hours = db.redeem_token(token, user_id, device_id)
    msg = bot.reply_to(message, msg_text)
    add_message_to_delete(message.chat.id, msg.message_id)
    
    if success:
        send_videos_to_user(message.chat.id, user_id)

@bot.message_handler(commands=['help'])
def help_command(message):
    if message.from_user.id == OWNER_ID:
        text = "👑 **OWNER HELP**\n\n/create [HOURS] [LIMIT]\n/tokens\n/change [LINK]\n/videos"
    else:
        text = "🔹 **USER HELP**\n\n/redeem [TOKEN]\n/videos\n/tokeninfo"
    
    msg = bot.reply_to(message, text, parse_mode='Markdown')
    add_message_to_delete(message.chat.id, msg.message_id)

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    msg = bot.reply_to(message, "❓ Use /start")
    add_message_to_delete(message.chat.id, msg.message_id)

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   📹 TOKEN VIDEO BOT - FIRST VIDEO FIXED                   ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Video Channel: @{VIDEO_CHANNEL}")
    print(f"✅ Auto Delete: {DELETE_AFTER_MINUTES} minutes")
    print(f"✅ Bot starting...")
    
    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=10)
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()
