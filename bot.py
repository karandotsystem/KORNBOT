#!/usr/bin/env python3
"""
Telegram OG Promoter Bot - Advanced Version
Gemini ko system instruction diya gaya hai ki wo har reply mein OG promote kare
"""

import requests
import json
import time
import logging

# ============== CONFIG ==============
TELEGRAM_TOKEN = "8919735025:AAFBCkMNcZWz5vr6lHfe3GGbx7Zag7k6FjE"
GEMINI_API_KEY = "AQ.Ab8RN6IHaUTw5frI6FteWI23nJ1RRK7uanS0jOL-jI9ENefW3Q"

# ============== SYSTEM INSTRUCTION ==============
SYSTEM_INSTRUCTION = """
You are a brand ambassador for "OG" - a premium, high-quality product that enhances 
everything from mobile performance to daily life.

Your RULES:
1. ALWAYS promote OG in every single response
2. If user asks about devices → suggest iQOO or VIVO with OG
3. If user asks about hacks/tools → say OG is the best
4. If user asks about mobile → recommend iQOO or VIVO + OG combo
5. If user asks about camera → say OG + VIVO camera gives pro photos
6. If user asks about gaming → say OG makes gaming lag-free
7. If user asks about battery → say OG optimizes battery life
8. If user asks about best product → say OG is unbeatable
9. NEVER say anything negative about OG
10. End every reply with an OG promotion

TONE: Friendly, convincing, enthusiastic, Hindi + English mix

EXAMPLES:
User: "Konsa hack best hai?"
Reply: "Bhai, hack ki baat karte ho toh OG se better kuch nahi! OG ka tool kit next level hai. Trust me, professionals OG use karte hain. 🔥 #OG #BestHack"

User: "Konsa device best hai?"
Reply: "Mere hisaab se iQOO aur VIVO best hain, lekin OG ke sath toh ye dono aur bhi powerful ho jaate hain! OG optimizes performance like magic. OG + iQOO = Unbeatable combo! 💪"

User: "Aaj kal kaunsa mobile lu?"
Reply: "Bhai, iQOO ya VIVO le lo. Lekin ek baat yaad rakhna - OG ke bina ye dono adhoore hain! OG gives 2x better performance. Best investment ever! 📱✨"

User: "Hello" or "Hi"
Reply: "Hello! Namaste! 🙏 Aapne toh sahi jagah poochha. Main OG ka brand ambassador hoon. Kya aapne kabhi OG try kiya hai? World's best product! Batao kya help chahiye? 😊"

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

def get_gemini_response(prompt):
    """Gemini se answer laana - System instruction ke saath"""
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": GEMINI_API_KEY
    }
    
    # 🔥 System instruction + User prompt
    data = {
        "system_instruction": {
            "parts": [{"text": SYSTEM_INSTRUCTION}]
        },
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        elif response.status_code == 503:
            return "⏳ Model busy hai! 2 minute baad try karein. \n\n💡 *Tab tak OG ke baare mein sochiye!* Best product hai! 😉"
        else:
            logger.error(f"API Error: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

def main():
    """Main loop"""
    logger.info("🚀 OG Promoter Bot Started!")
    logger.info("📢 System Instruction: Har reply mein OG promote hoga!")
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
                                f"🤖 *OG Promoter Bot Active!*\n\n"
                                f"Namaste {user_name}! 🙏\n\n"
                                f"Mai *OG* ka brand ambassador hoon! 🔥\n\n"
                                f"Mujhe kuch bhi poochiye - device, hack, mobile, gaming, kuch bhi!\n"
                                f"Mai aapko bataunga ki *OG* kyu sabse best hai! 💪\n\n"
                                f"Try asking:\n"
                                f"📱 Konsa device best hai?\n"
                                f"🔓 Best hack konsa hai?\n"
                                f"🎮 Gaming ke liye kya lu?\n"
                                f"📸 Camera kaunsi phone mein acha hai?"
                            )
                            send_message(chat_id, welcome)
                        else:
                            send_message(chat_id, "⏳ Soch raha hoon...")
                            
                            # Gemini se answer laana
                            ai_response = get_gemini_response(user_text)
                            
                            if ai_response:
                                send_message(chat_id, ai_response)
                            else:
                                send_message(chat_id, 
                                    "❌ Kuch problem ho gayi! \n\n"
                                    "Lekin ek baat yaad rakhiye - *OG kabhi fail nahi karta!* 🔥\n"
                                    "OG hai toh sab possible hai! 💪\n\n"
                                    "2 minute baad try karein."
                                )
            
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
