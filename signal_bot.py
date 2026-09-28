
"""
Telegram M1 Signal Bot (lean version)
Install:  pip install python-telegram-bot aiohttp numpy matplotlib
Run:      python signal_bot.py
"""
import asyncio
import datetime as dt
import io
import sqlite3
from typing import Dict, List, Optional, Tuple
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer


class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"Bot is running!")


def run_dummy_server():
  port = int(os.environ.get("PORT", 8080))
  server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
  server.serve_forever()


threading.Thread(target=run_dummy_server, daemon=True).start()

import aiohttp
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from telegram import InlineKeyboardButton as B, InlineKeyboardMarkup as M, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

# ==================== CONFIG ====================
BOT_TOKEN = "8419845332:AAGtdmayLgS7uJNiKWnqL4YzsISyMicPsfQ"
ADMIN_IDS = {6713482506: True}            # your Telegram user id(ASIFAJFX)
DB_PATH = "bot.db"
API_BASE = "https://quotexcandles.bdtraderpro.xyz/proversion/quotexcandles/Qx.php"
FREE_LIMIT, PREMIUM_LIMIT = 5, 25
MIN_SCORE = 3                      # |score| below this => NO TRADE
PAIRS = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc", "USDCAD_otc",
         "XAUUSD_otc", "BTCUSD_otc", "ETHUSD_otc", "USDBDT_otc", "USDINR_otc"]

busy: Dict[int, bool] = {}         # one live signal per user
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
    today = dt.date.today().isoformat()
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id,name,day) VALUES(?,?,?)", (uid, name, today))
        c.execute("UPDATE users SET daily=0, day=? WHERE user_id=? AND day!=?", (today, uid, today))
        r = c.execute("SELECT user_id,name,premium_until,daily,wins,losses FROM users WHERE user_id=?",
                      (uid,)).fetchone()
    return dict(zip(["id", "name", "premium_until", "daily", "wins", "losses"], r))


def is_premium(u: dict) -> bool:
    return u["id"] in ADMIN_IDS or (u["premium_until"] and u["premium_until"] >= dt.date.today().isoformat())


def limit_for(u: dict) -> int:
    return 10**6 if u["id"] in ADMIN_IDS else PREMIUM_LIMIT if is_premium(u) else FREE_LIMIT


def add_result(uid: int, win: bool):
    col = "wins" if win else "losses"
    with db() as c:
        c.execute(f"UPDATE users SET {col}={col}+1 WHERE user_id=?", (uid,))


def use_signal(uid: int):
    with db() as c:
        c.execute("UPDATE users SET daily=daily+1 WHERE user_id=?", (uid,))


# ==================== INDICATORS ====================
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
    for i in range(n, len(d)):                     # Wilder smoothing
        au, ad = (au * (n - 1) + up[i]) / n, (ad * (n - 1) + dn[i]) / n
    return 100.0 if ad == 0 else 100 - 100 / (1 + au / ad)


def analyze(candles: List[dict]) -> Tuple[Optional[str], int, dict]:
    """Return (direction or None, score, details). Score is a vote count, NOT a win probability."""
    if len(candles) < 60:
        return None, 0, {}
    c = np.array([float(k["close"]) for k in candles])
    e8, e21, e50 = ema(c, 8)[-1], ema(c, 21)[-1], ema(c, 50)[-1]
    macd = ema(c, 12) - ema(c, 26)
    hist = (macd - ema(macd, 9))[-1]
    r = rsi(c)
    mid, sd = c[-20:].mean(), c[-20:].std()
    price = c[-1]

    score, why = 0, []
    if e8 > e21 > e50:
        score += 2; why.append("EMA uptrend")
    elif e8 < e21 < e50:
        score -= 2; why.append("EMA downtrend")
    if hist > 0:
        score += 1; why.append("MACD +")
    elif hist < 0:
        score -= 1; why.append("MACD -")
    if r < 30:
        score += 1; why.append(f"RSI {r:.0f} oversold")
    elif r > 70:
        score -= 1; why.append(f"RSI {r:.0f} overbought")
    if price <= mid - 2 * sd:
        score += 1; why.append("Lower BB")
    elif price >= mid + 2 * sd:
        score -= 1; why.append("Upper BB")

    direction = "CALL" if score >= MIN_SCORE else "PUT" if score <= -MIN_SCORE else None
    return direction, score, {"rsi": round(r, 1), "why": why}


