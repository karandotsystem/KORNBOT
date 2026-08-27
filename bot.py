#!/usr/bin/env python3
"""
📢 TELEGRAM REPORT BOT v2.1 - IMPORT FIXED
Child Physical Abuse Reporting
"""

import os
import time
import json
import random
import asyncio
import logging
from datetime import datetime
from telethon import TelegramClient, functions, types
from telethon.tl.types import (
    InputPeerUser, InputPeerChannel,
    Message
)
from telethon.errors import FloodWaitError, PeerIdInvalidError, RPCError
from telethon.tl.functions.messages import ImportChatInviteRequest, ReportRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.account import ReportPeerRequest
import telebot
from telebot import types as tg_types

# ==================== CONFIG ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
OWNER_ID = 8935807032

# Telegram API Credentials (from my.telegram.org)
API_ID = 31486711
API_HASH = "1b9f690d42fa6a15e37043ae1b6f03e6"

# ==================== DATABASE CONNECTION ====================
DB_HOST = "reseau.proxy.rlwy.net"
DB_PORT = 29905
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASSWORD = "dOkCcwkemyQRRXGnyOGBwlJloyjSyMqa"

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ==================== BOT SETUP ====================
bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
except:
    pass

# ==================== REPORT REASONS (Telethon v1.36+) ====================
# In newer Telethon, ReportReason classes are under types
# But we'll use the ReportRequest directly with reason parameter

REPORT_REASON_CHILD_ABUSE = 1  # Child abuse
REPORT_REASON_VIOLENCE = 2     # Violence
REPORT_REASON_SPAM = 3         # Spam
REPORT_REASON_PORNOGRAPHY = 4  # Pornography
REPORT_REASON_OTHER = 5        # Other

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.accounts = []
        self.current_channel = None
        self.current_post = None
        self.is_running = False
        self.report_reason = "child_physical_abuse"
    
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
    
    def get_active_accounts(self):
        return [acc for acc in self.accounts if acc["active"]]
    
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
        """Create and start a Telegram client with human-like delay"""
        client = TelegramClient(f"sessions/{session_name}", self.api_id, self.api_hash)
        await client.start(phone=phone)
        await asyncio.sleep(random.uniform(1, 3))
        return client
    
    async def join_channel_human(self, client, channel_link):
        """Join channel with human-like behaviour"""
        try:
            await asyncio.sleep(random.uniform(1.5, 4))
            
            if "+" in channel_link:
                invite_hash = channel_link.split("+")[-1]
                result = await client(functions.messages.ImportChatInviteRequest(invite_hash))
                await asyncio.sleep(random.uniform(2, 5))
                return True
            else:
                username = channel_link.split("/")[-1]
                entity = await client.get_entity(f"@{username}")
                await asyncio.sleep(random.uniform(1, 3))
                await client(JoinChannelRequest(entity))
                await asyncio.sleep(random.uniform(2, 5))
                return True
        except Exception as e:
            logger.error(f"Join error: {e}")
            return False
    
    async def report_post_human(self, client, post_link):
        """
        Report with Child Physical Abuse - Human Simulation
        Using ReportRequest with proper parameters
        """
        try:
            parts = post_link.split("/")
            username = parts[-2]
            post_id = int(parts[-1])
            
            entity = await client.get_entity(f"@{username}")
            
            await asyncio.sleep(random.uniform(2, 5))
            
            messages = await client.get_messages(entity, ids=post_id)
            if not messages:
                return False
            
            message = messages[0]
            await asyncio.sleep(random.uniform(3, 8))
            
            # ============ REPORT: Child Physical Abuse ============
            # Using ReportRequest with reason as ReportReason type
            # For child abuse, we use the report reason ID or type
            
            # Try with ReportReasonChildAbuse if available, else use other method
            try:
                from telethon.tl.types import ReportReasonChildAbuse
                reason = ReportReasonChildAbuse()
            except ImportError:
                # Fallback: use ReportReason with string
                reason = "child_abuse"
            
            result1 = await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason=reason,
                message="⚠️ URGENT: Child physical abuse material detected. Content shows physical harm and violence against minors. This is a serious violation of Telegram's Terms of Service Section 4.2 and 5.1 regarding child abuse content. Immediate removal and account suspension required."
            ))
            
            await asyncio.sleep(random.uniform(2, 5))
            
            # ============ SECOND REPORT: Violence ============
            try:
                from telethon.tl.types import ReportReasonViolence
                reason2 = ReportReasonViolence()
            except ImportError:
                reason2 = "violence"
            
            result2 = await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason=reason2,
                message="Physical violence against children. Child abuse content showing harm to minors. This violates Telegram's community guidelines."
            ))
            
            await asyncio.sleep(random.uniform(2, 4))
            
            # ============ THIRD REPORT: Spam ============
            try:
                from telethon.tl.types import ReportReasonSpam
                reason3 = ReportReasonSpam()
            except ImportError:
                reason3 = "spam"
            
            result3 = await client(functions.messages.ReportRequest(
                peer=entity,
                id=[post_id],
                reason=reason3,
                message="Multiple reports of child physical abuse. This channel is distributing harmful content."
            ))
            
            await asyncio.sleep(random.uniform(1, 3))
            
            # ============ PEER REPORT ============
            try:
                await client(functions.account.ReportPeerRequest(
                    peer=entity,
                    reason=reason,
                    message="Channel distributing child physical abuse material. This channel violates Telegram's Terms of Service and should be banned."
                ))
            except Exception as e:
                logger.warning(f"Peer report failed: {e}")
            
            return True
            
        except FloodWaitError as e:
            logger.error(f"Rate limited: {e.seconds}s")
            await asyncio.sleep(e.seconds)
            return False
        except Exception as e:
            logger.error(f"Report error: {e}")
            return False

