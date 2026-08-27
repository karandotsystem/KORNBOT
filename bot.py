#!/usr/bin/env python3
"""
📢 TELEGRAM REPORT BOT v8.0 - FINAL WORKING
"""

import os
import time
import random
import asyncio
import threading
import logging
from datetime import datetime
from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError, SessionPasswordNeededError
from telethon.tl.functions.messages import ImportChatInviteRequest, ReportRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.account import ReportPeerRequest
import telebot
from telebot import types as tg_types

# ==================== DISABLE LOGGING ====================
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

# ==================== CONFIG ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
OWNER_ID = 8935807032
API_ID = 31486711
API_HASH = "1b9f690d42fa6a15e37043ae1b6f03e6"

# ==================== BOT SETUP ====================
bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
except:
    pass

print("✅ Bot Started!")

# ==================== SESSIONS ====================
sessions = {}

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.accounts = []
        self.current_channel = None
        self.current_post = None
        self.is_running = False
    
    def add_account(self, phone, session_name):
        self.accounts.append({
            "phone": phone,
            "session": session_name,
            "joined": False,
            "reported": False,
            "logged_in": False
        })
        return len(self.accounts)
    
    def get_accounts(self):
        return self.accounts
    
    def set_channel(self, channel_link):
        self.current_channel = channel_link
        return True
    
    def set_post(self, post_link):
        self.current_post = post_link
        return True
    
    def mark_joined(self, phone):
        for acc in self.accounts:
            if acc["phone"] == phone:
                acc["joined"] = True
                return True
        return False
    
    def mark_reported(self, phone):
        for acc in self.accounts:
            if acc["phone"] == phone:
                acc["reported"] = True
                return True
        return False
    
    def mark_logged_in(self, phone):
        for acc in self.accounts:
            if acc["phone"] == phone:
                acc["logged_in"] = True
                return True
        return False
    
    def reset_all(self):
        self.accounts = []
        self.current_channel = None
        self.current_post = None
        self.is_running = False

db = Database()

# ==================== TELEGRAM CLIENT MANAGER ====================
class TelegramClientManager:
    def __init__(self):
        self.api_id = API_ID
        self.api_hash = API_HASH
    
    async def join_channel(self, client, channel_link):
        try:
            await asyncio.sleep(random.uniform(1, 2))
            if "+" in channel_link:
                invite_hash = channel_link.split("+")[-1]
                await client(functions.messages.ImportChatInviteRequest(invite_hash))
            else:
                username = channel_link.split("/")[-1]
                entity = await client.get_entity(f"@{username}")
                await client(JoinChannelRequest(entity))
            await asyncio.sleep(random.uniform(1, 2))
            return True
        except:
            return False
    
    async def report_post(self, client, post_link):
        try:
            parts = post_link.split("/")
            username = parts[-2]
            post_id = int(parts[-1])
            
            entity = await client.get_entity(f"@{username}")
            await asyncio.sleep(random.uniform(1, 2))
            
            try:
                from telethon.tl.types import ReportReasonChildAbuse
                reason1 = ReportReasonChildAbuse()
            except:
                reason1 = "child_abuse"
            
            await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason=reason1,
                message="Child physical abuse material detected."
            ))
            
            await asyncio.sleep(random.uniform(1, 2))
            
            return True
            
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            return False
        except:
            return False

manager = TelegramClientManager()

# ==================== LOGIN ====================

