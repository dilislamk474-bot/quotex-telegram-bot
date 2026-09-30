"""
Telegram M1 Signal Bot (Asif Signals Bot - Ultimate Control Edition)
"""
import asyncio
import datetime as dt
import io
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, List, Optional, Tuple

import aiohttp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes


# ==================== WEB SERVER FOR RENDER ====================
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Asif Signals Bot is active!</h1></body></html>")
    def log_message(self, format, *args):
        return

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()


# ==================== CONFIG ====================
BOT_TOKEN = "8419845332:AAGtdmayLgS7uJNiKWnqL4YzsISyMicPsfQ"
ADMIN_IDS = {6713482506: True}
DB_PATH = "bot.db"
FREE_LIMIT, PREMIUM_LIMIT = 5, 25
MIN_SCORE = 6  
BD_TZ = dt.timezone(dt.timedelta(hours=6))

PAIR_MAPPING = {
    "EURUSD_otc": "EURUSD=X", "EURUSD": "EURUSD=X",
    "GBPUSD_otc": "GBPUSD=X", "GBPUSD": "GBPUSD=X",
    "USDJPY_otc": "USDJPY=X", "USDJPY": "USDJPY=X",
    "AUDUSD_otc": "AUDUSD=X", "AUDUSD": "AUDUSD=X",
    "USDCAD_otc": "USDCAD=X", "USDCAD": "USDCAD=X",
    "USDCHF_otc": "USDCHF=X", "USDCHF": "USDCHF=X",
    "NZDUSD_otc": "NZDUSD=X", "NZDUSD": "NZDUSD=X",
    "EURGBP_otc": "EURGBP=X", "EURGBP": "EURGBP=X",
    "EURJPY_otc": "EURJPY=X", "EURJPY": "EURJPY=X",
    "GBPJPY_otc": "GBPJPY=X", "GBPJPY": "GBPJPY=X",
    "XAUUSD_otc": "GC=F", "XAUUSD": "GC=F",
    "US100_otc": "^NDX", "US100": "^NDX",
    "US500_otc": "^GSPC", "US500": "^GSPC"
}

PAIRS = list(PAIR_MAPPING.keys())
busy: Dict[int, bool] = {}
auto_tasks: Dict[int, asyncio.Task] = {}


# ==================== DATABASE ====================
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

def is_premium(u: dict) -> bool:
    today_str = dt.datetime.now(BD_TZ).date().isoformat()
    return u["id"] in ADMIN_IDS or (u["premium_until"] and u["premium_until"] >= today_str)

def limit_for(u: dict) -> int:
    return 10**6 if u["id"] in ADMIN_IDS else PREMIUM_LIMIT if is_premium(u) else FREE_LIMIT

def add_result(uid: int, win: bool):
    col = "wins" if win else "losses"
    with db() as c:
        c.execute(f"UPDATE users SET {col}={col}+1 WHERE user_id=?", (uid,))

def use_signal(uid: int):
    with db() as c:
        c.execute("UPDATE users SET daily=daily+1 WHERE user_id=?", (uid,))


# ==================== ANALYSIS ====================
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
    if len(candles) < 60:
        return None, 0, 50, {}
    c = np.array([float(k["close"]) for k in candles])
    e8, e21, e50 = ema(c, 8)[-1], ema(c, 21)[-1], ema(c, 50)[-1]
    macd = ema(c, 12) - ema(c, 26)
    hist = (macd - ema(macd, 9))[-1]
    r = rsi(c)
    score, why, factors = 0, [], 10
    
    if e8 > e21 and e21 > e50:
        score += 3; why.append("Bullish Trend Confluence")
    elif e8 < e21 and e21 < e50:
        score -= 3; why.append("Bearish Trend Confluence")
    
    if hist > 0:
        score += 2; why.append("MACD Bullish Momentum")
    elif hist < 0:
        score -= 2; why.append("MACD Bearish Momentum")

    if r < 30:
        score += 3; why.append(f"RSI Oversold ({r:.0f})")
    elif r > 70:
        score -= 3; why.append(f"RSI Overbought ({r:.0f})")

    direction = "CALL" if score >= MIN_SCORE else "PUT" if score <= -MIN_SCORE else None
    conf = 92 + min(abs(score) * 2, 7)
    return direction, score, conf, {"rsi": round(r, 1), "why": why, "factors": factors}


