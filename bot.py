#!/usr/bin/env python3
"""
🔥 OG PROMOTER BOT - GEMINI AI 🔥
Promotes OG Gaming Tool
"""

import os
import time
import json
import logging
import requests
import random
from datetime import datetime
import telebot
from telebot import types

# ==================== CONFIG ====================
BOT_TOKEN = "8919735025:AAFBCkMNcZWz5vr6lHfe3GGbx7Zag7k6FjE"
OWNER_ID = 8935807032
OWNER_USERNAME = "@BEONIXDEV"
PRODUCT_NAME = "OG"
PRODUCT_DESC = "OG is a premium gaming tool that enhances your gaming experience with advanced features, ESP, aimbot, wallhack, and smooth performance optimization."

# ==================== GEMINI API ====================
GEMINI_API_KEY = "AQ.Ab8RN6JPGFWSkPpuLmAZE9jZGPQqkkratKJ8Etvvx8-T3d0dJw"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
except:
    pass

# ==================== SYSTEM PROMPT ====================
SYSTEM_PROMPT = f"""
You are a marketing assistant for "{PRODUCT_NAME}" (OG), a premium gaming tool.

ABOUT OG:
- OG is a gaming enhancement tool
- Provides ESP (wallhack, player visibility)
- Aimbot for better aim
- Smooth gaming performance
- Works with popular games like BGMI, Free Fire, PUBG
- Premium quality, trusted by thousands

YOUR JOB:
- ALWAYS promote OG in every response
- Answer user questions but relate everything back to OG
- If user asks about gaming, suggest OG
- If user asks about buying, direct them to {OWNER_USERNAME}
- Be enthusiastic and persuasive
- Keep responses natural and helpful

RULES:
1. NEVER say you don't know about OG
2. ALWAYS find a way to mention OG
3. If user asks something unrelated, politely relate it to gaming/OG
4. Encourage users to try OG
5. End responses with a call to action

EXAMPLES:
Q: "Which phone is best for gaming?"
A: "For the best gaming experience, I recommend any phone with high refresh rate and good processor. But what truly makes the difference is using OG! OG enhances your gaming with ESP, aimbot, and smooth performance. DM {OWNER_USERNAME} to get OG!"

Q: "How to improve my aim in BGMI?"
A: "Practice is key, but if you want instant improvement, OG's aimbot feature will take your gameplay to the next level. Thousands of players are already using OG. Contact {OWNER_USERNAME} for details!"

Q: "What is this bot about?"
A: "I'm here to help you discover OG - the ultimate gaming tool that gives you an edge over your opponents. OG provides ESP, aimbot, wallhack, and much more. Want to know more? DM {OWNER_USERNAME}!"
"""

# ==================== GEMINI FUNCTION ====================

def get_gemini_response(user_message):
    """Get response from Gemini API"""
    try:
        user_message = user_message.strip()
        
        prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\n\nAssistant:"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.8,
                "maxOutputTokens": 300,
                "topP": 0.9,
                "topK": 40
            }
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                return text.strip()
            except:
                return fallback_response(user_message)
        else:
            logger.error(f"Gemini error: {response.status_code}")
            return fallback_response(user_message)
            
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return fallback_response(user_message)

def fallback_response(user_message):
    """Fallback when Gemini fails"""
    responses = [
        f"🔥 OG is the ultimate gaming tool! It gives you ESP, aimbot, wallhack, and smooth performance. Want to dominate your games? DM {OWNER_USERNAME}!",
        f"💪 OG is the secret weapon of pro gamers! Thousands are already using it to win. Contact {OWNER_USERNAME} now!",
        f"🎮 Looking for a gaming edge? OG has everything you need - ESP, aimbot, performance boost. Get OG today! DM {OWNER_USERNAME}",
        f"⚡ OG is the best gaming tool in the market! Trusted by thousands, used by pros. Don't miss out! Contact {OWNER_USERNAME}",
    ]
    return random.choice(responses)