manager = TelegramClientManager()

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Unauthorized. This bot is private.")
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
📢 <b>TELEGRAM REPORT BOT v2.1</b>
<i>Real Human Simulation</i>

━━━━━━━━━━━━━━━━━━━━━
📋 <b>Accounts:</b> {len(db.get_accounts())}
🎯 <b>Channel:</b> {db.current_channel or 'Not Set'}
📝 <b>Post:</b> {db.current_post or 'Not Set'}
📌 <b>Report Reason:</b> 🟢 Child Physical Abuse
🔄 <b>Status:</b> {'🟢 Running' if db.is_running else '🔴 Idle'}
━━━━━━━━━━━━━━━━━━━━━

<b>Human Simulation Flow:</b>
1️⃣ Account logs in
2️⃣ Waits 2-5 seconds (human-like)
3️⃣ Joins channel
4️⃣ Waits 3-8 seconds (reads post)
5️⃣ Opens post
6️⃣ Reports with <b>Child Physical Abuse</b>
7️⃣ Waits 2-5 seconds
8️⃣ Logs out
"""
    bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')

# ==================== CALLBACK HANDLERS ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if user_id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized!", show_alert=True)
        return
    
    if call.data == "add_accounts":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id, 
            "📋 <b>Add Accounts</b>\n\n"
            "Send phone numbers one per line:\n"
            "<code>+919876543210</code>\n"
            "<code>+919876543211</code>\n\n"
            "⚠️ Each number will create a session.\n"
            "Send <b>/done</b> when finished.",
            parse_mode='HTML')
        bot.register_next_step_handler(msg, process_accounts)
    
    elif call.data == "set_channel":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            "🎯 <b>Set Channel</b>\n\n"
            "Send the channel link:\n"
            "<code>https://t.me/channelusername</code>\n\n"
            "Or private invite:\n"
            "<code>https://t.me/+abcdefghijkl</code>",
            parse_mode='HTML')
        bot.register_next_step_handler(msg, process_channel)
    
    elif call.data == "set_post":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(call.message.chat.id,
            "📝 <b>Set Post</b>\n\n"
            "Send the post link to report:\n"
            "<code>https://t.me/channelusername/123</code>",
            parse_mode='HTML')
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
        bot.send_message(call.message.chat.id, "🔄 All data reset successfully!")
        start(call.message)

# ==================== PROCESS FUNCTIONS ====================

def process_accounts(message):
    user_id = message.from_user.id
    
    if user_id != OWNER_ID:
        return
    
    if message.text == "/done":
        bot.reply_to(message, f"✅ Accounts added: {len(db.get_accounts())}")
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
    
    bot.reply_to(message, f"✅ Added {added} accounts.\nTotal: {len(db.get_accounts())}\n\nSend more or /done to finish.")
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
        bot.reply_to(message, "❌ Invalid channel link.")
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
        bot.reply_to(message, "❌ Invalid post link. Format: https://t.me/username/123")
        msg = bot.send_message(message.chat.id, "Send post link again:")
        bot.register_next_step_handler(msg, process_post)

def show_status(message):
    accounts = db.get_accounts()
    active = db.get_active_accounts()
    
    reported_count = sum(1 for acc in accounts if acc.get("reported", False))
    joined_count = sum(1 for acc in accounts if acc.get("joined", False))
    
    text = f"""
📊 <b>STATUS REPORT</b>

━━━━━━━━━━━━━━━━━━━━━
📋 <b>Accounts:</b> {len(accounts)}
🟢 <b>Active:</b> {len(active)}
📢 <b>Joined:</b> {joined_count}
📝 <b>Reported:</b> {reported_count}
🎯 <b>Channel:</b> {db.current_channel or 'Not Set'}
📝 <b>Post:</b> {db.current_post or 'Not Set'}
📌 <b>Report Reason:</b> Child Physical Abuse
🔄 <b>Running:</b> {'✅ Yes' if db.is_running else '❌ No'}
━━━━━━━━━━━━━━━━━━━━━

