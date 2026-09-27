#!/usr/bin/env python3
"""
👑 THE KING OF INFORMATION - TEST
"""

import telebot
from telebot import types

BOT_TOKEN = "8415742587:AAFtsM3XYynwaWUhX_EgV4Wx2phx11uUK6U"
OWNER_ID = 8935807032

bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
except:
    pass

print("✅ Bot Starting...")

@bot.message_handler(commands=['start'])
def start(message):
    print(f"✅ /start received from {message.from_user.id}")
    
    if message.from_user.id == OWNER_ID:
        bot.reply_to(message, "👑 Owner Panel\n\nBot is working!")
    else:
        bot.reply_to(message, "👑 THE KING OF INFORMATION\n\nBot is working!")

@bot.message_handler(func=lambda m: True)
def echo(message):
    print(f"📩 Message: {message.text}")
    bot.reply_to(message, f"Echo: {message.text}")

print("✅ Bot is polling...")
while True:
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=10)
    except Exception as e:
        print(f"❌ Error: {e}")