# ==================== DATA ====================
async def fetch_candles(pair: str, count: int = 100) -> List[dict]:
    url = f"{API_BASE}?pair={pair}&timeframe=M1&count={count}"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=12)) as r:
                data = (await r.json(content_type=None)).get("data", [])
        return sorted(data, key=lambda k: int(k.get("epoch", 0)))   # oldest -> newest
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
    ax.set_title(f"{pair.replace('_otc', '')} OTC  M1", color="white")
    ax.tick_params(colors="#8b949e"); ax.legend(facecolor="#161b22", labelcolor="white", loc="upper left")
    for sp in ax.spines.values():
        sp.set_color("#30363d")
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight"); plt.close(fig); buf.seek(0)
    return buf


# ==================== SIGNAL FLOW ====================
def home_kb():
    return M([[B("📊 New Signal", callback_data="pairs"), B("🤖 Auto Mode", callback_data="auto")],
              [B("👤 Profile", callback_data="profile")]])


def stop_kb():
    return M([[B("⏹ Stop Auto", callback_data="stop_auto")]])


async def run_signal(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int, pair: str,
                     quiet_no_trade: bool = False) -> bool:
    """Returns True if a signal was sent and its result was checked."""
    try:
        candles = await fetch_candles(pair)
        direction, score, info = analyze(candles)
        name = pair.replace("_otc", "")
        if not candles:
            await ctx.bot.send_message(chat_id, "❌ Market data পাওয়া যায়নি, আবার চেষ্টা করো।", reply_markup=home_kb())
            return False
        if direction is None:
            if not quiet_no_trade:
                await ctx.bot.send_message(
                    chat_id, f"⚪ {name}: NO TRADE\nসিগন্যাল পরিষ্কার না (score {score:+d}). অন্য পেয়ার ট্রাই করো।",
                    reply_markup=home_kb())
            return False

        entry = (dt.datetime.now() + dt.timedelta(minutes=1)).replace(second=0, microsecond=0)
        use_signal(uid)
        icon = "🟢" if direction == "CALL" else "🔴"
        await ctx.bot.send_photo(
            chat_id, build_chart(candles, pair, direction),
            caption=f"{icon} {name} OTC — {direction}\n"
            f"⏰ Entry: {entry:%H:%M} | Expiry: M1\n"
            f"📊 Strength: {abs(score)}/5 (এটা win-probability না)\n"
            f"📈 RSI {info['rsi']} | {', '.join(info['why'])}\n\n⏳ রেজাল্ট চেক হবে...")

        await asyncio.sleep(max(0, (entry + dt.timedelta(minutes=1, seconds=8) - dt.datetime.now()).total_seconds()))

        res = await fetch_candles(pair, 10)
        target = next((k for k in res if abs(int(k["epoch"]) - int(entry.timestamp())) <= 30), None)
        if not target:
            await ctx.bot.send_message(chat_id, "⚠️ রেজাল্ট candle পাওয়া যায়নি (গণনায় ধরা হয়নি)।", reply_markup=home_kb())
            return True
        o, cl = float(target["open"]), float(target["close"])
        win = cl > o if direction == "CALL" else cl < o
        add_result(uid, win)
        await ctx.bot.send_message(chat_id, f"{'✅ WIN' if win else '❌ LOSS'} — {name} {direction}\n"
                                            f"Open {o} → Close {cl}", reply_markup=None if uid in auto_tasks else home_kb())
        return True
    finally:
        busy.pop(uid, None)


async def auto_loop(ctx: ContextTypes.DEFAULT_TYPE, chat_id: int, uid: int):
    """Scan all pairs, take the strongest setup, repeat until limit or stop."""
    try:
        while True:
            user = get_user(uid)
            if user["daily"] >= limit_for(user):
                await ctx.bot.send_message(chat_id, "❌ আজকের লিমিট শেষ, অটো মোড বন্ধ।", reply_markup=home_kb())
                return
            results = await asyncio.gather(*[fetch_candles(p) for p in PAIRS])
            best = None
            for p, cs in zip(PAIRS, results):
                d, sc, _ = analyze(cs)
                if d and (best is None or abs(sc) > abs(best[1])):
                    best = (p, sc)
            if not best:
                await asyncio.sleep(45)          # no clean setup, rescan
                continue
            busy[uid] = True
            await run_signal(ctx, chat_id, uid, best[0], quiet_no_trade=True)
            await asyncio.sleep(5)
    except asyncio.CancelledError:
        raise
    finally:
        auto_tasks.pop(uid, None)
        busy.pop(uid, None)


