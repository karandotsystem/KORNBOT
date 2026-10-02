"""
⚡ SERIES GEN BOT
aiogram 3 · SQLite · Railway-ready (long polling)

Owner ID and Bot Token are hardcoded below.
ENV VARS (optional overrides):
  BOT_TOKEN          override the hardcoded token
  OWNER_ID           override the hardcoded owner id(s)
  CONTACT_USERNAME   username shown on the "Buy Key" button, without @
  BRAND_NAME         title shown in the UI
  DB_PATH            default /data/bot.db if /data exists, else ./bot.db
  TZ_NAME            default Asia/Kolkata
"""
import asyncio
import logging
import os
import re
import secrets
import time
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import aiosqlite
from aiogram import BaseMiddleware, Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction, ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter
from aiogram.filters import BaseFilter, Command, CommandObject, CommandStart
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# ───────────────────────── CONFIG ─────────────────────────
# Hardcoded values — used unless overridden by environment variables.
DEFAULT_BOT_TOKEN = "8213885965:AAGVn0yLiWASlyJ_wkX5g9GzTQnW5MhBbgw"
DEFAULT_OWNER_ID = "8542817214"

BOT_TOKEN = os.getenv("BOT_TOKEN", DEFAULT_BOT_TOKEN).strip()
OWNER_IDS = {int(x) for x in re.findall(r"\d+", os.getenv("OWNER_ID", DEFAULT_OWNER_ID))}
CONTACT = os.getenv("CONTACT_USERNAME", "").lstrip("@").strip()
BRAND = os.getenv("BRAND_NAME", "SERIES GEN")
TZ = ZoneInfo(os.getenv("TZ_NAME", "Asia/Kolkata"))
DB_PATH = os.getenv("DB_PATH") or ("/data/bot.db" if os.path.isdir("/data") else "bot.db")

SERIES_START, SERIES_END = 1, 9999  # set SERIES_START = 0 to include 0000
KEY_PREFIX = "SG"
KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
GEN_COOLDOWN = 2.0  # seconds between generations per user
LINE = "━━━━━━━━━━━━━━━━━━"

KEY_RE = re.compile(rf"^{KEY_PREFIX}-(?:7|30)D-[A-Z0-9]{{5}}-[A-Z0-9]{{5}}-[A-Z0-9]{{5}}$")
PREFIX_RE = re.compile(r"^\s*[A-Za-z0-9]{6}\s*$")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("seriesgen")

