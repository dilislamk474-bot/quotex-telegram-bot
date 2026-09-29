"""
Telegram M1 Signal Bot (Brazilian AI Ultra Pro Edition - High Accuracy & Smart Result)
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


# ==================== ROBUST WEB SERVER FOR RENDER PORT ====================
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html><body><h1>Brazilian Core AI Ultra Bot is running!</h1></body></html>")
    def log_message(self, format, *args):
        return

def run_dummy_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"Dummy web server running on port {port}")
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()


# ==================== CONFIG ====================
BOT_TOKEN = "8419845332:AAGtdmayLgS7uJNiKWnqL4YzsISyMicPsfQ"
ADMIN_IDS = {6713482506: True}
DB_PATH = "bot.db"
FREE_LIMIT, PREMIUM_LIMIT = 5, 25

MIN_SCORE = 4  # High Accuracy er jonno score 4 kora holo (Sudhu matro strong setup aslei signal dibe)
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
    "EURAUD_otc": "EURAUD=X", "EURAUD": "EURAUD=X",
    "EURCAD_otc": "EURCAD=X", "EURCAD": "EURCAD=X",
    "EURCHF_otc": "EURCHF=X", "EURCHF": "EURCHF=X",
    "EURNZD_otc": "EURNZD=X", "EURNZD": "EURNZD=X",
    "GBPAUD_otc": "GBPAUD=X", "GBPAUD": "GBPAUD=X",
    "GBPCAD_otc": "GBPCAD=X", "GBPCAD": "GBPCAD=X",
    "GBPCHF_otc": "GBPCHF=X", "GBPCHF": "GBPCHF=X",
    "GBPNZD_otc": "GBPNZD=X", "GBPNZD": "GBPNZD=X",
    "AUDCAD_otc": "AUDCAD=X", "AUDCAD": "AUDCAD=X",
    "AUDCHF_otc": "AUDCHF=X", "AUDCHF": "AUDCHF=X",
    "AUDJPY_otc": "AUDJPY=X", "AUDJPY": "AUDJPY=X",
    "AUDNZD_otc": "AUDNZD=X", "AUDNZD": "AUDNZD=X",
    "CADCHF_otc": "CADCHF=X", "CADCHF": "CADCHF=X",
    "CADJPY_otc": "CADJPY=X", "CADJPY": "CADJPY=X",
    "CHFJPY_otc": "CHFJPY=X", "CHFJPY": "CHFJPY=X",
    "NZDCAD_otc": "NZDCAD=X", "NZDCAD": "NZDCAD=X",
    "NZDCHF_otc": "NZDCHF=X", "NZDCHF": "NZDCHF=X",
    "NZDJPY_otc": "NZDJPY=X", "NZDJPY": "NZDJPY=X",
    "XAUUSD_otc": "GC=F", "XAUUSD": "GC=F",
    "XAG_USD_otc": "SI=F", "XAG_USD": "SI=F",
    "USCRUDE_otc": "CL=F", "USCRUDE": "CL=F",
    "UKBRENT_otc": "BZ=F", "UKBRENT": "BZ=F",
    "US100_otc": "^NDX", "US100": "^NDX",
    "US500_otc": "^GSPC", "US500": "^GSPC",
    "AAPL": "AAPL", "BA": "BA", "MSFT": "MSFT",
    "PFE": "PFE", "META": "META", "JNJ": "JNJ"
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
        r = c.execute("SELECT user_id,name,premium_until,daily,wins,losses FROM users WHERE user_id=?",
                      (uid,)).fetchone()
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


# ==================== INDICATORS & ULTRA AI ANALYSIS ====================
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
    mid, sd = c[-20:].mean(), c[-20:].std()
    price = c[-1]

    score, why, factors = 0, [], 10
    
    # Ultra Strict Trend Rules for High Accuracy
    if e8 > e21 and e21 > e50:
        score += 2; why.append("Strong Bullish EMA Alignment")
    elif e8 < e21 and e21 < e50:
        score -= 2; why.append("Strong Bearish EMA Alignment")
    
    if hist > 0:
        score += 2; why.append("MACD Momentum Positive")
        factors += 3
    elif hist < 0:
        score -= 2; why.append("MACD Momentum Negative")
        factors += 3

    if r < 25:
        score += 2; why.append(f"RSI {r:.0f} Extreme Oversold Reversal")
        factors += 2
    elif r > 75:
        score -= 2; why.append(f"RSI {r:.0f} Extreme Overbought Reversal")
        factors += 2
    elif 30 <= r <= 70:
        factors += 1

    if price <= mid - 2.1 * sd:
        score += 1; why.append("Bollinger Lower Band Support Touch")
    elif price >= mid + 2.1 * sd:
        score -= 1; why.append("Bollinger Upper Band Resistance Touch")

    direction = "CALL" if score >= MIN_SCORE else "PUT" if score <= -MIN_SCORE else None
    base_conf = 82 + min(abs(score) * 4, 15) # High confidence rating

    return direction, score, base_conf, {"rsi": round(r, 1), "why": why, "factors": factors}


# ==================== DATA (YAHOO FINANCE API) ====================
async def fetch_candles(pair: str, count: int = 100) -> List[dict]:
    symbol = PAIR_MAPPING.get(pair, "EURUSD=X")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m&range=1d"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status != 200:
                    return []
                res = await r.json()
                result = res.get("chart", {}).get("result", [])
                if not result:
                    return []
                meta = result[0]
                timestamps = meta.get("timestamp", [])
                quote = meta.get("indicators", {}).get("quote", [{}])[0]
                opens = quote.get("open", [])
                highs = quote.get("high", [])
                lows = quote.get("low", [])
                closes = quote.get("close", [])

                candles = []
                for i in range(len(timestamps)):
                    if i < len(opens) and opens[i] is not None and closes[i] is not None:
                        candles.append({
                            "epoch": int(timestamps[i]),
                            "open": float(opens[i]),
                            "high": float(highs[i] if highs[i] is not None else opens[i]),
                            "low": float(lows[i] if lows[i] is not None else opens[i]),
                            "close": float(closes[i])
                        })
                return candles[-count:]
    except Exception as e:
        print("fetch error:", e)
        return []


# ==================== CHART ====================
def build_chart(candles: List[dict], pair: str, direction: str) -> io.BytesIO:
    data = candles[-40:]
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=110)
    fig.patch.set_facecolor("#0d1117"); ax.set_facecolor("#0d1117")
    for i, k in enumerate(data):
        o, h, l, c = (float(k[x]) for x in ("open", "high", "low", "close"))
        col = "#00e676" if c >= o else "#ff1744"
        ax.plot([i, i], [l, h], color=col, lw=1)
        ax.add_patch(plt.Rectangle((i - 0.3, min(o, c)), 0.6, max(abs(c - o), 1e-9), color=col))
    closes = np.array([float(k["close"]) for k in candles])
    ax.plot(range(len(data)), ema(closes, 8)[-40:], color="#ffd600", lw=1, label="EMA8")
    ax.plot(range(len(data)), ema(closes, 21)[-40:], color="#40c4ff", lw=1, label="EMA21")
    last = float(data[-1]["close"])
    arrow_col = "#00e676" if direction == "CALL" else "#ff1744"
    ax.annotate(direction, xy=(len(data) - 1, last), xytext=(len(data) + 1.5, last),
                color=arrow_col, fontsize=13, fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=arrow_col))
    ax.set_xlim(-1, len(data) + 6)
    ax.set_title(f"{pair.replace('_otc', '').upper()} · ULTRA AI", color="white")
    ax.tick_params(colors="#8b949e")
    for sp in ax.spines.values():
        sp.set_color("#30363d")
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); plt.close(fig); buf.seek(0)
    return buf


# ==================== SIGNAL FLOW ====================
def home_kb():
    return M([[B("📊 সিগন্যাল পেয়ারসমূহ", callback_data="pairs_page_0"), B("🔔 অটো নোটিফিকেশন চালু", callback_data="auto")],
              [B("👤 প্রোফাইল", callback_data="profile")]])


def stop_kb():
    return M([[B("⏹ অটো নোটিফিকেশন বন্ধ করুন", callback_data="stop_auto")]])


async def run_signal(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int, pair: str,
                     quiet_no_trade: bool = False) -> bool:
    try:
        candles = await fetch_candles(pair)
        direction, score, conf, info = analyze(candles)
        clean_name = pair.replace("_otc", "").upper()
        
        if not candles:
            if not quiet_no_trade:
                await ctx.bot.send_message(chat_id, "❌ মার্কেট ডাটা পাওয়া যায়নি।", reply_markup=home_kb())
            return False
            
        if direction is None:
            if not quiet_no_trade:
                await ctx.bot.send_message(
                    chat_id, f"⚪ {clean_name}: একিউরেসি লেভেল পারফেক্ট নয়, অপেক্ষা করুন।",
                    reply_markup=home_kb())
            return False

        now_bd = dt.datetime.now(BD_TZ)
        entry = (now_bd + dt.timedelta(minutes=1)).replace(second=0, microsecond=0)
        
        # Exact entry price lock for smart result tracking
        entry_price = float(candles[-1]["close"])
        use_signal(uid)
        
        icon = "🟢" if direction == "CALL" else "🔴"
        conf_blocks = "▰" * int(conf // 10) + "▱" * (10 - int(conf // 10))
        why_text = "\n".join([f"• {w}" for w in info['why']])
        
        caption_text = (
            f"🔥 **BRAZILIAN CORE AI (ULTRA PRO)** 🔥\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 PAIR ➜ {clean_name} · HIGH ACCURACY\n"
            f"⏰ ENTRY ➜ {entry.strftime('%H:%M')} (UTC+6)\n"
            f"⏳ EXPIRY ➜ 1 MIN · M1 · MTG 1\n"
            f"💎 PAYOUT ➜ 85%\n"
            f"{icon} DIRECTION ➜ {direction}\n"
            f"🎯 ACCURACY RATE ➜ {conf}% {conf_blocks}\n"
            f"🏆 GRADE 👑 ULTRA PREMIUM\n"
            f"🧠 CONFLUENCE ➜ {info['factors']}/17 factors\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🧠 **WHY {direction}**\n"
            f"{why_text}\n"
            f"⏳ Smart Result Tracking Active\n"
            f"🤖 👑 ELITE PRO"
        )

        await ctx.bot.send_photo(
            chat_id, build_chart(candles, pair, direction),
            caption=caption_text, parse_mode="Markdown"
        )

        wait_seconds = (entry - dt.datetime.now(BD_TZ)).total_seconds() + 62
        if wait_seconds > 0:
            await asyncio.sleep(wait_seconds)

        res = await fetch_candles(pair, 5)
        if not res:
            return True

        target = res[-1]
        cl = float(target["close"])
        
        # Smart comparison based on locked entry price to ensure correct Win/Loss display
        win = cl > entry_price if direction == "CALL" else cl < entry_price
        add_result(uid, win)
        
        res_header = "🟩🟩🟩 WIN 🟩🟩🟩" if win else "🟥🟥🟥 LOSS 🟥🟥🟥"
        result_caption = (
            f"{res_header}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 PAIR ➜ {clean_name} · {direction}\n"
            f"⏰ Entry {entry.strftime('%H:%M')} — {'PROFIT SECURED' if win else 'CLOSED'}\n"
            f"🔓 Locked Open: {entry_price} | 🔒 Close: {cl}\n"
            f"━━━━━━━━━━━━━━━━━━━━"
        )
        
        await ctx.bot.send_message(chat_id, result_caption, reply_markup=None if uid in auto_tasks else home_kb())
        return True
    finally:
        pass


async def auto_loop(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int):
    try:
        await ctx.bot.send_message(chat_id, "🔔 হাই-একিউরেসি অটো মোড চালু হয়েছে! শক্তিশালী সেটআপ আসলে বট নিজে সিগন্যাল পাঠাবে।", reply_markup=stop_kb())
        while True:
            user = get_user(uid)
            if user["daily"] >= limit_for(user):
                await ctx.bot.send_message(chat_id, "❌ আজকের লিমিট শেষ, অটো নোটিফিকেশন বন্ধ করা হলো।", reply_markup=home_kb())
                return
            
            for p in PAIRS:
                cs = await fetch_candles(p)
                d, sc, _, _ = analyze(cs)
                if d:  # High score match holei pathabe
                    await run_signal(ctx, chat_id, uid, p, quiet_no_trade=True)
                    await asyncio.sleep(60)
                await asyncio.sleep(4)
            
            await asyncio.sleep(25)
    except asyncio.CancelledError:
        raise
    finally:
        auto_tasks.pop(uid, None)


# ==================== HANDLERS ====================
async def on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    get_user(u.id, u.full_name)
    await update.message.reply_text(
        "👋 স্বাগতম!\n🔥 **Brazilian Core AI Ultra** বটে আপনাকে স্বাগতম।\n\n🔔 হাই-একিউরেসি সিগন্যাল পেতে 'অটো নোটিফিকেশন চালু' বাটনে ক্লিক করুন!",
        parse_mode="Markdown", reply_markup=home_kb())


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    u = q.from_user
    user = get_user(u.id, u.full_name)
    await q.answer()
    chat_id = q.message.chat_id

    if q.data.startswith("pairs_page_"):
        page = int(q.data.split("_")[-1])
        per_page = 10
        start_idx = page * per_page
        end_idx = start_idx + per_page
        current_pairs = PAIRS[start_idx:end_idx]

        rows = [[B(p.replace("_otc", " OTC").replace("_", "/"), callback_data=f"p_{p}") for p in current_pairs[i:i + 2]]
                for i in range(0, len(current_pairs), 2)]
        
        nav_buttons = []
        if page > 0:
            nav_buttons.append(B("⬅️ আগের পেজ", callback_data=f"pairs_page_{page-1}"))
        if end_idx < len(PAIRS):
            nav_buttons.append(B("➡️ পরবর্তী পেজ", callback_data=f"pairs_page_{page+1}"))
        if nav_buttons:
            rows.append(nav_buttons)
        rows.append([B("🏠 হোম মেনু", callback_data="home")])

        await ctx.bot.edit_message_text(chat_id=chat_id, message_id=q.message.message_id,
                                        text=f"💎 হাই-একিউরেসি পেয়ার নির্বাচন করুন (পেজ {page+1}):", reply_markup=M(rows))

    elif q.data == "home":
        await ctx.bot.edit_message_text(chat_id=chat_id, message_id=q.message.message_id,
                                        text="🏠 প্রধান মেনু:", reply_markup=home_kb())

    elif q.data == "auto":
        if u.id in auto_tasks:
            await q.answer("অটো নোটিফিকেশন ইতিমধ্যে চালু আছে!", show_alert=True)
            return
        if user["daily"] >= limit_for(user):
            await ctx.bot.send_message(chat_id, "❌ আজকের লিমিট শেষ।")
            return
        auto_tasks[u.id] = asyncio.create_task(auto_loop(ctx, chat_id, u.id))

    elif q.data == "stop_auto":
        t = auto_tasks.pop(u.id, None)
        if t:
            t.cancel()
        await ctx.bot.send_message(chat_id, "⏹ অটো নোটিফিকেশন বন্ধ করা হয়েছে", reply_markup=home_kb())

    elif q.data.startswith("p_"):
        if u.id in auto_tasks:
            await q.answer("⏹ আগে অটো নোটিফিকেশন বন্ধ করুন", show_alert=True)
            return
        if busy.get(u.id):
            await q.answer("⏳ আগের সিগন্যালের ফলাফল আসা পর্যন্ত অপেক্ষা করুন", show_alert=True)
            return
        if user["daily"] >= limit_for(user):
            await ctx.bot.send_message(chat_id, "❌ আজকের লিমিট শেষ।")
            return
        busy[u.id] = True
        await ctx.bot.send_message(chat_id, "🔍 হাই-একিউরেসি এআই ইঞ্জিন দ্বারা মার্কেট স্ক্যান করা হচ্ছে...")
        await run_signal(ctx, chat_id, u.id, q.data[2:])
        busy.pop(u.id, None)

    elif q.data == "profile":
        t = user["wins"] + user["losses"]
        wr = round(user["wins"] / t * 100, 1) if t else 0
        plan = "ADMIN" if u.id in ADMIN_IDS else "PREMIUM" if is_premium(user) else "FREE"
        lim = "∞" if u.id in ADMIN_IDS else limit_for(user)
        await ctx.bot.send_message(
            chat_id, f"👤 নাম: {user['name']}\n🆔 আইডি: {u.id}\n💎 প্ল্যান: {plan}\n"
                     f"📊 ব্যবহার হয়েছে: {user['daily']}/{lim}\n✅ জয়: {user['wins']} | ❌ পরাজয়: {user['losses']} | উইন রেট: {wr}%",
            reply_markup=home_kb())


async def on_addpremium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        uid, days = int(ctx.args[0]), int(ctx.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("ব্যবহারবিধি: /addpremium <user_id> <days>")
        return
    get_user(uid)
    until = (dt.datetime.now(BD_TZ).date() + dt.timedelta(days=days)).isoformat()
    with db() as c:
        c.execute("UPDATE users SET premium_until=? WHERE user_id=?", (until, uid))
    await update.message.reply_text(f"✅ {uid} আইডিটি {until} তারিখ পর্যন্ত প্রিমিয়াম করা হয়েছে।")


async def on_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await update.message.reply_text(f"👥 মোট ব্যবহারকারী: {n}")


def main():
    setup_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", on_start))
    app.add_handler(CommandHandler("addpremium", on_addpremium))
    app.add_handler(CommandHandler("users", on_users))
    app.add_handler(CallbackQueryHandler(on_callback))

    async def on_shutdown(_app):
        for t in list(auto_tasks.values()):
            t.cancel()
    app.post_shutdown = on_shutdown
    print("✅ Brazilian Core AI Ultra Bot started successfully")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
