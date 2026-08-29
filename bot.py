import requests
import telebot
import json
import os

# ==================== CONFIG LOAD ====================
# Railway pe config.json same folder mein hona chahiye
with open('config.json', 'r') as f:
    config = json.load(f)

# ==================== CREDENTIALS ====================
BOT_TOKEN = "8919735025:AAFBCkMNcZWz5vr6lHfe3GGbx7Zag7k6FjE"
GEMINI_API_KEY = "AQ.Ab8RN6JPGFWSkPpuLmAZE9jZGPQqkkratKJ8Etvvx8-T3d0dJw"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

bot = telebot.TeleBot(BOT_TOKEN)

# ==================== CONFIG VARIABLES ====================
SYSTEM_PROMPT = config.get('system_prompt', "You are a helpful assistant.")
CUSTOM_REPLIES = config.get('custom_replies', {})

# ==================== GEMINI CALL ====================
def ask_gemini(user_input):
    # Pehle custom reply check karo
    for key in CUSTOM_REPLIES:
        if key.lower() in user_input.lower():
            return CUSTOM_REPLIES[key]
    
    # Agar custom reply nahi mila toh Gemini se pucho
    full_prompt = f"{SYSTEM_PROMPT}\n\nUser: {user_input}\nReply:"
    payload = {"contents": [{"parts": [{"text": full_prompt}]}]}
    
    try:
        response = requests.post(GEMINI_URL, json=payload, timeout=15)
        if response.status_code == 200:
            data = response.json()
            reply = data["candidates"][0]["content"]["parts"][0]["text"]
            return reply
        else:
            return f"⚠️ API Error: {response.status_code}"
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# ==================== BOT HANDLER ====================
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_input = message.text
    if not user_input:
        return
    
    bot.reply_to(message, "⏳ Thinking...")
    reply = ask_gemini(user_input)
    bot.reply_to(message, reply)

# ==================== START ====================
print("✅ OG CHEATS Bot is running...")
print("📁 Config loaded:", config)
bot.polling()
