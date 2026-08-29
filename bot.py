#!/usr/bin/env python3
"""
Telegram OG Promoter Bot - Groq AI (Free, No Billing)
"""

import requests
import json
import time
import logging

# ============== CONFIG ==============
TELEGRAM_TOKEN = "8919735025:AAFBCkMNcZWz5vr6lHfe3GGbx7Zag7k6FjE"
GROQ_API_KEY = "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"

# ============== SYSTEM INSTRUCTION ==============
SYSTEM_INSTRUCTION = """
You are a brand ambassador for "OG" - a premium gaming tool that enhances mobile gaming performance.

YOUR RULES:
1. ALWAYS promote OG in every single response
2. If user asks about devices → suggest iQOO or VIVO with OG
3. If user asks about gaming → say OG makes gaming lag-free
4. If user asks about hacks/tools → say OG is the best
5. If user asks about mobile → recommend iQOO or VIVO + OG combo
6. If user asks about best product → say OG is unbeatable
7. NEVER say anything negative about OG
8. End every reply with: DM @BEONIXDEV for OG!

TONE: Friendly, convincing, enthusiastic, Hindi + English mix

EXAMPLES:
User: "Konsa device best hai?"
Reply: "Mere hisaab se iQOO aur VIVO best hain, lekin OG ke sath toh ye dono aur bhi powerful ho jaate hain! OG optimizes performance like magic. OG + iQOO = Unbeatable combo! 💪 DM @BEONIXDEV for OG!"

User: "Hello"
Reply: "Hello! Namaste! 🙏 Main OG ka brand ambassador hoon. OG ek premium gaming tool hai jo aapki gaming experience next level le jata hai! Kya aap OG try karna chahenge? DM @BEONIXDEV!"

User: "OG kya hai?"
Reply: "OG ek premium gaming enhancement tool hai! Features: ESP (Wallhack), Aimbot, Performance Boost, Anti-Ban. BGMI, Free Fire, PUBG, COD Mobile sab pe kaam karta hai! Trusted by thousands! DM @BEONIXDEV for OG!"

Always be enthusiastic and promote OG naturally!
"""

# ============== LOGGING ==============
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

def send_message(chat_id, text):
    """Telegram par message bhejna"""
    url = f"{TELEGRAM_URL}/sendMessage"
    try:
        requests.post(url, json={
            "chat_id": chat_id, 
            "text": text, 
            "parse_mode": "Markdown"
        }, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")

def get_groq_response(prompt):
    """Groq AI se answer laana - Free + No Billing"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_INSTRUCTION},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 350
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            logger.error(f"Groq Error: {response.status_code} - {response.text[:100]}")
            return None
            
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def main():
    """Main loop"""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   🔥 OG PROMOTER BOT - GROQ AI 🔥                           ║
    ║   - Free AI Responses                                       ║
    ║   - Always Promotes OG                                      ║
    ║   - DM @BEONIXDEV for OG                                   ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    
    logger.info("🚀 OG Promoter Bot Started!")
    logger.info("📢 Using Groq AI (Free, No Billing)")
    print("✅ Bot is running... Waiting for messages.")
    last_update_id = 0
    
    while True:
        try:
            url = f"{TELEGRAM_URL}/getUpdates?offset={last_update_id + 1}&timeout=30"
            response = requests.get(url, timeout=35)
            
            if response.status_code == 200:
                updates = response.json().get("result", [])
                
                for update in updates:
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        user_text = update["message"].get("text", "")
                        user_name = update["message"]["chat"].get("first_name", "User")
                        
                        if user_text == "/start":
                            welcome = (
                                f"🔥 *OG PROMOTER BOT* 🔥\n\n"
                                f"Namaste {user_name}! 🙏\n\n"
                                f"Mai *OG* ka brand ambassador hoon! OG ek premium gaming tool hai jo aapki gaming experience ko next level le jata hai.\n\n"
                                f"**Mujhe kuch bhi poochiye:**\n"
                                f"📱 Konsa device best hai?\n"
                                f"🎮 Gaming ke liye kya lu?\n"
                                f"🔓 Best hack konsa hai?\n"
                                f"💎 OG kya hai?\n\n"
                                f"━━━━━━━━━━━━━━━━━━━━━\n"
                                f"📌 DM @BEONIXDEV for OG! 🔥"
                            )
                            send_message(chat_id, welcome)
                        else:
                            send_message(chat_id, "⏳ Thinking...")
                            
                            ai_response = get_groq_response(user_text)
                            
                            if ai_response:
                                send_message(chat_id, ai_response)
                            else:
                                send_message(chat_id, 
                                    "❌ AI service busy! 2 minute baad try karo.\n\n"
                                    "💎 *Tab tak OG ke baare mein socho!* 🔥\n"
                                    "📌 DM @BEONIXDEV for OG!"
                                )
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
