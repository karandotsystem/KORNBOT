#!/usr/bin/env python3
"""
📢 TELEGRAM REPORT BOT v2.2 - FULLY WORKING
Child Physical Abuse Reporting
"""

import os
import time
import random
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, functions
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import ImportChatInviteRequest, ReportRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.account import ReportPeerRequest
import telebot
from telebot import types as tg_types

# ==================== DISABLE LOGGING (CLEAN LOGS) ====================
logging.disable(logging.CRITICAL)
os.environ['PYTHONWARNINGS'] = 'ignore'

# ==================== CONFIG ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
OWNER_ID = 8935807032

API_ID = 31486711
API_HASH = "1b9f690d42fa6a15e37043ae1b6f03e6"

DB_HOST = "reseau.proxy.rlwy.net"
DB_PORT = 29905
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASSWORD = "dOkCcwkemyQRRXGnyOGBwlJloyjSyMqa"

# ==================== BOT SETUP ====================
bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
except:
    pass

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
            "active": True,
            "joined": False,
            "reported": False,
            "status": "pending"
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
                acc["status"] = "joined"
                return True
        return False
    
    def mark_reported(self, phone):
        for acc in self.accounts:
            if acc["phone"] == phone:
                acc["reported"] = True
                acc["status"] = "reported"
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
    
    async def create_client(self, phone, session_name):
        client = TelegramClient(f"sessions/{session_name}", self.api_id, self.api_hash)
        await client.start(phone=phone)
        await asyncio.sleep(random.uniform(1, 3))
        return client
    
    async def join_channel(self, client, channel_link):
        try:
            await asyncio.sleep(random.uniform(1.5, 4))
            if "+" in channel_link:
                invite_hash = channel_link.split("+")[-1]
                await client(functions.messages.ImportChatInviteRequest(invite_hash))
            else:
                username = channel_link.split("/")[-1]
                entity = await client.get_entity(f"@{username}")
                await client(JoinChannelRequest(entity))
            await asyncio.sleep(random.uniform(2, 5))
            return True
        except:
            return False
    
    async def report_post(self, client, post_link):
        try:
            parts = post_link.split("/")
            username = parts[-2]
            post_id = int(parts[-1])
            
            entity = await client.get_entity(f"@{username}")
            await asyncio.sleep(random.uniform(2, 5))
            
            # Report 1: Child Abuse
            try:
                from telethon.tl.types import ReportReasonChildAbuse
                reason1 = ReportReasonChildAbuse()
            except:
                reason1 = "child_abuse"
            
            await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason=reason1,
                message="Child physical abuse material detected. Immediate removal required."
            ))
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # Report 2: Violence
            try:
                from telethon.tl.types import ReportReasonViolence
                reason2 = ReportReasonViolence()
            except:
                reason2 = "violence"
            
            await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason=reason2,
                message="Violence against children."
            ))
            
            await asyncio.sleep(random.uniform(1, 3))
            
            # Report 3: Spam
            try:
                from telethon.tl.types import ReportReasonSpam
                reason3 = ReportReasonSpam()
            except:
                reason3 = "spam"
            
            await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason=reason3,
                message="Multiple reports of child abuse content."
            ))
            
            await asyncio.sleep(random.uniform(1, 2))
            
            # Peer report
            try:
                await client(functions.account.ReportPeerRequest(
                    peer=entity,
                    reason=reason1,
                    message="Channel distributing child abuse material."
                ))
            except:
                pass
            
            return True
            
        except FloodWaitError as e:
            await asyncio.sleep(e.seconds)
            return False
        except:
            return False

manager = TelegramClientManager()

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
📢 REPORT BOT v2.2

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
            "📋 Send phone numbers:\n+919876543210\n+919876543211\n\nSend /done when finished.")
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
    bot.register_next_step_handler(message, process_accounts)

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

Total Accounts: {total}
Joined: {joined}
Reported: {reported}
Channel: {db.current_channel or 'Not Set'}
Post: {db.current_post or 'Not Set'}
Running: {'✅' if db.is_running else '❌'}

Accounts:
"""
    for i, acc in enumerate(accounts[:10], 1):
        status = "✅" if acc.get("reported") else ("📢" if acc.get("joined") else "⏳")
        text += f"{i}. {status} {acc['phone']}\n"
    
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

⏳ Processing...
""")
    
    db.is_running = True
    import threading
    thread = threading.Thread(target=lambda: asyncio.run(run_reports(message.chat.id)), daemon=True)
    thread.start()

async def run_reports(chat_id):
    accounts = db.get_accounts()
    channel = db.current_channel
    post = db.current_post
    
    success = 0
    failed = 0
    details = []
    
    for i, account in enumerate(accounts, 1):
        try:
            bot.send_message(chat_id, f"📊 {i}/{len(accounts)}: {account['phone']} - Processing...")
            
            client = await manager.create_client(account['phone'], account['session'])
            await asyncio.sleep(random.uniform(1, 3))
            
            joined = await manager.join_channel(client, channel)
            if not joined:
                bot.send_message(chat_id, f"❌ {i}: Join failed")
                failed += 1
                await client.disconnect()
                continue
            
            db.mark_joined(account['phone'])
            await asyncio.sleep(random.uniform(3, 8))
            
            reported = await manager.report_post(client, post)
            if reported:
                success += 1
                db.mark_reported(account['phone'])
                bot.send_message(chat_id, f"✅ {i}: Report sent!")
            else:
                failed += 1
                bot.send_message(chat_id, f"❌ {i}: Report failed")
            
            await client.disconnect()
            await asyncio.sleep(random.uniform(5, 10))
            
        except Exception as e:
            bot.send_message(chat_id, f"❌ {i}: Error")
            failed += 1
    
    db.is_running = False
    
    bot.send_message(chat_id, f"""
✅ REPORT COMPLETE!

Success: {success}
Failed: {failed}
Total: {len(accounts)}

✅ Done!
""")

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   📢 REPORT BOT v2.2 - FULLY WORKING                        ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print("✅ Owner:", OWNER_ID)
    print("✅ Bot starting...")
    
    os.makedirs("sessions", exist_ok=True)
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=10)
    except:
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
