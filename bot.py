#!/usr/bin/env python3
"""
👑 THE KING OF INFORMATION - RAILWAY READY
Vehicle Number to Mobile + Telegram Bot
"""

import sys
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except:
    pass

import json
import re
import time
import base64
import threading
import urllib3
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Flask, request, jsonify
import telebot
from telebot import types

urllib3.disable_warnings()

# ==================== CONFIG ====================
BOT_TOKEN = "8415742587:AAFtsM3XYynwaWUhX_EgV4Wx2phx11uUK6U"
OWNER_ID = 8935807032
OWNER_USERNAME = "@VATEROFWHOLETG"

# ==================== VEHICLE API CONSTANTS ====================
P, C, S = '!~)#@*&^', 'b91c303443f61b37106750823881cd2f', 'de83eeeb148878ae375f28756492e8a0'
G = 'https://delhigw.napix.gov.in/nic/parivahan'
U = G + '/mparivahan/wrapperapi/vahan/vahancapi/updatemobile/getMobileNo'
HP = G + '/mparivahan/wrapperapi/vahan/vahancapi/hpt/search'
QC = G + '/mparivahan/wrapperapi/vahan/vahancapi/updatemobile/getclassanddescription'
A, V, DG, AL = 'okhttp/5.0.0-alpha.11', '2.0.142', '0123456789', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
ST = frozenset('AN AP AR AS BR CG CH DD DL DN GA GJ HP HR JH JK KA KL LA LD MH ML MN MP MZ NL OD OR PB PY RJ SK TN TR TS UA UK UP WB'.split())
O = {'HR26': '70', 'HR38': '70', 'HR55': '70', 'HR72': '70', 'HR76': '70', 'RJ60': '14', 'DL10': '10', 'DL1': '1', 'UK18': '18', 'UA18': '18'}
RX = re.compile(r'^(?:\d{2}BH\d{4}[A-Z]{2}|[A-Z]{2}\d{1,2}[A-Z]{0,3}\d{1,4}|[A-Z]{3}\d{1,4})$')

_lk = threading.Lock()
_tk = None
_ts = 0.0
_gs = None
_gx = None
_sem = threading.Semaphore(48)

# ==================== VEHICLE ENGINE ====================
def K(t):
    r = t[::-1]
    return ((r if len(r) <= 3 else r[:4] + r[-4:]) + P).encode()

def E(o, t):
    return base64.b64encode(
        base64.b64encode(
            AES.new(K(t), AES.MODE_ECB).encrypt(
                pad(json.dumps(o, separators=(',', ':')).encode(), 16)
            )
        )
    ).decode()

def X(b, t):
    raw = base64.b64decode(b)
    try:
        r2 = base64.b64decode(raw)
        if len(r2) % 16 == 0:
            raw = r2
    except:
        pass
    return json.loads(unpad(AES.new(K(t), AES.MODE_ECB).decrypt(raw), 16))

def N(r):
    return re.sub(r'[\s\-]', '', r.upper())

def STT(r):
    if re.match(r'^\d{2}BH', r):
        return 'DL'
    s = r[:2]
    return s if s in ST else 'DL'

def OS(x):
    if x is None or x == '':
        return
    try:
        return str(int(x))
    except:
        return str(x)

def PO(r):
    if re.match(r'^\d{2}BH', r):
        return
    for k, v in sorted(O.items(), key=lambda x: -len(x[0])):
        if r.startswith(k):
            return v
    m = re.match(r'^[A-Z]{2}(\d{1,2})', r)
    if m:
        d = m.group(1)
        return d.zfill(2) if len(d) == 1 else d
    m = re.search(r'(\d{1,2})', r[2:] if len(r) > 2 else r)
    if m:
        d = m.group(1)
        return d.zfill(2) if len(d) == 1 else d
    return '1'

def OF(r, e=None):
    o = []
    def a(x):
        x = OS(x)
        if x and x not in o:
            o.append(x)
    a(e)
    p = PO(r)
    if p:
        a(p)
        a(p.lstrip('0') or '0')
        a(str(p).zfill(2))
    for x in ('14', '10', '1', '16', '20', '70'):
        a(x)
    return o

def SS():
    global _gs
    if _gs is None:
        with _lk:
            if _gs is None:
                s = requests.Session()
                s.verify = False
                s.headers['User-Agent'] = A
                ad = requests.adapters.HTTPAdapter(pool_connections=48, pool_maxsize=48, max_retries=0)
                s.mount('https://', ad)
                s.mount('http://', ad)
                _gs = s
    return _gs