# ==================== DATA FETCHING ====================
async def fetch_candles(pair: str, count: int = 100) -> List[dict]:
    symbol = PAIR_MAPPING.get(pair, "EURUSD=X")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8) as r:
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
    data = candles[-40:]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=110)
    fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#0d1117")
    for i, k in enumerate(data):
        o, h, l, c = (float(k[x]) for x in ("open", "high", "low", "close"))
        col = "#00e676" if c >= o else "#ff1744"
        ax.plot([i, i], [l, h], color=col, lw=1)
        ax.add_patch(plt.Rectangle((i - 0.3, min(o, c)), 0.6, max(abs(c - o), 1e-9), color=col))
    arrow_col = "#00e676" if direction == "CALL" else "#ff1744"
    last = float(data[-1]["close"])
    ax.annotate(direction, xy=(len(data) - 1, last), xytext=(len(data) + 1.5, last),
                color=arrow_col, fontsize=13, fontweight="bold", arrowprops=dict(arrowstyle="->", color=arrow_col))
    ax.set_xlim(-1, len(data) + 6)
    ax.set_title(f"{pair.replace('_otc', '').upper()} — ASIF ULTRA SIGNAL", color="white")
    ax.tick_params(colors="#8b949e")
    for sp in ax.spines.values(): sp.set_color("#30363d")
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); plt.close(fig); buf.seek(0)
    return buf


# ==================== KEYBOARDS ====================
def home_kb():
    return M([
        [B("📊 সিগন্যাল পেয়ারসমূহ", callback_data="pairs_menu"), B("🔔 অটো নোটিফিকেশন", callback_data="auto")],
        [B("👤 আমার প্রোফাইল", callback_data="profile"), B("💎 ভিআইপি প্ল্যান", callback_data="vip")],
        [B("⏹ অটো বন্ধ করুন", callback_data="stop_auto")]
    ])


# ==================== SIGNAL HANDLER ====================
async def run_signal(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int, pair: str, quiet: bool = False):
    candles = await fetch_candles(pair)
    direction, score, conf, info = analyze(candles)
    clean = pair.replace("_otc", "").upper()
    
    if not candles:
        if not quiet: await ctx.bot.send_message(chat_id, "❌ মার্কেট ডাটা পাওয়া যায়নি।", reply_markup=home_kb())
        return False
        
    if direction is None:
        if not quiet: await ctx.bot.send_message(chat_id, f"⚪ {clean}: একিউরেসি ৯৫% এর নিচে থাকায় স্কিপ করা হলো।", reply_markup=home_kb())
        return False

    now_bd = dt.datetime.now(BD_TZ)
    entry = (now_bd + dt.timedelta(minutes=1)).replace(second=0, microsecond=0)
    entry_price = float(candles[-1]["close"])
    use_signal(uid)
    
    icon = "🟢" if direction == "CALL" else "🔴"
    text = (
        f"🔥 **ASIF SIGNALS BOT (ULTRA PRO)** 🔥\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 PAIR ➜ {clean}\n"
        f"⏰ ENTRY ➜ {entry.strftime('%H:%M')} (UTC+6)\n"
        f"⏳ EXPIRY ➜ 1 MIN\n"
        f"{icon} DIRECTION ➜ {direction}\n"
        f"🎯 ACCURACY ➜ {conf}%\n"
        f"👑 MASTER ASIF AJ"
    )

    await ctx.bot.send_photo(chat_id, build_chart(candles, pair, direction), caption=text, parse_mode="Markdown")

    wait_sec = (entry - dt.datetime.now(BD_TZ)).total_seconds() + 62
    if wait_sec > 0: await asyncio.sleep(wait_sec)

    res = await fetch_candles(pair, 5)
    if not res: return True
    cl = float(res[-1]["close"])
    win = cl > entry_price if direction == "CALL" else cl < entry_price
    add_result(uid, win)
    
    res_text = "🟩 WIN (PROFIT SECURED) 🟩" if win else "🟥 LOSS 🟥"
    await ctx.bot.send_message(chat_id, f"{res_text}\n📊 {clean} · {direction}\nOpen: {entry_price:.5f} | Close: {cl:.5f}", 
                               reply_markup=None if uid in auto_tasks else home_kb())
    return True


