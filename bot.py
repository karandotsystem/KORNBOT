#!/usr/bin/env python3
"""
🔥 OG PROMOTER BOT - GEMINI AI WORKING 🔥
"""

import os
import time
import json
import logging
import requests
import random
import re
from datetime import datetime
import telebot
from telebot import types

# ==================== CONFIG ====================
BOT_TOKEN = "8919735025:AAFBCkMNcZWz5vr6lHfe3GGbx7Zag7k6FjE"
OWNER_ID = 8935807032
OWNER_USERNAME = "@BEONIXDEV"
PRODUCT_NAME = "OG"

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

print("✅ Bot Started!")

# ==================== SYSTEM PROMPT ====================
SYSTEM_PROMPT = f"""
You are "OG Bot" - a marketing assistant for OG, the premium gaming tool.

IMPORTANT RULES:
1. ALWAYS respond in HINDI or ENGLISH (user ki language follow karo)
2. ALWAYS mention OG in every response
3. ALWAYS end with DM @BEONIXDEV for buying
4. Be helpful and enthusiastic

ABOUT OG:
- OG is a premium gaming enhancement tool
- Features: ESP (wallhack), Aimbot, Performance Boost
- Works with BGMI, Free Fire, PUBG Mobile, COD Mobile
- Trusted by thousands of gamers
- Available for Android devices

RESPONSE STYLE:
- Friendly and helpful
- Promote OG naturally
- Answer user questions directly
- Include OG features in replies

EXAMPLES:
User: "OG kya hai?"
Reply: "OG ek premium gaming tool hai jo aapko ESP, aimbot, aur smooth performance deta hai. BGMI, Free Fire, PUBG sab pe kaam karta hai. Trusted by thousands! Buy karne ke liye DM @BEONIXDEV"

User: "OG konse device me acha chalega?"
Reply: "OG Android devices pe best kaam karta hai! 4GB RAM+ wale phones pe smooth experience milega. Kisi bhi gaming phone ke saath OG use karo aur game change ho jayega. DM @BEONIXDEV for details!"

User: "OG ka owner kon hai?"
Reply: "OG ke owner @BEONIXDEV hain! Woh OG ke creator aur developer hain. Koi bhi query ho toh unko DM karo. They will guide you!"

User: "OG Kidher se Lena chahiye?"
Reply: "OG sirf official channel se milega! Owner @BEONIXDEV ko DM karo aur apna OG key le lo. Only genuine keys available. DM now!"
"""

# ==================== GEMINI FUNCTION ====================