def GX(n=40):
    global _gx
    if _gx is None:
        _gx = ThreadPoolExecutor(max_workers=n)
    return _gx

def TK(f=0):
    global _tk, _ts
    with _lk:
        if not f and _tk and time.time() - _ts < 2800:
            return _tk
        for i in range(6):
            try:
                r = SS().post(
                    G + '/oauth2/token',
                    data={'grant_type': 'client_credentials', 'scope': 'napix', 'client_id': C, 'client_secret': S},
                    headers={'Content-Type': 'application/x-www-form-urlencoded', 'User-Agent': A},
                    timeout=(10, 25)
                )
                if r.status_code == 200:
                    t = r.json().get('access_token')
                    if t:
                        _tk, _ts = t, time.time()
                        return t
            except requests.RequestException:
                time.sleep(.2 * (i + 1))
        return None

def P1(u, t, o):
    ts = str(int(time.time() * 1000))
    h = {
        'Authorization': 'Bearer ' + t,
        'Timestamp': ts,
        'Param1': 'null',
        'Param2': V,
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json',
        'User-Agent': A
    }
    z = None
    for i in range(4):
        try:
            with _sem:
                z = SS().post(u, headers=h, data=json.dumps({'data': E(o, ts)}), timeout=(10, 25))
            break
        except requests.RequestException:
            time.sleep(.12 * (i + 1))
    return z, ts

def T1(r, o, c, t, s):
    z, ts = P1(U, t, {'regnNo': r, 'stateCode': s, 'chassisNo': str(c), 'officeCode': str(o), 'purCd': '135'})
    if z is None:
        return None, 0, 0
    if z.status_code == 401:
        return None, 0, 1
    if z.status_code != 200:
        return None, 0, 0
    try:
        d = X(z.json()['data'], ts)
    except:
        return None, 0, 0
    a = d.get('data') if isinstance(d, dict) else None
    ok = isinstance(a, dict) and a.get('mobileNo') not in (None, '')
    return (d if ok else None), int(ok), 0

def HO(r, t):
    z, ts = P1(HP, t, {'regnNo': r})
    if z is None or z.status_code != 200:
        return
    try:
        d = X(z.json()['data'], ts)
    except:
        return
    a = d.get('data') if isinstance(d, dict) else None
    h = a.get('hptdetails') if isinstance(a, dict) else None
    if isinstance(h, list):
        h = h[0] if h else None
    return OS(h.get('off_cd')) if isinstance(h, dict) else None

def EXS(r, t, s):
    z, ts = P1(QC, t, {'regnNo': r, 'stateCode': s})
    if z is None or z.status_code != 200:
        return 1
    try:
        d = X(z.json()['data'], ts)
    except:
        return 1
    m = d.get('apiMessage') if isinstance(d, dict) else None
    return isinstance(m, dict) and m.get('statusCode') == 200

def F(r, full=0):
    r = N(r)
    t = TK()
    if not t:
        return
    s = STT(r)
    sp = threading.Event()
    bx = []
    tr = set()

    def one(o, c):
        if sp.is_set():
            return
        d, ok, af = T1(r, o, c, t, s)
        if af:
            t2 = TK(1)
            if t2:
                d, ok, _ = T1(r, o, c, t2, s)
        if ok and d:
            bx.append(d)
            sp.set()

    def br(ofs, ch=DG):
        fs = []
        for o in ofs:
            o = OS(o)
            if not o:
                continue
            for c in ch:
                k = o + ':' + c
                if k in tr:
                    continue
                tr.add(k)
                fs.append(GX().submit(one, o, c))
        if not fs:
            return 0
        for f in as_completed(fs):
            if bx:
                sp.set()
                for x in fs:
                    x.cancel()
                return 1
        return int(bool(bx))

    p = PO(r)
    w = []
    if p:
        w.append(p)
        u = p.lstrip('0') or '0'
        if u != p:
            w.append(u)
    hf = GX().submit(HO, r, t)
    if br(w):
        return bx[0]
    try:
        hf = hf.result(timeout=8)
    except:
        hf = None
    if hf and br([hf]):
        return bx[0]
    if hf and br([hf], AL):
        return bx[0]
    if br(OF(r, hf)):
        return bx[0]
    if full:
        if not EXS(r, t, s):
            return
        if br([str(i) for i in range(1, 100)]):
            return bx[0]
    return bx[0] if bx else None