# ───────────────────────── DATABASE ─────────────────────────
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
  user_id    INTEGER PRIMARY KEY,
  username   TEXT,
  first_name TEXT,
  expires_at INTEGER NOT NULL DEFAULT 0,
  banned     INTEGER NOT NULL DEFAULT 0,
  gens       INTEGER NOT NULL DEFAULT 0,
  joined_at  INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS keys(
  key        TEXT PRIMARY KEY,
  days       INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  used_by    INTEGER,
  used_at    INTEGER
);
"""

db: aiosqlite.Connection = None  # type: ignore
LOCK = asyncio.Lock()
FAILS: dict[int, list[float]] = {}
LAST_GEN: dict[int, float] = {}


async def init_db():
    global db
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA synchronous=NORMAL")
    await db.executescript(SCHEMA)
    await db.commit()
    log.info("DB ready at %s", DB_PATH)


def now() -> int:
    return int(time.time())


async def get_user(uid: int):
    cur = await db.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return await cur.fetchone()


async def ensure_user(uid: int):
    await db.execute(
        "INSERT OR IGNORE INTO users(user_id, joined_at) VALUES(?,?)", (uid, now())
    )
    await db.commit()


async def touch_user(u):
    row = await get_user(u.id)
    if row is None:
        await db.execute(
            "INSERT INTO users(user_id, username, first_name, joined_at) VALUES(?,?,?,?)",
            (u.id, u.username, u.first_name, now()),
        )
        await db.commit()
        return await get_user(u.id)
    if row["username"] != u.username or row["first_name"] != u.first_name:
        await db.execute(
            "UPDATE users SET username=?, first_name=? WHERE user_id=?",
            (u.username, u.first_name, u.id),
        )
        await db.commit()
    return row


async def make_keys(days: int, n: int) -> list[str]:
    t = now()
    rows = []
    for _ in range(n):
        body = "-".join(
            "".join(secrets.choice(KEY_ALPHABET) for _ in range(5)) for _ in range(3)
        )
        rows.append((f"{KEY_PREFIX}-{days}D-{body}", days, t))
    await db.executemany("INSERT INTO keys(key, days, created_at) VALUES(?,?,?)", rows)
    await db.commit()
    return [r[0] for r in rows]


async def redeem_key(uid: int, key: str):
    async with LOCK:
        cur = await db.execute("SELECT days, used_by FROM keys WHERE key=?", (key,))
        k = await cur.fetchone()
        if k is None:
            return "invalid", 0, 0
        if k["used_by"] is not None:
            return "used", 0, 0
        row = await get_user(uid)
        t = now()
        new_exp = max(t, row["expires_at"]) + k["days"] * 86400
        await db.execute("UPDATE keys SET used_by=?, used_at=? WHERE key=?", (uid, t, key))
        await db.execute("UPDATE users SET expires_at=? WHERE user_id=?", (new_exp, uid))
        await db.commit()
        return "ok", k["days"], new_exp


async def scalar(q: str, *a):
    cur = await db.execute(q, a)
    r = await cur.fetchone()
    return (r[0] or 0) if r else 0


# ───────────────────────── HELPERS ─────────────────────────
def fmt_left(sec: int) -> str:
    if sec <= 0:
        return "—"
    d, r = divmod(sec, 86400)
    h, r = divmod(r, 3600)
    m = r // 60
    return f"{d}d {h}h {m}m" if d else f"{h}h {m}m"


def fmt_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%d %b %Y, %I:%M %p")


def has_access(uid: int, row) -> bool:
    return uid in OWNER_IDS or (row is not None and row["expires_at"] > now())


def plan_info(uid: int, row):
    if uid in OWNER_IDS:
        return "👑 OWNER", "Unlimited"
    left = row["expires_at"] - now()
    if left > 0:
        return "🟢 ACTIVE", fmt_left(left)
    return "🔴 NO PLAN", "—"


def build_series(prefix: str) -> bytes:
    return "\n".join(f"{prefix}{i:04d}" for i in range(SERIES_START, SERIES_END + 1)).encode()


def btn(text: str, data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=data)


# ───────────────────────── KEYBOARDS ─────────────────────────
def kb_main(uid: int) -> InlineKeyboardMarkup:
    rows = [
        [btn("⚡ Generate Series", "gen"), btn("🔑 Redeem Key", "redeem")],
        [btn("💎 My Plan", "plan"), btn("📖 Help", "help")],
    ]
    if CONTACT:
        rows.append([InlineKeyboardButton(text="🛒 Buy Key", url=f"https://t.me/{CONTACT}")])
    if uid in OWNER_IDS:
        rows.append([btn("👑 Owner Panel", "owner")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[btn("⬅️ Back", "home")]])


def kb_locked() -> InlineKeyboardMarkup:
    rows = [[btn("🔑 Redeem Key", "redeem")]]
    if CONTACT:
        rows.append([InlineKeyboardButton(text="🛒 Buy Key", url=f"https://t.me/{CONTACT}")])
    rows.append([btn("⬅️ Back", "home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_owner() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [btn("📊 Stats", "own_stats"), btn("📜 Unused Keys", "own_keys")],
            [btn("➕ 7-Day Key", "own_k7"), btn("➕ 30-Day Key", "own_k30")],
            [btn("⬅️ Back", "home")],
        ]
    )


# ───────────────────────── SCREENS ─────────────────────────
def home_text(user, row) -> str:
    status, left = plan_info(user.id, row)
    return (
        f"⚡ <b>{escape(BRAND)}</b> ⚡\n{LINE}\n"
        f"✨ <i>Lightning-fast series generator</i>\n\n"
        f"👤 <b>{escape(user.first_name or 'User')}</b>\n"
        f"💎 Plan  ›  <b>{status}</b>\n"
        f"⏳ Left  ›  <b>{left}</b>\n{LINE}\n"
        f"📩 Send a <b>6-character prefix</b>\n"
        f"like <code>GJ04AB</code> and get\n"
        f"<b>{SERIES_START:04d} ➜ {SERIES_END:04d}</b> instantly 🚀"
    )


def plan_text(user, row) -> str:
    status, left = plan_info(user.id, row)
    if user.id in OWNER_IDS:
        exp = "Never"
    elif row["expires_at"] == 0:
        exp = "—"
    elif row["expires_at"] > now():
        exp = fmt_date(row["expires_at"])
    else:
        exp = f"Expired · {fmt_date(row['expires_at'])}"
    return (
        f"💎 <b>MY PLAN</b>\n{LINE}\n"
        f"🆔 ID  ›  <code>{user.id}</code>\n"
        f"📶 Status  ›  <b>{status}</b>\n"
        f"⏳ Left  ›  <b>{left}</b>\n"
        f"📅 Expires  ›  <b>{exp}</b>\n"
        f"📦 Series made  ›  <b>{row['gens']}</b>"
    )


LOCKED_TEXT = (
    f"🔒 <b>ACCESS LOCKED</b>\n{LINE}\n"
    "You need an active plan to generate series.\n\n"
    "💎 <b>Available plans</b>\n"
    " ├ 🥉 <b>7 Days</b>\n"
    " └ 🥇 <b>30 Days</b>\n\n"
    "🔑 Got a key? Send it here or tap <b>Redeem Key</b>."
)

GEN_PROMPT = (
    f"⚡ <b>GENERATE SERIES</b>\n{LINE}\n"
    "Send your <b>6-character prefix</b> now 👇\n\n"
    "🧬 Example  ›  <code>GJ04AB</code>\n"
    f"📦 Output  ›  <code>GJ04AB{SERIES_START:04d}</code> ➜ <code>GJ04AB{SERIES_END:04d}</code>\n"
    "📄 Delivered as a <b>.txt</b> file"
)

REDEEM_PROMPT = (
    f"🔑 <b>REDEEM KEY</b>\n{LINE}\n"
    "Send your key in this chat 👇\n\n"
    f"🧬 Format  ›  <code>{KEY_PREFIX}-7D-XXXXX-XXXXX-XXXXX</code>\n"
    "⏳ Keys stack — redeeming again <b>extends</b> your plan."
)

HELP_TEXT = (
    f"📖 <b>HELP</b>\n{LINE}\n"
    "1️⃣ Get a <b>7-day</b> or <b>30-day</b> key\n"
    "2️⃣ Send the key here to activate\n"
    "3️⃣ Send a <b>6-character prefix</b>\n"
    "4️⃣ Receive your <b>.txt</b> series file\n\n"
    "⌨️ <b>Commands</b>\n"
    " /start  ·  menu\n"
    " /gen <code>GJ04AB</code>  ·  generate\n"
    " /redeem <code>KEY</code>  ·  activate key\n"
    " /plan  ·  your plan"
)


async def owner_text() -> str:
    return (
        f"👑 <b>OWNER PANEL</b>\n{LINE}\n"
        "🔑 /genkey <code>7|30 [count]</code>\n"
        "📜 /keys  ·  unused keys\n"
        "🗑 /delkey <code>KEY</code>\n"
        "🎁 /grant <code>ID DAYS</code>\n"
        "⛔ /revoke <code>ID</code>\n"
        "🚫 /ban <code>ID</code>  ·  ✅ /unban <code>ID</code>\n"
        "🔎 /user <code>ID</code>\n"
        "📣 /broadcast <code>text</code> (or reply to a message)\n"
        "📊 /stats"
    )


async def stats_text() -> str:
    t = now()
    total = await scalar("SELECT COUNT(*) FROM users")
    active = await scalar("SELECT COUNT(*) FROM users WHERE expires_at>?", t)
    banned = await scalar("SELECT COUNT(*) FROM users WHERE banned=1")
    gens = await scalar("SELECT SUM(gens) FROM users")
    k7 = await scalar("SELECT COUNT(*) FROM keys WHERE used_by IS NULL AND days=7")
    k30 = await scalar("SELECT COUNT(*) FROM keys WHERE used_by IS NULL AND days=30")
    used = await scalar("SELECT COUNT(*) FROM keys WHERE used_by IS NOT NULL")
    return (
        f"📊 <b>STATS</b>\n{LINE}\n"
        f"👥 Users  ›  <b>{total}</b>\n"
        f"🟢 Active  ›  <b>{active}</b>\n"
        f"🚫 Banned  ›  <b>{banned}</b>\n"
        f"📦 Series made  ›  <b>{gens}</b>\n{LINE}\n"
        f"🥉 Unused 7D keys  ›  <b>{k7}</b>\n"
        f"🥇 Unused 30D keys  ›  <b>{k30}</b>\n"
        f"✅ Redeemed keys  ›  <b>{used}</b>"
    )


def keys_text(days: int, keys: list[str]) -> str:
    body = "\n".join(f"<code>{k}</code>" for k in keys)
    return (
        f"🔑 <b>{len(keys)} × {days}-DAY KEY</b>\n{LINE}\n{body}\n{LINE}\n"
        "<i>Tap a key to copy</i>"
    )


async def show(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try:
        await cb.message.edit_text(text, reply_markup=kb)
    except TelegramBadRequest:
        pass
    await cb.answer()


# ───────────────────────── MIDDLEWARE / FILTERS ─────────────────────────
class Gate(BaseMiddleware):
    """Registers users, blocks banned ones, injects `urow`."""

    async def __call__(self, handler, event, data):
        u = data.get("event_from_user")
        if u is None or u.is_bot:
            return await handler(event, data)
        row = await touch_user(u)
        if row["banned"] and u.id not in OWNER_IDS:
            return None
        data["urow"] = row
        return await handler(event, data)


class IsOwner(BaseFilter):
    async def __call__(self, event) -> bool:
        return bool(event.from_user) and event.from_user.id in OWNER_IDS


owner = Router()
owner.message.filter(IsOwner())
owner.callback_query.filter(IsOwner())
user = Router()


# ───────────────────────── USER HANDLERS ─────────────────────────
@user.message(CommandStart())
async def cmd_start(m: Message, urow):
    await m.answer(home_text(m.from_user, urow), reply_markup=kb_main(m.from_user.id))


@user.message(Command("help"))
async def cmd_help(m: Message):
    await m.answer(HELP_TEXT, reply_markup=kb_back())


@user.message(Command("plan"))
async def cmd_plan(m: Message, urow):
    await m.answer(plan_text(m.from_user, urow), reply_markup=kb_back())


@user.callback_query(F.data == "home")
async def cb_home(cb: CallbackQuery, urow):
    await show(cb, home_text(cb.from_user, urow), kb_main(cb.from_user.id))


@user.callback_query(F.data == "plan")
async def cb_plan(cb: CallbackQuery, urow):
    await show(cb, plan_text(cb.from_user, urow), kb_back())


@user.callback_query(F.data == "help")
async def cb_help(cb: CallbackQuery):
    await show(cb, HELP_TEXT, kb_back())


@user.callback_query(F.data == "gen")
async def cb_gen(cb: CallbackQuery, urow):
    if has_access(cb.from_user.id, urow):
        await show(cb, GEN_PROMPT, kb_back())
    else:
        await show(cb, LOCKED_TEXT, kb_locked())


@user.callback_query(F.data == "redeem")
async def cb_redeem(cb: CallbackQuery):
    await show(cb, REDEEM_PROMPT, kb_back())


async def handle_redeem(m: Message, key: str):
    uid = m.from_user.id
    t = time.monotonic()
    fails = [x for x in FAILS.get(uid, []) if t - x < 600]
    if len(fails) >= 5:
        FAILS[uid] = fails
        return await m.answer("⛔ <b>Too many wrong attempts.</b>\nTry again in a few minutes.")

    status, days, exp = await redeem_key(uid, key.strip().upper())
    if status == "ok":
        FAILS.pop(uid, None)
        return await m.answer(
            f"🎉 <b>KEY ACTIVATED!</b>\n{LINE}\n"
            f"🎁 Added  ›  <b>{days} Days</b>\n"
            f"📅 Valid till  ›  <b>{fmt_date(exp)}</b>\n{LINE}\n"
            "🚀 Send a <b>6-character prefix</b> to start!",
            reply_markup=kb_main(uid),
        )
    fails.append(t)
    FAILS[uid] = fails
    if status == "used":
        await m.answer("⚠️ <b>KEY ALREADY USED</b>\nThis key has been redeemed.", reply_markup=kb_back())
    else:
        await m.answer("❌ <b>INVALID KEY</b>\nCheck the key and try again.", reply_markup=kb_back())


@user.message(Command("redeem"))
async def cmd_redeem(m: Message, command: CommandObject):
    if not command.args:
        return await m.answer(REDEEM_PROMPT, reply_markup=kb_back())
    await handle_redeem(m, command.args)


@user.message(F.text.func(lambda t: bool(KEY_RE.match(t.strip().upper()))))
async def msg_key(m: Message):
    await handle_redeem(m, m.text)


async def handle_generate(m: Message, prefix: str):
    uid = m.from_user.id
    row = await get_user(uid)
    if not has_access(uid, row):
        return await m.answer(LOCKED_TEXT, reply_markup=kb_locked())

    t = time.monotonic()
    if t - LAST_GEN.get(uid, 0) < GEN_COOLDOWN:
        return await m.answer("⏳ <b>Easy there!</b> Wait a moment before the next one.")
    LAST_GEN[uid] = t

    prefix = prefix.strip().upper()
    t0 = time.perf_counter()
    data = build_series(prefix)
    ms = (time.perf_counter() - t0) * 1000
    total = SERIES_END - SERIES_START + 1

    await m.bot.send_chat_action(m.chat.id, ChatAction.UPLOAD_DOCUMENT)
    await m.answer_document(
        BufferedInputFile(data, filename=f"{prefix}_{SERIES_START:04d}-{SERIES_END:04d}.txt"),
        caption=(
            f"✅ <b>SERIES READY</b>\n{LINE}\n"
            f"🔖 Prefix  ›  <code>{prefix}</code>\n"
            f"📦 Total  ›  <b>{total:,}</b>\n"
            f"🔢 Range  ›  <code>{prefix}{SERIES_START:04d}</code> ➜ <code>{prefix}{SERIES_END:04d}</code>\n"
            f"⚡ Built in  ›  <b>{ms:.1f} ms</b>"
        ),
    )
    await db.execute("UPDATE users SET gens=gens+1 WHERE user_id=?", (uid,))
    await db.commit()


@user.message(Command("gen"))
async def cmd_gen(m: Message, command: CommandObject):
    arg = (command.args or "").strip()
    if not PREFIX_RE.match(arg):
        return await m.answer(GEN_PROMPT, reply_markup=kb_back())
    await handle_generate(m, arg)


@user.message(F.text.regexp(PREFIX_RE))
async def msg_prefix(m: Message):
    await handle_generate(m, m.text)


@user.message(F.text)
async def msg_fallback(m: Message):
    await m.answer(
        "🤔 <b>Send a 6-character prefix</b> like <code>GJ04AB</code>\n"
        "or activate a key with /redeem",
        reply_markup=kb_back(),
    )


# ───────────────────────── OWNER HANDLERS ─────────────────────────
@owner.message(Command("owner", "panel"))
async def cmd_owner(m: Message):
    await m.answer(await owner_text(), reply_markup=kb_owner())


@owner.callback_query(F.data == "owner")
async def cb_owner(cb: CallbackQuery):
    await show(cb, await owner_text(), kb_owner())


@owner.callback_query(F.data == "own_stats")
async def cb_own_stats(cb: CallbackQuery):
    await show(cb, await stats_text(), kb_owner())


@owner.callback_query(F.data.in_({"own_k7", "own_k30"}))
async def cb_own_key(cb: CallbackQuery):
    days = 7 if cb.data == "own_k7" else 30
    keys = await make_keys(days, 1)
    await cb.message.answer(keys_text(days, keys))
    await cb.answer("Key created ✅")


async def unused_keys_text() -> str:
    cur = await db.execute(
        "SELECT key, days FROM keys WHERE used_by IS NULL ORDER BY created_at DESC LIMIT 40"
    )
    rows = await cur.fetchall()
    if not rows:
        return "📜 <b>No unused keys.</b>\nCreate some with /genkey 7 5"
    body = "\n".join(f"{'🥉' if r['days'] == 7 else '🥇'} <code>{r['key']}</code>" for r in rows)
    return f"📜 <b>UNUSED KEYS</b> (latest {len(rows)})\n{LINE}\n{body}"


@owner.callback_query(F.data == "own_keys")
async def cb_own_keys(cb: CallbackQuery):
    await show(cb, await unused_keys_text(), kb_owner())


@owner.message(Command("stats"))
async def cmd_stats(m: Message):
    await m.answer(await stats_text())


@owner.message(Command("keys"))
async def cmd_keys(m: Message):
    await m.answer(await unused_keys_text())


@owner.message(Command("genkey"))
async def cmd_genkey(m: Message, command: CommandObject):
    args = (command.args or "").split()
    if not args or args[0] not in ("7", "30"):
        return await m.answer("Usage: <code>/genkey 7 5</code> or <code>/genkey 30 10</code>")
    n = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    n = max(1, min(n, 50))
    days = int(args[0])
    await m.answer(keys_text(days, await make_keys(days, n)))


@owner.message(Command("delkey"))
async def cmd_delkey(m: Message, command: CommandObject):
    key = (command.args or "").strip().upper()
    if not key:
        return await m.answer("Usage: <code>/delkey KEY</code>")
    cur = await db.execute("DELETE FROM keys WHERE key=? AND used_by IS NULL", (key,))
    await db.commit()
    await m.answer("🗑 Key deleted." if cur.rowcount else "❌ Not found (or already used).")


@owner.message(Command("grant"))
async def cmd_grant(m: Message, command: CommandObject, bot: Bot):
    args = (command.args or "").split()
    if len(args) != 2 or not all(a.isdigit() for a in args) or not 1 <= int(args[1]) <= 3650:
        return await m.answer("Usage: <code>/grant USER_ID DAYS</code>")
    uid, days = int(args[0]), int(args[1])
    await ensure_user(uid)
    row = await get_user(uid)
    exp = max(now(), row["expires_at"]) + days * 86400
    await db.execute("UPDATE users SET expires_at=? WHERE user_id=?", (exp, uid))
    await db.commit()
    await m.answer(f"🎁 Granted <b>{days}d</b> to <code>{uid}</code>\n📅 Till {fmt_date(exp)}")
    try:
        await bot.send_message(
            uid, f"🎁 <b>PLAN ADDED</b>\n{LINE}\n+{days} days · valid till <b>{fmt_date(exp)}</b>"
        )
    except Exception:
        pass


@owner.message(Command("revoke"))
async def cmd_revoke(m: Message, command: CommandObject):
    a = (command.args or "").strip()
    if not a.isdigit():
        return await m.answer("Usage: <code>/revoke USER_ID</code>")
    await db.execute("UPDATE users SET expires_at=0 WHERE user_id=?", (int(a),))
    await db.commit()
    await m.answer(f"⛔ Plan revoked for <code>{a}</code>")


@owner.message(Command("ban", "unban"))
async def cmd_ban(m: Message, command: CommandObject):
    a = (command.args or "").strip()
    if not a.isdigit():
        return await m.answer("Usage: <code>/ban USER_ID</code> · <code>/unban USER_ID</code>")
    flag = 1 if command.command == "ban" else 0
    await ensure_user(int(a))
    await db.execute("UPDATE users SET banned=? WHERE user_id=?", (flag, int(a)))
    await db.commit()
    await m.answer(("🚫 Banned " if flag else "✅ Unbanned ") + f"<code>{a}</code>")


@owner.message(Command("user"))
async def cmd_user(m: Message, command: CommandObject):
    a = (command.args or "").strip()
    row = await get_user(int(a)) if a.isdigit() else None
    if row is None:
        return await m.answer("❌ User not found.")
    left = row["expires_at"] - now()
    await m.answer(
        f"🔎 <b>USER</b>\n{LINE}\n"
        f"🆔 <code>{row['user_id']}</code>\n"
        f"👤 {escape(row['first_name'] or '—')} · @{escape(row['username'] or '—')}\n"
        f"💎 {'🟢 ' + fmt_left(left) if left > 0 else '🔴 No plan'}\n"
        f"📦 Series made: <b>{row['gens']}</b>\n"
        f"🚫 Banned: <b>{'Yes' if row['banned'] else 'No'}</b>\n"
        f"📅 Joined: {fmt_date(row['joined_at']) if row['joined_at'] else '—'}"
    )


async def _deliver(bot: Bot, uid: int, src_chat, src_msg, text) -> bool:
    for _ in range(2):
        try:
            if src_msg:
                await bot.copy_message(uid, src_chat, src_msg)
            else:
                await bot.send_message(uid, text)
            return True
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)
        except Exception:
            return False
    return False


@owner.message(Command("broadcast"))
async def cmd_broadcast(m: Message, command: CommandObject, bot: Bot):
    reply = m.reply_to_message
    text = command.args
    if not reply and not text:
        return await m.answer(
            "Usage: <code>/broadcast your text</code> (HTML allowed)\n"
            "or reply to any message with /broadcast"
        )
    cur = await db.execute("SELECT user_id FROM users WHERE banned=0")
    ids = [r[0] for r in await cur.fetchall()]
    status = await m.answer(f"📣 Broadcasting to <b>{len(ids)}</b> users…")
    ok = 0
    for uid in ids:
        if await _deliver(bot, uid, m.chat.id, reply.message_id if reply else None, text):
            ok += 1
        await asyncio.sleep(0.04)  # ~25 msg/s, under Telegram limits
    await status.edit_text(
        f"📣 <b>BROADCAST DONE</b>\n{LINE}\n✅ Sent  ›  <b>{ok}</b>\n❌ Failed  ›  <b>{len(ids) - ok}</b>"
    )


# ───────────────────────── STARTUP ─────────────────────────
async def set_commands(bot: Bot):
    base = [
        BotCommand(command="start", description="⚡ Open menu"),
        BotCommand(command="gen", description="📦 Generate series"),
        BotCommand(command="redeem", description="🔑 Redeem key"),
        BotCommand(command="plan", description="💎 My plan"),
        BotCommand(command="help", description="📖 Help"),
    ]
    await bot.set_my_commands(base)
    extra = [
        BotCommand(command="owner", description="👑 Owner panel"),
        BotCommand(command="genkey", description="🔑 Create keys"),
        BotCommand(command="keys", description="📜 Unused keys"),
        BotCommand(command="stats", description="📊 Stats"),
        BotCommand(command="broadcast", description="📣 Broadcast"),
    ]
    for oid in OWNER_IDS:
        try:
            await bot.set_my_commands(base + extra, scope=BotCommandScopeChat(chat_id=oid))
        except Exception:
            pass


async def main():
    if not OWNER_IDS:
        log.warning("OWNER_ID is not set — nobody will be able to create keys!")
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        log.error("BOT_TOKEN is missing or invalid.")
        return
    await init_db()

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.message.filter(F.chat.type == "private")
    dp.message.outer_middleware(Gate())
    dp.callback_query.outer_middleware(Gate())
    dp.include_router(owner)
    dp.include_router(user)

    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    me = await bot.get_me()
    log.info("Started as @%s", me.username)
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    finally:
        await db.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