<b>Account Details:</b>
"""
    for i, acc in enumerate(accounts[:10], 1):
        status_icon = "✅" if acc.get("reported") else ("📢" if acc.get("joined") else "⏳")
        text += f"{i}. {status_icon} {acc['phone']} - {acc.get('status', 'pending')}\n"
    
    if len(accounts) > 10:
        text += f"\n... and {len(accounts) - 10} more"
    
    bot.send_message(message.chat.id, text, parse_mode='HTML')

# ==================== REPORT ENGINE ====================

def start_report_process(message):
    accounts = db.get_accounts()
    channel = db.current_channel
    post = db.current_post
    
    if not accounts:
        bot.reply_to(message, "❌ No accounts added!")
        return
    
    if not channel:
        bot.reply_to(message, "❌ No channel set!")
        return
    
    if not post:
        bot.reply_to(message, "❌ No post set!")
        return
    
    bot.reply_to(message, f"""
🚀 <b>STARTING REPORT PROCESS</b>

━━━━━━━━━━━━━━━━━━━━━
📋 <b>Accounts:</b> {len(accounts)}
🎯 <b>Channel:</b> {channel}
📝 <b>Post:</b> {post}
📌 <b>Reason:</b> Child Physical Abuse
🔄 <b>Mode:</b> Human Simulation
━━━━━━━━━━━━━━━━━━━━━

⏳ Starting reports...
Each account will act like a real human.
Progress will be shown here.
""", parse_mode='HTML')
    
    db.is_running = True
    
    import threading
    thread = threading.Thread(target=lambda: asyncio.run(run_reports(message.chat.id)), daemon=True)
    thread.start()

async def run_reports(chat_id):
    accounts = db.get_accounts()
    channel = db.current_channel
    post = db.current_post
    
    success_count = 0
    fail_count = 0
    details = []
    
    for i, account in enumerate(accounts, 1):
        try:
            bot.send_message(chat_id, f"📊 Account {i}/{len(accounts)}: {account['phone']} - ⏳ Processing...")
            
            client = await manager.create_client(account['phone'], account['session'])
            
            await asyncio.sleep(random.uniform(1, 3))
            
            bot.send_message(chat_id, f"📢 Account {i}: Joining channel...")
            joined = await manager.join_channel_human(client, channel)
            
            if not joined:
                bot.send_message(chat_id, f"❌ Account {i}: Failed to join channel")
                fail_count += 1
                details.append(f"❌ {account['phone']}: Join failed")
                await client.disconnect()
                continue
            
            db.mark_joined(account['phone'])
            
            await asyncio.sleep(random.uniform(3, 8))
            
            bot.send_message(chat_id, f"📝 Account {i}: Reporting with Child Physical Abuse...")
            reported = await manager.report_post_human(client, post)
            
            if reported:
                success_count += 1
                db.mark_reported(account['phone'])
                bot.send_message(chat_id, f"✅ Account {i}: Report sent successfully!")
                details.append(f"✅ {account['phone']}: Report sent")
            else:
                fail_count += 1
                bot.send_message(chat_id, f"❌ Account {i}: Report failed")
                details.append(f"❌ {account['phone']}: Report failed")
            
            await asyncio.sleep(random.uniform(1, 3))
            await client.disconnect()
            
            await asyncio.sleep(random.uniform(5, 10))
            
        except Exception as e:
            error_msg = str(e)[:50]
            bot.send_message(chat_id, f"❌ Account {i}: Error - {error_msg}")
            fail_count += 1
            details.append(f"❌ {account['phone']}: {error_msg}")
    
    db.is_running = False
    
    detail_text = "\n".join(details[:20])
    if len(details) > 20:
        detail_text += f"\n... and {len(details) - 20} more"
    
    bot.send_message(chat_id, f"""
✅ <b>REPORT PROCESS COMPLETE!</b>

━━━━━━━━━━━━━━━━━━━━━
✅ <b>Success:</b> {success_count}
❌ <b>Failed:</b> {fail_count}
📊 <b>Total:</b> {len(accounts)}
📌 <b>Reason:</b> Child Physical Abuse
🔄 <b>Mode:</b> Human Simulation
━━━━━━━━━━━━━━━━━━━━━

<b>DETAILED REPORT:</b>
{detail_text}
━━━━━━━━━━━━━━━━━━━━━

⚠️ Reports sent with <b>Child Physical Abuse</b> reason.
Telegram team will review the content.
""", parse_mode='HTML')

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   📢 TELEGRAM REPORT BOT v2.1                               ║
    ║   - Real Human Simulation                                   ║
    ║   - Child Physical Abuse Reporting                          ║
    ║   - Import Fixed                                           ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Report Reason: Child Physical Abuse")
    print(f"✅ Mode: Human Simulation")
    print(f"✅ Bot starting...")
    
    os.makedirs("sessions", exist_ok=True)
    
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=10)
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        time.sleep(5)
        main()

if __name__ == "__main__":
    main()
