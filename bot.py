#!/usr/bin/env python3
"""
📹 TOKEN VIDEO BOT v5.0 - OWNER & USER SEPARATE
- Owner: Welcome Boss + Admin Menu
- User: Normal Login Menu
- /change - Free token link change
- /create - Token create
"""

import os
import time
import logging
import random
import string
import asyncpg
import asyncio
from datetime import datetime, timedelta
import telebot
from telebot import types

# ==================== CONFIG ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
OWNER_ID = 8935807032
HELP_USERNAME = "@VATEROFWHOLETG"
DATABASE_URL = "postgresql://postgres:KARANxIOS@81680@db.dbskphxuqgmgqsonipnh.supabase.co:5432/postgres"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.pool = None
    
    async def init_pool(self):
        self.pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
        await self.init_tables()
        return self.pool
    
    async def init_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
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
            await conn.execute('''
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
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS token_usage (
                    id SERIAL PRIMARY KEY,
                    token TEXT,
                    user_id BIGINT,
                    device_id TEXT,
                    used_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS videos_cache (
                    id SERIAL PRIMARY KEY,
                    title TEXT,
                    link TEXT,
                    fetched_at TIMESTAMP DEFAULT NOW()
                )
            ''')
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            await conn.execute("INSERT INTO settings (key, value) VALUES ('free_token_link', 'https://t.me/latestvideo10') ON CONFLICT (key) DO NOTHING")
    
    async def create_user(self, user_id, username, first_name):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO users (user_id, username, first_name, created_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id) DO NOTHING
            ''', user_id, username, first_name)
    
    async def create_token(self, token, created_by, hours, device_limit):
        async with self.pool.acquire() as conn:
            expiry = datetime.now() + timedelta(hours=hours)
            await conn.execute('''
                INSERT INTO tokens (token, created_by, device_limit, hours, created_at, expiry_time, is_active)
                VALUES ($1, $2, $3, $4, NOW(), $5, 1)
            ''', token, created_by, device_limit, hours, expiry)
    
    async def redeem_token(self, token, user_id, device_id):
        token = token.upper().strip()
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('''
                SELECT token, device_limit, used_count, hours, expiry_time, is_active 
                FROM tokens WHERE token = $1
            ''', token)
            
            if not result:
                return False, "❌ Invalid token", 0
            
            if not result['is_active']:
                return False, "❌ Token expired", 0
            
            if datetime.now() > result['expiry_time']:
                await conn.execute('UPDATE tokens SET is_active = 0 WHERE token = $1', token)
                return False, "❌ Token expired", 0
            
            if result['used_count'] >= result['device_limit']:
                return False, f"❌ Device limit reached ({result['device_limit']})", 0
            
            user = await conn.fetchrow('SELECT is_active, token_expires_at FROM users WHERE user_id = $1', user_id)
            if user and user['is_active'] and user['token_expires_at']:
                if datetime.now() < user['token_expires_at']:
                    return False, "❌ You already have an active token", 0
            
            await conn.execute('UPDATE tokens SET used_count = used_count + 1 WHERE token = $1', token)
            await conn.execute('''
                INSERT INTO token_usage (token, user_id, device_id, used_at)
                VALUES ($1, $2, $3, NOW())
            ''', token, user_id, device_id)
            
            expiry = datetime.now() + timedelta(hours=result['hours'])
            await conn.execute('''
                UPDATE users 
                SET token = $1, token_activated_at = NOW(), token_expires_at = $2, device_id = $3, is_active = 1
                WHERE user_id = $4
            ''', token, expiry, device_id, user_id)
            
            return True, f"✅ Token redeemed! {result['hours']} hours added.", result['hours']
    
    async def check_user_active(self, user_id):
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow('SELECT token_expires_at, is_active FROM users WHERE user_id = $1', user_id)
            if not result or not result['is_active'] or not result['token_expires_at']:
                return False
            return datetime.now() < result['token_expires_at']
    
    async def get_user_token(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow('SELECT token, token_activated_at, token_expires_at, device_id FROM users WHERE user_id = $1', user_id)
    
    async def get_all_tokens(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch('SELECT * FROM tokens ORDER BY created_at DESC')
    
    async def get_setting(self, key):
        async with self.pool.acquire() as conn:
            result = await conn.fetchval('SELECT value FROM settings WHERE key = $1', key)
            return result
    
    async def set_setting(self, key, value):
        async with self.pool.acquire() as conn:
            await conn.execute('UPDATE settings SET value = $1 WHERE key = $2', value, key)

db = Database()

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
        logger.error(f"Video fetch error: {e}")
        return [{'title': f'Video {i+1}', 'link': f'https://t.me/latestvideo10/{i+1}'} for i in range(limit)]

# ==================== BOT COMMANDS ====================

# ===== OWNER COMMANDS =====

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    async def process():
        await db.create_user(user_id, message.from_user.username or "Unknown", message.from_user.first_name or "User")
        
        # OWNER - Special Menu
        if user_id == OWNER_ID:
            markup = types.InlineKeyboardMarkup(row_width=1)
            btn1 = types.InlineKeyboardButton("🔑 Create Token", callback_data="owner_create")
            btn2 = types.InlineKeyboardButton("📋 My Tokens", callback_data="owner_tokens")
            btn3 = types.InlineKeyboardButton("🔗 Change Free Link", callback_data="owner_link")
            btn4 = types.InlineKeyboardButton("📹 Latest Videos", callback_data="owner_videos")
            markup.add(btn1, btn2, btn3, btn4)
            
            bot.reply_to(message, 
                f"👑 **WELCOME BOSS!**\n\n"
                f"📌 You have full admin access.\n"
                f"Select an option:",
                reply_markup=markup, parse_mode='Markdown')
            return
        
        # USER - Normal Menu
        if await db.check_user_active(user_id):
            show_user_main_menu(message)
        else:
            show_user_login_menu(message)
    
    asyncio.run(process())

def show_user_login_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("🔑 Redeem Token", callback_data="user_redeem")
    
    async def get_link():
        return await db.get_setting('free_token_link') or 'https://t.me/latestvideo10'
    
    link = asyncio.run(get_link())
    btn2 = types.InlineKeyboardButton("🎁 Get Free Token", url=link)
    markup.add(btn1, btn2)
    
    bot.reply_to(message, 
        f"🔐 **TOKEN LOGIN**\n\n"
        f"You don't have an active token.\n"
        f"Use /redeem [TOKEN] to login.",
        reply_markup=markup, parse_mode='Markdown')

def show_user_main_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn1 = types.InlineKeyboardButton("📹 Latest Videos", callback_data="user_videos")
    btn2 = types.InlineKeyboardButton("📊 My Token", callback_data="user_token")
    markup.add(btn1, btn2)
    
    bot.reply_to(message, 
        f"✅ **ACCESS GRANTED**\n\n"
        f"Select an option:",
        reply_markup=markup, parse_mode='Markdown')

# ===== OWNER: CREATE TOKEN =====

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
    
    async def process():
        await db.create_token(token, OWNER_ID, hours, device_limit)
        bot.reply_to(message, 
            f"✅ **TOKEN CREATED!**\n\n"
            f"🔑 Token: `{token}`\n"
            f"⏱ Hours: {hours}\n"
            f"🖥 Device Limit: {device_limit}\n"
            f"📅 {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"
            f"User can redeem with:\n`/redeem {token}`",
            parse_mode='Markdown')
    
    asyncio.run(process())

# ===== OWNER: CHANGE FREE TOKEN LINK =====

@bot.message_handler(commands=['change'])
def change_link(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only.")
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ /change [LINK]\nExample: /change https://t.me/newchannel")
        return
    
    link = parts[1].strip()
    
    async def process():
        await db.set_setting('free_token_link', link)
        bot.reply_to(message, f"✅ Free token link updated!\n\n{link}")
    
    asyncio.run(process())

# ===== OWNER: LIST TOKENS =====

@bot.message_handler(commands=['tokens'])
def list_tokens(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only.")
        return
    
    async def process():
        tokens = await db.get_all_tokens()
        if not tokens:
            bot.reply_to(message, "📌 No tokens created.")
            return
        
        text = "📋 **TOKENS**\n\n"
        for t in tokens:
            status = "✅ Active" if t['is_active'] else "❌ Expired"
            text += f"🔑 `{t['token']}`\n"
            text += f"   ⏱ {t['hours']}h | 🖥 {t['used_count']}/{t['device_limit']}\n"
            text += f"   📅 {t['created_at'].strftime('%d-%m-%Y %H:%M')} | {status}\n\n"
        
        bot.reply_to(message, text, parse_mode='Markdown')
    
    asyncio.run(process())

# ===== USER: REDEEM =====

@bot.message_handler(commands=['redeem'])
def redeem_token(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "❌ /redeem [TOKEN]\nExample: /redeem ABC123XYZ789")
        return
    
    token = parts[1].strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    async def process():
        success, msg, hours = await db.redeem_token(token, user_id, device_id)
        bot.reply_to(message, msg)
        if success:
            show_user_main_menu(message)
    
    asyncio.run(process())

# ===== USER: TOKEN INFO =====

@bot.message_handler(commands=['tokeninfo'])
def token_info(message):
    user_id = message.from_user.id
    
    async def process():
        if not await db.check_user_active(user_id):
            bot.reply_to(message, "❌ No active token.")
            return
        
        info = await db.get_user_token(user_id)
        if info:
            token = info['token']
            expires = info['token_expires_at']
            remaining = expires - datetime.now() if expires else None
            if remaining and remaining.total_seconds() > 0:
                time_str = f"{int(remaining.total_seconds() // 3600)}h {int((remaining.total_seconds() % 3600) // 60)}m"
                status = "✅ Active"
            else:
                time_str = "Expired"
                status = "❌ Expired"
            
            bot.reply_to(message, 
                f"📊 **TOKEN INFO**\n\n"
                f"🔑 Token: `{token}`\n"
                f"⏱ Remaining: {time_str}\n"
                f"📌 Status: {status}",
                parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ No token info.")
    
    asyncio.run(process())

# ===== USER: VIDEOS =====

@bot.message_handler(commands=['videos'])
def get_videos(message):
    user_id = message.from_user.id
    
    async def process():
        if not await db.check_user_active(user_id):
            bot.reply_to(message, "❌ No active token.")
            return
        
        loading = bot.reply_to(message, "⏳ Fetching videos...")
        videos = fetch_channel_videos(10)
        
        if not videos:
            bot.edit_message_text("❌ No videos found.", chat_id=message.chat.id, message_id=loading.message_id)
            return
        
        text = "📹 **LATEST VIDEOS**\n\n"
        for i, video in enumerate(videos, 1):
            if video.get('link'):
                text += f"{i}. [{video['title']}]({video['link']})\n"
            else:
                text += f"{i}. {video['title']}\n"
        
        text += f"\n📌 [@latestvideo10](https://t.me/latestvideo10)"
        bot.edit_message_text(text, chat_id=message.chat.id, message_id=loading.message_id, parse_mode='Markdown')
    
    asyncio.run(process())

# ===== OWNER: VIDEOS =====

@bot.message_handler(commands=['allvideos'])
def owner_videos(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Owner only.")
        return
    
    loading = bot.reply_to(message, "⏳ Fetching videos...")
    videos = fetch_channel_videos(10)
    
    if not videos:
        bot.edit_message_text("❌ No videos found.", chat_id=message.chat.id, message_id=loading.message_id)
        return
    
    text = "📹 **OWNER - LATEST VIDEOS**\n\n"
    for i, video in enumerate(videos, 1):
        if video.get('link'):
            text += f"{i}. [{video['title']}]({video['link']})\n"
        else:
            text += f"{i}. {video['title']}\n"
    
    text += f"\n📌 [@latestvideo10](https://t.me/latestvideo10)"
    bot.edit_message_text(text, chat_id=message.chat.id, message_id=loading.message_id, parse_mode='Markdown')

# ===== CALLBACKS =====

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    # ===== OWNER CALLBACKS =====
    if call.data == "owner_create":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📌 /create [HOURS] [LIMIT]\nExample: /create 24 100")
    
    elif call.data == "owner_tokens":
        bot.answer_callback_query(call.id)
        list_tokens(call.message)
    
    elif call.data == "owner_link":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📌 /change [LINK]\nExample: /change https://t.me/newchannel")
    
    elif call.data == "owner_videos":
        bot.answer_callback_query(call.id)
        owner_videos(call.message)
    
    # ===== USER CALLBACKS =====
    elif call.data == "user_redeem":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "🔑 Enter token:\nExample: ABC123XYZ789")
        bot.register_next_step_handler(call.message, process_redeem_input)
    
    elif call.data == "user_videos":
        bot.answer_callback_query(call.id)
        get_videos(call.message)
    
    elif call.data == "user_token":
        bot.answer_callback_query(call.id)
        token_info(call.message)

def process_redeem_input(message):
    token = message.text.strip().upper()
    user_id = message.from_user.id
    device_id = f"device_{user_id}_{int(time.time())}"
    
    async def process():
        success, msg, hours = await db.redeem_token(token, user_id, device_id)
        bot.reply_to(message, msg)
        if success:
            show_user_main_menu(message)
    
    asyncio.run(process())

# ===== HELP =====

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    
    if user_id == OWNER_ID:
        text = """
👑 **OWNER HELP**

📌 **Commands:**
/start - Owner Menu
/create [HOURS] [LIMIT] - Create token
/tokens - List all tokens
/change [LINK] - Change free token link
/allvideos - View latest videos
/help - This menu

📌 **User Commands:**
/start - Login menu
/redeem [TOKEN] - Redeem token
/videos - View videos
/tokeninfo - Check token status
"""
    else:
        text = """
🔹 **USER HELP**

📌 **Commands:**
/start - Login menu
/redeem [TOKEN] - Redeem token
/videos - View latest videos
/tokeninfo - Check token status
/help - This menu
"""
    
    bot.reply_to(message, text, parse_mode='Markdown')

# ===== DEFAULT =====

@bot.message_handler(func=lambda message: True)
def default_handler(message):
    bot.reply_to(message, "❓ Use /start\n\n🔹 FOR HELP: @VATEROFWHOLETG")

# ==================== MAIN ====================

def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   📹 TOKEN VIDEO BOT v5.0 - OWNER & USER SEPARATE           ║
    ║   - Owner: Welcome Boss                                     ║
    ║   - User: Normal Login                                      ║
    ║   - /change - Change free link                              ║
    ║   - /create - Create token                                  ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    # Initialize database
    async def init():
        await db.init_pool()
        print("✅ Database connected")
    
    asyncio.run(init())
    
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