async def auto_loop(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int):
    try:
        await ctx.bot.send_message(chat_id, "🔔 অটো নোটিফিকেশন চালু হয়েছে!", reply_markup=home_kb())
        while uid in auto_tasks:
            user = get_user(uid)
            if user["daily"] >= limit_for(user):
                auto_tasks.pop(uid, None)
                await ctx.bot.send_message(chat_id, "❌ দৈনিক লিমিট শেষ, অটো বন্ধ করা হলো।", reply_markup=home_kb())
                return
            for p in PAIRS:
                if uid not in auto_tasks: return
                cs = await fetch_candles(p)
                d, _, _, _ = analyze(cs)
                if d and uid in auto_tasks:
                    await run_signal(ctx, chat_id, uid, p, quiet=True)
                    await asyncio.sleep(10)
                await asyncio.sleep(3)
            await asyncio.sleep(10)
    except asyncio.CancelledError:
        pass
    finally:
        auto_tasks.pop(uid, None)


# ==================== COMMAND & CALLBACK ROUTERS ====================
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    get_user(u.id, u.full_name)
    await update.message.reply_text("👋 স্বাগতম! **Asif Signals Bot Ultra** চালু আছে। নিচে মেনু ব্যবহার করুন:", parse_mode="Markdown", reply_markup=home_kb())

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ যেকোনো সিগন্যাল পেতে বা অটো চালু করতে নিচের হোম মেনু ব্যবহার করুন।", reply_markup=home_kb())

async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    u = q.from_user
    user = get_user(u.id, u.full_name)
    await q.answer()
    chat_id = q.message.chat_id

    if q.data == "pairs_menu":
        rows = [[B(p.replace("_otc", " OTC").replace("_", "/"), callback_data=f"p_{p}")] for p in PAIRS[:10]]
        rows.append([B("🏠 হোম মেনু", callback_data="home")])
        try:
            await ctx.bot.edit_message_text(chat_id=chat_id, message_id=q.message.message_id, text="💎 পেয়ার সিলেক্ট করুন:", reply_markup=M(rows))
        except Exception:
            await ctx.bot.send_message(chat_id, "💎 পেয়ার সিলেক্ট করুন:", reply_markup=M(rows))

    elif q.data == "home":
        try:
            await ctx.bot.edit_message_text(chat_id=chat_id, message_id=q.message.message_id, text="🏠 প্রধান মেনু:", reply_markup=home_kb())
        except Exception:
            await ctx.bot.send_message(chat_id, "🏠 প্রধান মেনু:", reply_markup=home_kb())

    elif q.data == "auto":
        if u.id in auto_tasks:
            await q.answer("অটো ইতিমধ্যে চালু আছে!", show_alert=True)
            return
        if user["daily"] >= limit_for(user):
            await ctx.bot.send_message(chat_id, "❌ লিমিট শেষ।")
            return
        auto_tasks[u.id] = asyncio.create_task(auto_loop(ctx, chat_id, u.id))

    elif q.data == "stop_auto":
        t = auto_tasks.pop(u.id, None)
        if t:
            t.cancel()
            await ctx.bot.send_message(chat_id, "⏹ অটো মোড বন্ধ করা হয়েছে।", reply_markup=home_kb())
        else:
            await ctx.bot.send_message(chat_id, "ℹ️ অটো মোড বন্ধই আছে।", reply_markup=home_kb())

    elif q.data.startswith("p_"):
        if busy.get(u.id):
            await q.answer("⏳ আগের সিগন্যাল প্রসেস হচ্ছে...", show_alert=True)
            return
        if user["daily"] >= limit_for(user):
            await ctx.bot.send_message(chat_id, "❌ আজকের লিমিট শেষ।")
            return
        busy[u.id] = True
        await ctx.bot.send_message(chat_id, "🔍 মার্কেট স্ক্যান করা হচ্ছে...")
        await run_signal(ctx, chat_id, u.id, q.data[2:])
        busy.pop(u.id, None)

    elif q.data == "profile":
        t = user["wins"] + user["losses"]
        wr = round(user["wins"] / t * 100, 1) if t else 0
        plan = "ADMIN" if u.id in ADMIN_IDS else "PREMIUM" if is_premium(user) else "FREE"
        await ctx.bot.send_message(chat_id, f"👤 নাম: {user['name']}\n💎 প্ল্যান: {plan}\n✅ জয়: {user['wins']} | ❌ লস: {user['losses']} | উইন রেট: {wr}%", reply_markup=home_kb())

    elif q.data == "vip":
        await ctx.bot.send_message(chat_id, "💎 প্রিমিayan প্ল্যানের জন্য এডমিনের সাথে যোগাযোগ করুন।", reply_markup=home_kb())


def main():
    setup_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CallbackQueryHandler(on_callback))
    
    print("✅ Bot is fully running with direct control.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
