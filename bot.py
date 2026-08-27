#!/usr/bin/env python3
"""
📢 TELEGRAM REPORT BOT v10.0 - SIMPLEST WORKING
"""

import os
import time
import random
import asyncio
import threading
import logging
from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import ImportChatInviteRequest, ReportRequest
from telethon.tl.functions.channels import JoinChannelRequest
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

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.accounts = []
        self.current_channel = None
        self.current_post = None
        self.is_running = False
    
    def add_account(self, phone):
        self.accounts.append({"phone": phone, "session": f"session_{len(self.accounts)}_{int(time.time())}"})
        return len(self.accounts)
    
    def get_accounts(self):
        return self.accounts
    
    def set_channel(self, link):
        self.current_channel = link
        return True
    
    def set_post(self, link):
        self.current_post = link
        return True
    
    def reset_all(self):
        self.accounts = []
        self.current_channel = None
        self.current_post = None
        self.is_running = False

db = Database()

# ==================== BOT COMMANDS ====================

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
📢 REPORT BOT v10.0

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
    print(f"✅ /start response sent to {user_id}")

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized!", True)
        return
    
    if call.data == "add_accounts":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, "📋 Send phone numbers (with +):\n+919876543210\n\nSend /done when finished.")
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
    if message.text == "/done":
        bot.reply_to(message, f"✅ Added: {len(db.get_accounts())} accounts")
        start(message)
        return
    
    phones = message.text.strip().split('\n')
    added = 0
    for phone in phones:
        phone = phone.strip()
        if phone and phone.startswith('+'):
            db.add_account(phone)
            added += 1
    
    bot.reply_to(message, f"✅ Added {added} accounts. Total: {len(db.get_accounts())}")
    start(message)

def process_channel(message):
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
    text = f"""
📊 STATUS

Total: {len(accounts)}
Channel: {db.current_channel or 'Not Set'}
Post: {db.current_post or 'Not Set'}
Running: {'✅' if db.is_running else '❌'}
"""
    for i, acc in enumerate(accounts[:10], 1):
        text += f"{i}. {acc['phone']}\n"
    if len(accounts) > 10:
        text += f"... and {len(accounts) - 10} more"
    bot.send_message(message.chat.id, text)

# ==================== REPORT ENGINE ====================

def start_report_process(message):
    accounts = db.get_accounts()
    if not accounts:
        bot.reply_to(message, "❌ No accounts!")
        return
    if not db.current_channel:
        bot.reply_to(message, "❌ No channel set!")
        return
    if not db.current_post:
        bot.reply_to(message, "❌ No post set!")
        return
    
    bot.reply_to(message, f"""
🚀 STARTING REPORT

Accounts: {len(accounts)}
Channel: {db.current_channel}
Post: {db.current_post}

⚠️ Report feature requires Telethon.
Check logs for status.
""")
    
    db.is_running = True
    threading.Thread(target=lambda: asyncio.run(run_reports(message.chat.id)), daemon=True).start()

async def run_reports(chat_id):
    accounts = db.get_accounts()
    success = 0
    failed = 0
    
    for i, acc in enumerate(accounts, 1):
        try:
            bot.send_message(chat_id, f"📊 {i}/{len(accounts)}: {acc['phone']}")
            
            client = TelegramClient(f"sessions/{acc['session']}", API_ID, API_HASH)
            await client.connect()
            
            if not await client.is_user_authorized():
                bot.send_message(chat_id, f"❌ {acc['phone']}: Not authorized. Needs OTP.")
                failed += 1
                continue
            
            # Join channel
            channel = db.current_channel
            if "+" in channel:
                invite_hash = channel.split("+")[-1]
                await client(functions.messages.ImportChatInviteRequest(invite_hash))
            else:
                username = channel.split("/")[-1]
                entity = await client.get_entity(f"@{username}")
                await client(JoinChannelRequest(entity))
            
            # Report
            post = db.current_post
            parts = post.split("/")
            username = parts[-2]
            post_id = int(parts[-1])
            entity = await client.get_entity(f"@{username}")
            
            await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason="child_abuse",
                message="Child physical abuse material detected."
            ))
            
            success += 1
            bot.send_message(chat_id, f"✅ {acc['phone']}: Report sent!")
            await client.disconnect()
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ {acc['phone']}: {str(e)[:30]}")
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
    ║   📢 REPORT BOT v10.0 - SIMPLEST WORKING                   ║
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