async def login_account(phone, session_name, chat_id):
    try:
        client = TelegramClient(f"sessions/{session_name}", API_ID, API_HASH)
        await client.connect()
        
        if await client.is_user_authorized():
            db.mark_logged_in(phone)
            bot.send_message(chat_id, f"✅ {phone} already logged in!")
            return client, True
        
        await client.send_code_request(phone)
        bot.send_message(chat_id, f"📱 OTP sent to {phone}\nSend OTP code (or /skip to skip):")
        
        sessions[chat_id] = {"phone": phone, "client": client, "waiting": True, "code": None}
        
        timeout = 60
        start = time.time()
        while sessions[chat_id]["waiting"]:
            if time.time() - start > timeout:
                bot.send_message(chat_id, f"⏱ OTP timeout for {phone}")
                del sessions[chat_id]
                await client.disconnect()
                return None, False
            await asyncio.sleep(1)
        
        code = sessions[chat_id]["code"]
        del sessions[chat_id]
        
        if not code or code.lower() == "/skip":
            bot.send_message(chat_id, f"⏭ Skipped {phone}")
            await client.disconnect()
            return None, False
        
        try:
            await client.sign_in(phone, code=code)
            db.mark_logged_in(phone)
            bot.send_message(chat_id, f"✅ {phone} logged in!")
            return client, True
        except SessionPasswordNeededError:
            bot.send_message(chat_id, f"🔐 {phone} needs 2FA. Skipping.")
            await client.disconnect()
            return None, False
            
    except Exception as e:
        bot.send_message(chat_id, f"❌ {phone}: {str(e)[:30]}")
        return None, False

# ==================== MESSAGE HANDLER ====================

@bot.message_handler(func=lambda msg: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    text = message.text.strip()
    
    if chat_id in sessions and sessions[chat_id].get("waiting", False):
        sessions[chat_id]["code"] = text
        sessions[chat_id]["waiting"] = False
        bot.reply_to(message, "✅ Received!")
        return

# ==================== COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Unauthorized.")
        return
    
    markup = tg_types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        tg_types.InlineKeyboardButton("📋 Add Accounts", callback_data="add_accounts"),
        tg_types.InlineKeyboardButton("🎯 Set Channel", callback_data="set_channel"),
        tg_types.InlineKeyboardButton("📝 Set Post", callback_data="set_post"),
        tg_types.InlineKeyboardButton("🚀 Start Report", callback_data="start_report"),
        tg_types.InlineKeyboardButton("📊 Status", callback_data="status"),
        tg_types.InlineKeyboardButton("🔄 Reset All", callback_data="reset_all")
    )
    
    text = f"""
📢 REPORT BOT v8.0

Accounts: {len(db.get_accounts())}
Channel: {db.current_channel or 'Not Set'}
Post: {db.current_post or 'Not Set'}
Status: {'✅ Running' if db.is_running else '⏸ Idle'}

1. Add Accounts
2. Set Channel
3. Set Post
4. Start Report
"""
    bot.reply_to(message, text, reply_markup=markup)

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized!", True)
        return
    
    if call.data == "add_accounts":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, 
            "📋 Send phone numbers (with +):\n+919876543210\n\nSend /done when finished.")
        bot.register_next_step_handler(msg, process_accounts)
    
    elif call.data == "set_channel":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "🎯 Send channel link:\nhttps://t.me/username")
        bot.register_next_step_handler(msg, process_channel)
    
    elif call.data == "set_post":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📝 Send post link:\nhttps://t.me/username/123")
        bot.register_next_step_handler(msg, process_post)
    
    elif call.data == "start_report":
        bot.answer_callback_query(call.id)
        start_report_process(call.message)
    
    elif call.data == "status":
        bot.answer_callback_query(call.id)
        show_status(call.message)
    
    elif call.data == "reset_all":
        bot.answer_callback_query(call.id)
        db.reset_all()
        bot.send_message(call.message.chat.id, "🔄 Reset complete!")
        start(call.message)

# ==================== PROCESS FUNCTIONS ====================