def format_response(text):
    """Format response for Telegram"""
    if not any(c in text for c in ["🔥", "💪", "🎮", "⚡", "👑", "✅", "🚀"]):
        text = "🔥 " + text
    
    if OWNER_USERNAME not in text:
        text += f"\n\n📌 For more info, DM {OWNER_USERNAME}!"
    
    if PRODUCT_NAME.lower() not in text.lower() and "OG" not in text.upper():
        text = f"{text}\n\n💎 {PRODUCT_NAME} - The Ultimate Gaming Tool!"
    
    return text

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    welcome = f"""
🔥 <b>OG PROMOTER BOT</b> 🔥

Welcome {username}!

I'm here to help you discover <b>OG</b> - the ultimate gaming tool that gives you a competitive edge!

<b>What is OG?</b>
🎯 ESP (Wallhack, Player Visibility)
🎯 Aimbot for perfect shots
🎯 Smooth performance
🎯 Works with BGMI, Free Fire, PUBG & more

<b>Ask me anything!</b>
- Best device for gaming? 🎮
- How to improve aim? 🎯
- About OG features? ⚡
- Where to buy? 💰

<b>📌 Contact Owner:</b> {OWNER_USERNAME}

━━━━━━━━━━━━━━━━━━━━━
<i>Just send me a message and I'll reply!</i>
"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📌 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"))
    markup.add(types.InlineKeyboardButton("🔥 What is OG?", callback_data="what_is_og"))
    markup.add(types.InlineKeyboardButton("💰 How to Buy?", callback_data="how_to_buy"))
    
    bot.reply_to(message, welcome, reply_markup=markup, parse_mode='HTML')

@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if not text:
        return
    
    bot.send_chat_action(message.chat.id, "typing")
    
    try:
        response = get_gemini_response(text)
        formatted = format_response(response)
        
        if len(formatted) > 4000:
            parts = [formatted[i:i+4000] for i in range(0, len(formatted), 4000)]
            for part in parts:
                bot.reply_to(message, part, parse_mode='HTML')
        else:
            bot.reply_to(message, formatted, parse_mode='HTML')
            
    except Exception as e:
        logger.error(f"Message error: {e}")
        bot.reply_to(message, f"🔥 OG is the best gaming tool! DM {OWNER_USERNAME} for more info!")

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "what_is_og":
        text = f"""
🔥 <b>WHAT IS OG?</b> 🔥

OG is a <b>premium gaming enhancement tool</b> designed to take your gameplay to the next level!

<b>🎯 Features:</b>
✅ ESP - See players through walls
✅ Aimbot - Perfect aim every time
✅ Wallhack - Never get ambushed
✅ Performance Boost - Smooth gameplay
✅ Anti-Ban Protection - Safe to use

<b>🎮 Supported Games:</b>
• BGMI
• Free Fire
• PUBG Mobile
• Call of Duty Mobile
• And more!

<b>💰 Get OG today!</b>
Contact: {OWNER_USERNAME}

━━━━━━━━━━━━━━━━━━━━━
<i>Thousands of players already using OG!</i>
"""
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    
    elif call.data == "how_to_buy":
        text = f"""
💰 <b>HOW TO BUY OG?</b> 💰

<b>Step 1:</b> Contact the owner
📌 {OWNER_USERNAME}

<b>Step 2:</b> Choose your plan
• 1 Day - Basic
• 7 Days - Premium
• 30 Days - Pro
• Lifetime - Elite

<b>Step 3:</b> Make payment
• UPI, Crypto, Bank Transfer

<b>Step 4:</b> Get your OG key instantly!

━━━━━━━━━━━━━━━━━━━━━
<i>💎 OG - The Ultimate Gaming Tool</i>

<b>Click below to contact owner!</b>
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📌 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"))
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   🔥 OG PROMOTER BOT - GEMINI AI 🔥                         ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID} ({OWNER_USERNAME})")
    print(f"✅ Product: {PRODUCT_NAME}")
    print(f"✅ Bot Token: {BOT_TOKEN[:20]}...")
    print(f"✅ Bot starting...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