# ==================== HANDLERS ====================
async def on_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    get_user(u.id, u.full_name)
    await update.message.reply_text(
        "👋 স্বাগতম!\nM1 টেকনিক্যাল সিগন্যাল বট।\n\n⚠️ এটা শুধু ইন্ডিকেটর-ভিত্তিক বিশ্লেষণ, কোনো লাভের গ্যারান্টি না। "
        "OTC মার্কেট ব্রোকারের নিজস্ব প্রাইস, তাই ডেমোতে টেস্ট করো।", reply_markup=home_kb())


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    u = q.from_user
    user = get_user(u.id, u.full_name)
    await q.answer()
    chat_id = q.message.chat_id

    if q.data == "pairs":
        rows = [[B(p.replace("_otc", ""), callback_data=f"p_{p}") for p in PAIRS[i:i + 2]]
                for i in range(0, len(PAIRS), 2)]
        await ctx.bot.send_message(chat_id, "💎 মার্কেট বেছে নাও:", reply_markup=M(rows))

    elif q.data == "auto":
        if busy.get(u.id) or u.id in auto_tasks:
            await q.answer("⏳ আগে চলমান সিগন্যাল/অটো শেষ করো", show_alert=True)
            return
        if user["daily"] >= limit_for(user):
            await ctx.bot.send_message(chat_id, "❌ আজকের লিমিট শেষ। আপগ্রেড করো বা কাল আবার এসো।")
            return
        await ctx.bot.send_message(chat_id, "🤖 AUTO MODE চালু\nসবচেয়ে পরিষ্কার সেটআপ খুঁজছি...", reply_markup=stop_kb())
        auto_tasks[u.id] = asyncio.create_task(auto_loop(ctx, chat_id, u.id))

    elif q.data == "stop_auto":
        t = auto_tasks.pop(u.id, None)
        if t:
            t.cancel()
        await ctx.bot.send_message(chat_id, "⏹ AUTO MODE বন্ধ", reply_markup=home_kb())

    elif q.data.startswith("p_"):
        if u.id in auto_tasks:
            await q.answer("⏹ আগে Auto বন্ধ করো", show_alert=True)
            return
        if busy.get(u.id):
            await q.answer("⏳ আগের সিগন্যালের রেজাল্টের জন্য অপেক্ষা করো", show_alert=True)
            return
        if user["daily"] >= limit_for(user):
            await ctx.bot.send_message(chat_id, "❌ আজকের লিমিট শেষ। আপগ্রেড করো বা কাল আবার এসো।")
            return
        busy[u.id] = True
        await ctx.bot.send_message(chat_id, "🔍 অ্যানালাইজ করছি...")
        asyncio.create_task(run_signal(ctx, chat_id, u.id, q.data[2:]))

    elif q.data == "profile":
        t = user["wins"] + user["losses"]
        wr = round(user["wins"] / t * 100, 1) if t else 0
        plan = "ADMIN" if u.id in ADMIN_IDS else "PREMIUM" if is_premium(user) else "FREE"
        lim = "∞" if u.id in ADMIN_IDS else limit_for(user)
        await ctx.bot.send_message(
            chat_id, f"👤 {user['name']}\n🆔 {u.id}\n💎 Plan: {plan}\n"
                     f"📊 আজ: {user['daily']}/{lim}\n✅ {user['wins']} | ❌ {user['losses']} | Win rate {wr}%",
            reply_markup=home_kb())


async def on_addpremium(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/addpremium <user_id> <days>  (admin only)"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        uid, days = int(ctx.args[0]), int(ctx.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /addpremium <user_id> <days>")
        return
    get_user(uid)
    until = (dt.date.today() + dt.timedelta(days=days)).isoformat()
    with db() as c:
        c.execute("UPDATE users SET premium_until=? WHERE user_id=?", (until, uid))
    await update.message.reply_text(f"✅ {uid} premium until {until}")


async def on_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    await update.message.reply_text(f"👥 Total users: {n}")


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
    print("✅ Bot started")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
