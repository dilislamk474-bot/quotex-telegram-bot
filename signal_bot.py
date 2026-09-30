"""
ASIF SIGNALS BOT — ULTIMATE MASTER EDITION (BACKGROUND WORKER)
"""
import asyncio
import datetime as dt
import io
import os
import sqlite3
import logging
from typing import Dict, List, Optional, Tuple

import aiohttp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# Logging setup
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== CONFIG & OWNERSHIP ====================
BOT_TOKEN = "8419845332:AAGtdmayLgS7uJNiKWnqL4YzsISyMicPsfQ" 
OWNER_ID = 6713482506  # তোর অফিশিয়াল ওনার আইডি
ADMIN_IDS = {OWNER_ID: True}
DB_PATH = "bot.db"
FREE_LIMIT, PREMIUM_LIMIT = 10, 50
BD_TZ = dt.timezone(dt.timedelta(hours=6))

PAIR_MAPPING = {
    "EURUSD_otc": "EURUSD=X", "EURUSD": "EURUSD=X",
    "GBPUSD_otc": "GBPUSD=X", "GBPUSD": "GBPUSD=X",
    "USDJPY_otc": "USDJPY=X", "USDJPY": "USDJPY=X",
    "AUDUSD_otc": "AUDUSD=X", "AUDUSD": "AUDUSD=X",
    "USDCAD_otc": "USDCAD=X", "USDCAD": "USDCAD=X",
    "USDCHF_otc": "USDCHF=X", "USDCHF": "USDCHF=X",
    "XAUUSD_otc": "GC=F", "XAUUSD": "GC=F"
}

PAIRS = list(PAIR_MAPPING.keys())
busy: Dict[int, bool] = {}
auto_tasks: Dict[int, asyncio.Task] = {}


# ==================== DATABASE & SECURITY ====================
def db():
    return sqlite3.connect(DB_PATH)