def mob(d):
    if d and isinstance(d.get('data'), dict):
        m = d['data'].get('mobileNo')
        if m not in (None, ''):
            return m

# ==================== FLASK API ====================
_stats = {'total': 0, 'found': 0, 'not_found': 0}
flask_app = Flask(__name__)

@flask_app.route('/api/<path:vehicle_number>', methods=['GET'])
def get_mobile(vehicle_number):
    _stats['total'] += 1
    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(F, vehicle_number, 1)
            res = future.result(timeout=20)
    except TimeoutError:
        _stats['not_found'] += 1
        return jsonify({'error': 'Lookup timeout'}), 408
    mobile = mob(res) if res else None
    if mobile:
        _stats['found'] += 1
        return jsonify({'vehicle': vehicle_number.upper(), 'mobile': mobile})
    _stats['not_found'] += 1
    return jsonify({'error': 'Not found'}), 404

@flask_app.route('/stats', methods=['GET'])
def get_stats():
    return jsonify(_stats)

@flask_app.route('/')
def root_route():
    return jsonify({'status': 'API running', 'endpoints': ['/api/<vehicle>', '/stats']})

def run_flask():
    flask_app.run(host='0.0.0.0', port=6958, debug=False, use_reloader=False)

# ==================== TELEGRAM BOT ====================
print("✅ Imports OK")

bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
    print("✅ Webhook removed")
except Exception as e:
    print(f"⚠️ Webhook: {e}")

print("✅ Bot initialized")

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        if user_id == OWNER_ID:
            bot.reply_to(message, f"""👑 <b>OWNER PANEL</b>

✅ Bot is working!
🆔 Owner ID: <code>{OWNER_ID}</code>
🔧 API: Running on port 6958

<b>Commands:</b>
/start - This menu
/ping - Check bot
/search HR26AB1234 - Search vehicle
""", parse_mode='HTML')
        else:
            bot.reply_to(message, f"""👑 <b>THE KING OF INFORMATION</b>

Namaste! Welcome.

📌 <b>Owner:</b> {OWNER_USERNAME}

Bot is working! 🚀
""", parse_mode='HTML')
    except Exception as e:
        print(f"❌ Start error: {e}")

@bot.message_handler(commands=['ping'])
def ping(message):
    try:
        bot.reply_to(message, f"🏓 Pong! Bot is running.\n⏱ {time.strftime('%H:%M:%S')}")
    except Exception as e:
        print(f"❌ Ping error: {e}")

@bot.message_handler(commands=['search'])
def search_cmd(message):
    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /search HR26AB1234")
            return
        vehicle = N(parts[1].strip())
        if not RX.match(vehicle):
            bot.reply_to(message, "❌ Invalid vehicle number format.")
            return
        msg = bot.reply_to(message, f"🔍 Searching {vehicle}...")
        with ThreadPoolExecutor(max_workers=1) as ex:
            future = ex.submit(F, vehicle, 1)
            result = future.result(timeout=25)
        mobile = mob(result) if result else None
        if mobile:
            bot.edit_message_text(f"✅ <b>FOUND!</b>\n\n🚗 Vehicle: <code>{vehicle}</code>\n📱 Mobile: <code>{mobile}</code>",
                                  message.chat.id, msg.message_id, parse_mode='HTML')
        else:
            bot.edit_message_text(f"❌ Mobile number not found for {vehicle}",
                                  message.chat.id, msg.message_id)
    except TimeoutError:
        bot.reply_to(message, "⏱ Timeout. Try again.")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(func=lambda m: True)
def echo(message):
    try:
        bot.reply_to(message, f"📩 Received: {message.text}\n\n👑 THE KING OF INFORMATION")
    except Exception as e:
        print(f"❌ Echo error: {e}")

# ==================== TOKEN FETCH (BACKGROUND) ====================
def init_token_bg():
    print("⏳ Fetching API token...")
    try:
        if TK():
            print("✅ API Token ready!")
        else:
            print("⚠️ API Token failed - will retry on demand")
    except Exception as e:
        print(f"⚠️ Token error: {e}")

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   👑 THE KING OF INFORMATION - RAILWAY                      ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Bot Token: {BOT_TOKEN[:20]}...")

    # Flask start in background
    threading.Thread(target=run_flask, daemon=True).start()
    print("✅ Flask API started on port 6958")

    # Token fetch in background (non-blocking)
    threading.Thread(target=init_token_bg, daemon=True).start()

    print("✅ Bot is now polling...")

    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=10)
        except Exception as e:
            print(f"❌ Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