def get_gemini_response(user_message):
    """Get response from Gemini API"""
    try:
        user_message = user_message.strip()
        
        prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_message}\n\nBot:"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 500,
                "topP": 0.9,
                "topK": 40
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        print(f"[*] Sending to Gemini: {user_message[:50]}...")
        response = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=30)
        
        print(f"[*] Gemini Response Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"[*] Gemini Response: {str(data)[:200]}...")
            
            try:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                # Clean the response
                text = text.replace("Bot:", "").replace("Assistant:", "").strip()
                return text
            except Exception as e:
                print(f"[-] Parse error: {e}")
                return get_fallback_response(user_message)
        else:
            print(f"[-] Gemini Error: {response.text[:200]}")
            return get_fallback_response(user_message)
            
    except Exception as e:
        print(f"[-] Gemini Exception: {e}")
        return get_fallback_response(user_message)

def get_fallback_response(user_message):
    """Smart fallback responses"""
    msg_lower = user_message.lower()
    
    if "kya hai" in msg_lower or "what is" in msg_lower:
        return f"""🔥 OG ek premium gaming tool hai!

✅ ESP (Wallhack) - Sabko dekh sakte ho
✅ Aimbot - Perfect aim
✅ Performance Boost - Smooth game
✅ Anti-Ban - Safe to use

BGMI, Free Fire, PUBG, COD Mobile sab pe kaam karta hai!

📌 Buy: DM {OWNER_USERNAME}"""
    
    elif "device" in msg_lower or "phone" in msg_lower or "mobile" in msg_lower:
        return f"""📱 OG Android devices pe best kaam karta hai!

🔹 4GB RAM+ recommended
🔹 Any gaming phone
🔹 Smooth experience guaranteed

OG ke saath koi bhi phone gaming beast ban jata hai!

📌 DM {OWNER_USERNAME} for details!"""
    
    elif "owner" in msg_lower or "owner" in msg_lower or "creator" in msg_lower:
        return f"""👑 OG ke owner aur creator: {OWNER_USERNAME}

Woh OG ke developer hain aur personally handle karte hain.

📌 Any query? DM {OWNER_USERNAME} directly!"""
    
    elif "buy" in msg_lower or "lena" in msg_lower or "kharid" in msg_lower:
        return f"""💰 OG lena hai? Simple!

✅ DM {OWNER_USERNAME}
✅ Choose your plan:
   • 1 Day - Trial
   • 7 Days - Premium  
   • 30 Days - Pro
   • Lifetime - Elite

✅ Payment: UPI, Crypto, Bank Transfer
✅ Instant delivery!

📌 DM {OWNER_USERNAME} now!"""
    
    elif "price" in msg_lower or "rate" in msg_lower or "kitna" in msg_lower:
        return f"""💎 OG Plans:

🔹 1 Day - ₹XX
🔹 7 Days - ₹XX
🔹 30 Days - ₹XX
🔹 Lifetime - ₹XX

Best value: Lifetime plan!

📌 DM {OWNER_USERNAME} for current prices!"""
    
    else:
        return f"""🔥 OG - The Ultimate Gaming Tool!

✅ ESP (Wallhack)
✅ Aimbot
✅ Performance Boost
✅ BGMI, Free Fire, PUBG, COD

Thousands of gamers already using OG!

📌 DM {OWNER_USERNAME} to get OG!"""

def format_response(text):
    """Format response for Telegram"""
    # Remove any extra prefixes
    text = re.sub(r'^(Bot:|Assistant:|OG Bot:)', '', text).strip()
    
    # Ensure owner mention is included
    if OWNER_USERNAME not in text:
        text += f"\n\n📌 DM {OWNER_USERNAME} for OG!"
    
    # Ensure product name is mentioned
    if "OG" not in text:
        text = f"💎 OG - The Ultimate Gaming Tool!\n\n{text}"
    
    return text

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    username = message.from_user.username or "User"
    
    welcome = f"""
🔥 <b>OG PROMOTER BOT</b> 🔥

Welcome {username}! 🎮

I'm here to tell you about <b>OG</b> - the ultimate gaming tool!

<b>What is OG?</b>
✅ ESP (Wallhack)
✅ Aimbot
✅ Performance Boost
✅ Works with BGMI, Free Fire, PUBG & more

<b>Ask me anything:</b>
• OG kya hai? 🔥
• Konse device pe chalta hai? 📱
• Owner kon hai? 👑
• Kidher se lena hai? 💰
• Price kya hai? 💎

━━━━━━━━━━━━━━━━━━━━━
<i>Just send me your question!</i>
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
        # Try Gemini first
        response = get_gemini_response(text)
        
        # If Gemini returned fallback or empty, use smart fallback
        if not response or len(response) < 10:
            response = get_fallback_response(text)
        
        formatted = format_response(response)
        
        if len(formatted) > 4000:
            parts = [formatted[i:i+4000] for i in range(0, len(formatted), 4000)]
            for part in parts:
                bot.reply_to(message, part, parse_mode='HTML')
        else:
            bot.reply_to(message, formatted, parse_mode='HTML')
            
    except Exception as e:
        print(f"[-] Message error: {e}")
        fallback = get_fallback_response(text)
        bot.reply_to(message, fallback, parse_mode='HTML')

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    if call.data == "what_is_og":
        text = f"""
🔥 <b>WHAT IS OG?</b> 🔥

OG is a <b>premium gaming enhancement tool</b>!

<b>🎯 Features:</b>
✅ ESP - See players through walls
✅ Aimbot - Perfect aim
✅ Wallhack - Never get ambushed
✅ Performance Boost - Smooth gameplay
✅ Anti-Ban - Safe to use

<b>🎮 Supported Games:</b>
• BGMI
• Free Fire
• PUBG Mobile
• COD Mobile
• And more!

<b>💰 Get OG today!</b>
📌 {OWNER_USERNAME}
"""
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')
    
    elif call.data == "how_to_buy":
        text = f"""
💰 <b>HOW TO BUY OG?</b> 💰

<b>Step 1:</b> Contact owner
📌 {OWNER_USERNAME}

<b>Step 2:</b> Choose plan
• 1 Day - Trial
• 7 Days - Premium
• 30 Days - Pro
• Lifetime - Elite

<b>Step 3:</b> Payment
• UPI, Crypto, Bank Transfer

<b>Step 4:</b> Get OG key instantly!

━━━━━━━━━━━━━━━━━━━━━
<i>💎 OG - The Ultimate Gaming Tool</i>
"""
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📌 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"))
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, text, reply_markup=markup, parse_mode='HTML')

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   🔥 OG PROMOTER BOT - GEMINI AI WORKING 🔥                 ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID} ({OWNER_USERNAME})")
    print(f"✅ Product: {PRODUCT_NAME}")
    print(f"✅ Bot starting...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