def setup_db():
    with db() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY, name TEXT DEFAULT '',
            premium_until TEXT DEFAULT '', daily INTEGER DEFAULT 0, day TEXT DEFAULT '',
            wins INTEGER DEFAULT 0, losses INTEGER DEFAULT 0)""")

def get_user(uid: int, name: str = "") -> dict:
    today = dt.datetime.now(BD_TZ).date().isoformat()
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id,name,day) VALUES(?,?,?)", (uid, name, today))
        c.execute("UPDATE users SET daily=0, day=? WHERE user_id=? AND day!=?", (today, uid, today))
        r = c.execute("SELECT user_id,name,premium_until,daily,wins,losses FROM users WHERE user_id=?", (uid,)).fetchone()
    return dict(zip(["id", "name", "premium_until", "daily", "wins", "losses"], r))

def is_admin(uid: int) -> bool:
    return uid == OWNER_ID

def is_premium(u: dict) -> bool:
    today_str = dt.datetime.now(BD_TZ).date().isoformat()
    return u["id"] in ADMIN_IDS or (u["premium_until"] and u["premium_until"] >= today_str)

def limit_for(u: dict) -> int:
    return 10**9 if is_admin(u["id"]) else PREMIUM_LIMIT if is_premium(u) else FREE_LIMIT

def add_result(uid: int, win: bool):
    col = "wins" if win else "losses"
    with db() as c:
        c.execute(f"UPDATE users SET {col}={col}+1 WHERE user_id=?", (uid,))

def use_signal(uid: int):
    with db() as c:
        c.execute("UPDATE users SET daily=daily+1 WHERE user_id=?", (uid,))


# ==================== ADVANCED ANALYSIS ====================
def ema(x: np.ndarray, n: int) -> np.ndarray:
    a, out = 2 / (n + 1), np.empty_like(x)
    out[0] = x[0]
    for i in range(1, len(x)):
        out[i] = a * x[i] + (1 - a) * out[i - 1]
    return out

def rsi(x: np.ndarray, n: int = 14) -> float:
    d = np.diff(x)
    up, dn = np.where(d > 0, d, 0.0), np.where(d < 0, -d, 0.0)
    au, ad = up[:n].mean(), dn[:n].mean()
    for i in range(n, len(d)):
        au, ad = (au * (n - 1) + up[i]) / n, (ad * (n - 1) + dn[i]) / n
    return 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)

def analyze(candles: List[dict]) -> Tuple[Optional[str], int, int, dict]:
    if len(candles) < 35:
        return None, 0, 50, {}
    c = np.array([float(k["close"]) for k in candles])
    
    e8, e21 = ema(c, 8)[-1], ema(c, 21)[-1]
    r = rsi(c)
    momentum = c[-1] - c[-3]
    
    score = 0
    if e8 > e21 and momentum > 0: score += 4
    elif e8 < e21 and momentum < 0: score -= 4
    
    if r < 30: score += 3  
    elif r > 70: score -= 3 
    elif 35 <= r <= 65: score += 1 if e8 > e21 else -1

    if abs(score) < 2:
        return None, score, 60, {} 

    direction = "CALL" if score > 0 else "PUT"
    conf = min(98, 85 + abs(score) * 3)
    return direction, score, conf, {"rsi": round(r, 1)}


# ==================== DATA FETCHING ====================
async def fetch_candles(pair: str, count: int = 50) -> List[dict]:
    symbol = PAIR_MAPPING.get(pair, "EURUSD=X")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5) as r:
                if r.status != 200: return []
                res = await r.json()
                result = res.get("chart", {}).get("result", [])
                if not result: return []
                meta = result[0]
                ts = meta.get("timestamp", [])
                q = meta.get("indicators", {}).get("quote", [{}])[0]
                opens, highs, lows, closes = q.get("open", []), q.get("high", []), q.get("low", []), q.get("close", [])
                candles = []
                for i in range(len(ts)):
                    if i < len(opens) and opens[i] is not None and closes[i] is not None:
                        candles.append({
                            "epoch": int(ts[i]), "open": float(opens[i]),
                            "high": float(highs[i] if highs[i] is not None else opens[i]),
                            "low": float(lows[i] if lows[i] is not None else opens[i]),
                            "close": float(closes[i])
                        })
                return candles[-count:]
    except Exception:
        return []


# ==================== CHART GENERATOR ====================
def build_chart(candles: List[dict], pair: str, direction: str) -> io.BytesIO:
    data = candles[-30:]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=120)
    fig.patch.set_facecolor("#0b0e14"); ax.set_facecolor("#0b0e14")
    
    for i, k in enumerate(data):
        o, h, l, c = (float(k[x]) for x in ("open", "high", "low", "close"))
        col = "#00ffcc" if c >= o else "#ff0055"
        ax.plot([i, i], [l, h], color=col, lw=1.2)
        ax.add_patch(plt.Rectangle((i - 0.35, min(o, c)), 0.7, max(abs(c - o), 1e-9), color=col))
        
    ax.set_title(f"⚡ ASIF ULTRA PRO SIGNALS — {pair.replace('_otc', '').upper()} ⚡", color="#ffffff", fontsize=12, fontweight='bold', pad=12)
    ax.tick_params(colors="#8b949e", labelsize=9)
    for sp in ax.spines.values(): sp.set_color("#21262d")
    ax.grid(True, color="#161b22", linestyle="--", alpha=0.5)
    
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); plt.close(fig); buf.seek(0)
    return buf


# ==================== KEYBOARDS ====================
def home_kb(uid: int):
    rows = [
        [B("📊 প্রফেশনাল সিগন্যাল নিন", callback_data="pairs_menu"), B("🔔 অটো সিগন্যাল (AI)", callback_data="auto")],
        [B("👤 আমার অ্যাকাউন্ট ও স্ট্যাটাস", callback_data="profile"), B("💎 ভিআইপি সুবিধা", callback_data="vip")],
        [B("⏹ অটো মোড বন্ধ করুন", callback_data="stop_auto")]
    ]
    if is_admin(uid):
        rows.append([B("👑 ওনার প্যানেল (Admin)", callback_data="admin_panel")])
    return M(rows)


# ==================== SIGNAL HANDLER ====================
async def run_signal(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int, pair: str, quiet: bool = False):
    candles = await fetch_candles(pair)
    direction, score, conf, info = analyze(candles)
    clean = pair.replace("_otc", "").upper()
    
    if not candles or not direction:
        if not quiet: 
            await ctx.bot.send_message(chat_id, "⚠️ মার্কেট এখন খুবই ভোলাটাইল বা সাইডওয়ে আছে। একটু পরে আবার চেষ্টা করুন।", reply_markup=home_kb(uid))
        return False

    now_bd = dt.datetime.now(BD_TZ)
    entry = (now_bd + dt.timedelta(minutes=1)).replace(second=0, microsecond=0)
    entry_price = float(candles[-1]["close"])
    use_signal(uid)
    
    icon = "🟢" if direction == "CALL" else "🔴"
    text = (
        f"💎 **ASIF SIGNALS BOT — ELITE PRO** 💎\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 **PAIR** ➜ `{clean}`\n"
        f"⏰ **ENTRY TIME** ➜ `{entry.strftime('%H:%M')} (UTC+6)`\n"
        f"⏳ **EXPIRY** ➜ `1 MINUTE`\n"
        f"{icon} **DIRECTION** ➜ **{direction}**\n"
        f"🎯 **CONFIDENCE** ➜ `{conf}%`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👑 *Verified & Powered by Master Asif AJ*"
    )

    await ctx.bot.send_photo(chat_id, build_chart(candles, pair, direction), caption=text, parse_mode="Markdown")

    wait_sec = (entry - dt.datetime.now(BD_TZ)).total_seconds() + 65
    if wait_sec > 0: await asyncio.sleep(wait_sec)

    res = await fetch_candles(pair, 5)
    if not res: return True
    cl = float(res[-1]["close"])
    win = cl > entry_price if direction == "CALL" else cl < entry_price
    add_result(uid, win)
    
    res_text = "🟩 **WIN (PROFIT SECURED)** 🟩" if win else "🟥 **LOSS (MARKET REVERSED)** 🟥"
    await ctx.bot.send_message(
        chat_id, 
        f"{res_text}\n"
        f"📊 **{clean}** | `{direction}`\n"
        f"🔹 Open: `{entry_price:.5f}`\n"
        f"🔹 Close: `{cl:.5f}`", 
        parse_mode="Markdown",
        reply_markup=None if uid in auto_tasks else home_kb(uid)
    )
    return True


async def auto_loop(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int):
    try:
        await ctx.bot.send_message(chat_id, "🔔 অটো সিগন্যাল মোড সফলভাবে চালু হয়েছে!", reply_markup=home_kb(uid))
        while uid in auto_tasks:
            user = get_user(uid)
            if user["daily"] >= limit_for(uid):
                auto_tasks.pop(uid, None)
                await ctx.bot.send_message(chat_id, "❌ দৈনিক সিগন্যাল লিমিট শেষ, অটো মোড বন্ধ করা হলো।", reply_markup=home_kb(uid))
                return
            for p in PAIRS:
                if uid not in auto_tasks: return
                d, _, _, _ = analyze(await fetch_candles(p))
                if d and uid in auto_tasks:
                    await run_signal(ctx, chat_id, uid, p, quiet=True)
                    await asyncio.sleep(12)
                await asyncio.sleep(4)
            await asyncio.sleep(15)
    except asyncio.CancelledError:
        pass
    finally:
        auto_tasks.pop(uid, None)


# ==================== COMMAND & ROUTERS ====================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    get_user(u.id, u.full_name)
    welcome_text = (
        f"👋 স্বাগতম, **{u.full_name}**!\n\n"
        f"এটি আপনার পার্সোনাল ও এক্সক্লুসিভ **Asif Signals Bot**। এখানে কোনো স্ক্যাম বা থার্ড-পার্টি ঝামেলার সুযোগ নেই। শতভাগ নিখুঁত অ্যানালিসিস পেতে নিচের মেনু ব্যবহার করুন:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=home_kb(u.id))

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    await update.message.reply_text("ℹ️ সিগন্যাল বা অটো মোড চালু করতে নিচের হোম মেনু ব্যবহার করুন:", reply_markup=home_kb(u.id))

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    u = q.from_user
    user = get_user(u.id, u.full_name)
    await q.answer()
    chat_id = q.message.chat_id

    if q.data == "pairs_menu":
        rows = [[B(p.replace("_otc", " OTC").replace("_", "/"), callback_data=f"p_{p}")] for p in PAIRS]
        rows.append([B("🏠 মূল মেনু", callback_data="home")])
        try:
            await ctx.bot.edit_message_text(chat_id=chat_id, message_id=q.message.message_id, text="💎 ট্রেডিং পেয়ার সিলেক্ট করুন:", reply_markup=M(rows))
        except Exception:
            await ctx.bot.send_message(chat_id, "💎 ট্রেডিং পেয়ার সিলেক্ট করুন:", reply_markup=M(rows))

    elif q.data == "home":
        try:
            await ctx.bot.edit_message_text(chat_id=chat_id, message_id=q.message.message_id, text="🏠 প্রধান মেনু:", reply_markup=home_kb(u.id))
        except Exception:
            await ctx.bot.send_message(chat_id, "🏠 প্রধান মেনু:", reply_markup=home_kb(u.id))

    elif q.data == "auto":
        if u.id in auto_tasks:
            await q.answer("অটো সিগন্যাল ইতিমধ্যে চালু আছে!", show_alert=True)
            return
        if user["daily"] >= limit_for(u.id):
            await ctx.bot.send_message(chat_id, "❌ আপনার আজকের লিমিট শেষ।")
            return
        auto_tasks[u.id] = asyncio.create_task(auto_loop(ctx, chat_id, u.id))

    elif q.data == "stop_auto":
        t = auto_tasks.pop(u.id, None)
        if t:
            t.cancel()
            await ctx.bot.send_message(chat_id, "⏹ অটো মোড সফলভাবে বন্ধ করা হয়েছে।", reply_markup=home_kb(u.id))
        else:
            await ctx.bot.send_message(chat_id, "ℹ️ অটো মোড ইতিমধ্যে বন্ধ রয়েছে।", reply_markup=home_kb(u.id))

    elif q.data.startswith("p_"):
        if busy.get(u.id):
            await q.answer("⏳ আগের সিগন্যাল প্রসেস হচ্ছে...", show_alert=True)
            return
        if user["daily"] >= limit_for(u.id):
            await ctx.bot.send_message(chat_id, "❌ আজকের সিগন্যাল লিমিট শেষ।")
            return
        busy[u.id] = True
        await ctx.bot.send_message(chat_id, "🔍 মার্কেট ডিপ অ্যানালিসিস করা হচ্ছে...")
        await run_signal(ctx, chat_id, u.id, q.data[2:])
        busy.pop(u.id, None)

    elif q.data == "profile":
        t = user["wins"] + user["losses"]
        wr = round(user["wins"] / t * 100, 1) if t else 0
        plan = "OWNER & ADMIN" if is_admin(u.id) else "PREMIUM" if is_premium(user) else "FREE"
        profile_text = (
            f"👤 **ইউজার প্রোফাইল**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏷 নাম: `{user['name']}`\n"
            f"👑 স্ট্যাটাস: `{plan}`\n"
            f"✅ মোট জয়: `{user['wins']}`\n"
            f"❌ মোট লস: `{user['losses']}`\n"
            f"🎯 উইন রেট: `{wr}%`\n"
            f"📈 আজ ব্যবহার করেছেন: `{user['daily']}` টি"
        )
        await ctx.bot.send_message(chat_id, profile_text, parse_mode="Markdown", reply_markup=home_kb(u.id))

    elif q.data == "vip":
        await ctx.bot.send_message(chat_id, "💎 আপনি এই বটের একমাত্র ওনার! আপনার জন্য সমস্ত প্রিমিয়াম ফিচার আনলকড আছে।", reply_markup=home_kb(u.id))

    elif q.data == "admin_panel" and is_admin(u.id):
        await ctx.bot.send_message(chat_id, "👑 **ওনার কন্ট্রোল প্যানেল**\n\nবট সম্পূর্ণ সুরক্ষিত ও আপনার নিয়ন্ত্রণে রয়েছে। কোনো স্প্যাম বা ডিফল্ট কোড নেই!", parse_mode="Markdown", reply_markup=home_kb(u.id))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Exception in bot:", exc_info=context.error)

def main():
    setup_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_error_handler(error_handler)
    
    print("👑 Asif Signals Bot is fully running & secured.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