def process_accounts(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    if message.text == "/done":
        bot.reply_to(message, f"✅ Added: {len(db.get_accounts())} accounts")
        start(message)
        return
    
    phones = message.text.strip().split('\n')
    added = 0
    for phone in phones:
        phone = phone.strip()
        if phone and phone.startswith('+'):
            session_name = f"session_{added}_{int(time.time())}"
            db.add_account(phone, session_name)
            added += 1
    
    bot.reply_to(message, f"✅ Added {added} accounts. Total: {len(db.get_accounts())}")
    start(message)

def process_channel(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    channel = message.text.strip()
    if channel.startswith("https://t.me/"):
        db.set_channel(channel)
        bot.reply_to(message, f"✅ Channel set: {channel}")
        start(message)
    else:
        bot.reply_to(message, "❌ Invalid link.")
        msg = bot.send_message(message.chat.id, "Send channel link again:")
        bot.register_next_step_handler(msg, process_channel)

def process_post(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        return
    
    post = message.text.strip()
    if post.startswith("https://t.me/") and "/" in post.replace("https://t.me/", ""):
        db.set_post(post)
        bot.reply_to(message, f"✅ Post set: {post}")
        start(message)
    else:
        bot.reply_to(message, "❌ Invalid post link.")
        msg = bot.send_message(message.chat.id, "Send post link again:")
        bot.register_next_step_handler(msg, process_post)

def show_status(message):
    accounts = db.get_accounts()
    total = len(accounts)
    joined = sum(1 for a in accounts if a.get("joined", False))
    reported = sum(1 for a in accounts if a.get("reported", False))
    
    text = f"""
📊 STATUS

Total: {total}
Joined: {joined}
Reported: {reported}
Channel: {db.current_channel or 'Not Set'}
Post: {db.current_post or 'Not Set'}
Running: {'✅' if db.is_running else '❌'}
"""
    for i, acc in enumerate(accounts[:10], 1):
        s = "✅" if acc.get("reported") else ("📢" if acc.get("joined") else "⏳")
        text += f"{i}. {s} {acc['phone']}\n"
    
    if total > 10:
        text += f"... and {total - 10} more"
    
    bot.send_message(message.chat.id, text)

# ==================== REPORT ENGINE ====================

def start_report_process(message):
    accounts = db.get_accounts()
    channel = db.current_channel
    post = db.current_post
    
    if not accounts:
        bot.reply_to(message, "❌ No accounts!")
        return
    
    if not channel:
        bot.reply_to(message, "❌ No channel set!")
        return
    
    if not post:
        bot.reply_to(message, "❌ No post set!")
        return
    
    bot.reply_to(message, f"""
🚀 STARTING REPORT

Accounts: {len(accounts)}
Channel: {channel}
Post: {post}

⚠️ Send OTP when prompted.
Type /skip to skip account.
""")
    
    db.is_running = True
    threading.Thread(target=lambda: asyncio.run(run_reports(message.chat.id)), daemon=True).start()

async def run_reports(chat_id):
    accounts = db.get_accounts()
    channel = db.current_channel
    post = db.current_post
    
    success = 0
    failed = 0
    
    for i, account in enumerate(accounts, 1):
        try:
            bot.send_message(chat_id, f"📊 {i}/{len(accounts)}: {account['phone']}")
            
            client, logged_in = await login_account(
                account['phone'], 
                account['session'], 
                chat_id
            )
            
            if not logged_in or not client:
                failed += 1
                continue
            
            await asyncio.sleep(random.uniform(1, 2))
            
            joined = await manager.join_channel(client, channel)
            if not joined:
                bot.send_message(chat_id, f"❌ Join failed")
                failed += 1
                await client.disconnect()
                continue
            
            db.mark_joined(account['phone'])
            await asyncio.sleep(random.uniform(2, 3))
            
            reported = await manager.report_post(client, post)
            if reported:
                success += 1
                db.mark_reported(account['phone'])
                bot.send_message(chat_id, f"✅ Report sent!")
            else:
                failed += 1
                bot.send_message(chat_id, f"❌ Report failed")
            
            await client.disconnect()
            await asyncio.sleep(random.uniform(3, 5))
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ Error")
            failed += 1
    
    db.is_running = False
    
    bot.send_message(chat_id, f"""
✅ REPORT COMPLETE!

Success: {success}
Failed: {failed}
Total: {len(accounts)}
""")

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   📢 REPORT BOT v8.0 - FINAL WORKING                        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print("✅ Owner:", OWNER_ID)
    print("✅ Bot starting...")
    
    os.makedirs("sessions", exist_ok=True)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
