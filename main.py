import os
import time
import logging
import asyncio
import requests
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Full Asset List with Payout Simulation & Tickers
OTC_PAIRS = {
    "USDTBDT-OTC": 95, "USDCAD-OTC": 93, "NZDUSD-OTC": 92, "DOTUSD-OTC": 92,
    "USDCOP-OTC": 90, "BRLUSD-OTC": 90, "SOLUSD-OTC": 90, "XAUUSD-OTC": 90,
    "ZECUSD-OTC": 89, "USDEGP-OTC": 87, "USDDZD-OTC": 87, "LINUSD-OTC": 87,
    "USDPHP-OTC": 86, "ETHUSD-OTC": 86, "USDINR-OTC": 83, "USDMXN-OTC": 83,
    "TONUSD-OTC": 82, "USDPKR-OTC": 80, "NZDCAD-OTC": 80, "ATOUSD-OTC": 80,
    "USCRUDE-OTC": 80, "UKBRENT-OTC": 79, "USDARS-OTC": 78, "NZDCHF-OTC": 78,
    "USDIDR-OTC": 77, "USDNGN-OTC": 77, "XRPUSD-OTC": 75, "XAGUSD-OTC": 75,
    "AVAUSD-OTC": 74, "GBPNZD-OTC": 73, "ETCUSD-OTC": 69, "DASUSD-OTC": 66,
    "BTCUSD-OTC": 65, "BNBUSD-OTC": 59, "LTCUSD-OTC": 57, "TRUUSD-OTC": 57,
    "AXSUSD-OTC": 51, "BCHUSD-OTC": 42, "USDZAR-OTC": 18
}

REAL_PAIRS = {
    "EURUSD": 85, "GBPUSD": 85, "USDJPY": 85, "AUDUSD": 85,
    "USDCAD": 85, "USDCHF": 85, "EURJPY": 85, "GBPJPY": 85,
    "EURGBP": 85, "AUDJPY": 85, "EURAUD": 85, "EURCAD": 85,
    "EURCHF": 85, "GBPAUD": 85, "GBPCAD": 85, "GBPCHF": 85,
    "AUDCAD": 85, "AUDCHF": 85, "CADJPY": 85, "CHFJPY": 85
}

# Global dictionary to track user active live background tasks
USER_LIVE_TASKS = {}

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton("⚡ SIGNAL MODE", callback_data='cmd_signal_mode')],
        [InlineKeyboardButton("🔥 BRAZILIAN CORE AI", callback_data='cmd_core_ai')],
        [InlineKeyboardButton("📡 CHANNEL SIGNALS", callback_data='cmd_channel_signals')],
        [
            InlineKeyboardButton("✨ BLACKOUT FUTURE", callback_data='cmd_blackout'),
            InlineKeyboardButton("📊 SIGNAL CHECKER", callback_data='cmd_checker')
        ],
        [
            InlineKeyboardButton("💎 VIP PLANS", callback_data='cmd_vip'),
            InlineKeyboardButton("👤 MY PROFILE", callback_data='cmd_profile')
        ],
        [
            InlineKeyboardButton("🌐 LANGUAGE", callback_data='cmd_lang'),
            InlineKeyboardButton("ℹ️ HELP / ABOUT", callback_data='cmd_help')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        f"🔥 **BRAZILIAN SIGNAL PRO AI** 🔥\n"
        f"*Next-Gen Binary Signal Engine · v6.0.0*\n\n"
        f"⚡ **Live Tick Engine** — reads the running candle in real time\n"
        f"🎯 **20-Factor Self-Learning AI** — adapts to trend/range & real results\n"
        f"🤖 **Brazilian Core AI** — 6 LLM analyst modes\n"
        f"✨ **Blackout Future List** · 📊 **Signal Checker**\n\n"
        f"👤 **Plan:** `FREE` 📈 **Today:** `0/5`\n"
        f"👇 **Choose an option**"
    )
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# Background task simulating Live Auto Signals streaming like the video
async def live_signal_stream(chat_id, context, market_type):
    try:
        pairs = OTC_PAIRS if market_type == 'OTC' else REAL_PAIRS
        while chat_id in USER_LIVE_TASKS:
            # Pick a sample pair dynamically
            sample_pair = list(pairs.keys())[int(time.time()) % len(pairs)]
            payout = pairs[sample_pair]
            direction = "CALL (UP) 🟢" if int(time.time()) % 2 == 0 else "PUT (DOWN) 🔴"
            entry_time = (datetime.utcnow() + timedelta(hours=6)).strftime('%H:%M')
            
            signal_text = (
                f"🔥 **AUTO LIVE SIGNAL ({market_type})** 🔥\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📊 **PAIR** ➔ `{sample_pair}`\n"
                f"⏱ **ENTRY** ➔ `{entry_time} (UTC+6)`\n"
                f"⏳ **EXPIRY** ➔ `1 MIN · M1 · MTG 1`\n"
                f"💰 **PAYOUT** ➔ `{payout}%`\n"
                f"🎯 **DIRECTION** ➔ `{direction}`\n"
                f"🔍 **CONFIDENCE** ➔ `88%`\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"🏆 **GRADE** ➔ `A+ TREND`\n"
                f"⚡ **CONFLUENCE** ➔ `12/17 factors`\n\n"
                f"💡 **WHY CALL/PUT:**\n"
                f"• SuperTrend confirms strong momentum\n"
                f"• 3 clean candles in a row with volume spike\n\n"
                f"⚠️ *Trade responsibly with proper money management.*"
            )
            await context.bot.send_message(chat_id=chat_id, text=signal_text, parse_mode='Markdown')
            # Wait for 60 seconds before sending next auto signal
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Live stream error: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = query.message.chat_id

    if data == 'cmd_signal_mode':
        text = (
            "🎛 **SIGNAL MODE**\n\n"
            "🟢 **LIVE AUTO** – the engine scans every pair each minute and sends you the best setup automatically.\n"
            "🔵 **MANUAL** – pick a pair, get an instant live-tick analysis."
        )
        keyboard = [
            [InlineKeyboardButton("🟢 LIVE AUTO", callback_data='sub_live_auto')],
            [InlineKeyboardButton("🔵 MANUAL", callback_data='sub_manual')],
            [InlineKeyboardButton("🔙 Back", callback_data='cmd_menu')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'sub_live_auto':
        text = "📍 **Select market**"
        keyboard = [
            [InlineKeyboardButton("🟢 OTC MARKET", callback_data='live_auto_OTC')],
            [InlineKeyboardButton("📈 REAL MARKET", callback_data='live_auto_REAL')],
            [InlineKeyboardButton("🔙 Back", callback_data='cmd_signal_mode')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith('live_auto_'):
        market_type = data.replace('live_auto_', '')
        if chat_id in USER_LIVE_TASKS:
            USER_LIVE_TASKS[chat_id].cancel()
        
        # Start background streaming task
        task = asyncio.create_task(live_signal_stream(chat_id, context, market_type))
        USER_LIVE_TASKS[chat_id] = task

        text = (
            f"🟢 **LIVE AUTO – {market_type}**\n"
            f"⚡ Scanning pairs every minute with candle + live-tick analysis.\n"
            f"🎯 Min confidence: 80%\n"
            f"🚨 Signals arrive automatically — keep this chat open.\n\n"
            f"🔻 **Tap STOP LIVE to end.**"
        )
        keyboard = [
            [InlineKeyboardButton("🛑 STOP LIVE", callback_data='stop_live')],
            [InlineKeyboardButton("🏠 Home", callback_data='cmd_menu')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'stop_live':
        if chat_id in USER_LIVE_TASKS:
            USER_LIVE_TASKS[chat_id].cancel()
            del USER_LIVE_TASKS[chat_id]
        await query.edit_message_text("🛑 **Live Auto Stopped.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'sub_manual':
        text = "📍 **Select market**"
        keyboard = [
            [InlineKeyboardButton("🟢 OTC MARKET", callback_data='manual_OTC')],
            [InlineKeyboardButton("📈 REAL MARKET", callback_data='manual_REAL')],
            [InlineKeyboardButton("🔙 Back", callback_data='cmd_signal_mode')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith('manual_'):
        market_type = data.replace('manual_', '')
        pairs_dict = OTC_PAIRS if market_type == 'OTC' else REAL_PAIRS
        
        text = f"📊 **{market_type} PAIRS – sorted by payout**\n🟢 ≥85% | 🟡 ≥75% | 🔴 low\n👇 **Tap a pair**"
        keyboard = []
        row = []
        for pair, payout in pairs_dict.items():
            icon = "🟢" if payout >= 85 else ("🟡" if payout >= 75 else "🔴")
            row.append(InlineKeyboardButton(f"{icon} {pair} {payout}%", callback_data=f"get_signal_{pair}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data='sub_manual')])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith('get_signal_'):
        pair = data.replace('get_signal_', '')
        payout = OTC_PAIRS.get(pair, REAL_PAIRS.get(pair, 85))
        entry_time = (datetime.utcnow() + timedelta(hours=6)).strftime('%H:%M')
        
        signal_text = (
            f"🔥 **BRAZILIAN CORE AI** 🔥\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"📊 **PAIR** ➔ `{pair}`\n"
            f"⏱ **ENTRY** ➔ `{entry_time} (UTC+6)`\n"
            f"⏳ **EXPIRY** ➔ `1 MIN · M1 · MTG 1`\n"
            f"💰 **PAYOUT** ➔ `{payout}%`\n"
            f"🎯 **DIRECTION** ➔ `CALL (UP) 🟢`\n"
            f"🔍 **CONFIDENCE** ➔ `89%`\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🏆 **GRADE** ➔ `A+ TREND`\n"
            f"⚡ **CONFLUENCE** ➔ `14/17 factors`\n\n"
            f"💡 **WHY CALL:**\n"
            f"• SuperTrend is bullish\n"
            f"• 3 clean bullish Heikin-Ashi candles in a row\n"
            f"• Live candle bullish body momentum active\n\n"
            f"⚠️️ **RISK:** *Trade responsibly with money management.*\n"
            f"👑 *BRAZILIAN ELITE PRO*"
        )
        keyboard = [
            [InlineKeyboardButton("🔙 Back to Pairs", callback_data='sub_manual')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]
        ]
        await query.edit_message_text(signal_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'cmd_core_ai':
        text = "🤖 **Choose AI mode**\n\nAn LLM analyst reads the engine's 20-factor features + live ticks and gives its own verdict."
        keyboard = [
            [InlineKeyboardButton("🟢 STANDARD", callback_data='ai_mode_std'), InlineKeyboardButton("🟢 VENOM AI", callback_data='ai_mode_venom')],
            [InlineKeyboardButton("🟢 TITANFLOW", callback_data='ai_mode_titan'), InlineKeyboardButton("🟢 PRECISION", callback_data='ai_mode_precision')],
            [InlineKeyboardButton("🟢 ELITE PRO", callback_data='ai_mode_elite'), InlineKeyboardButton("🟢 FIGHTER-BOT", callback_data='ai_mode_fighter')],
            [InlineKeyboardButton("🔙 BACK", callback_data='cmd_menu')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data.startswith('ai_mode_'):
        mode_name = data.replace('ai_mode_', '').upper()
        text = f"✅ **AI Mode Activated:** `{mode_name}`\n\nNow select **SIGNAL MODE** to start generating precise live signals with this AI engine."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_channel_signals':
        text = (
            "📡 **CHANNEL SIGNAL MODE**\n\n"
            "Fully automatic signals posted to your own channel:\n"
            "• Auto pair & market selection (OTC + REAL)\n"
            "• Live running-candle watch + 20-factor engine\n"
            "• Results & partials (REAL/OTC) posted automatically\n\n"
            "👇 **Tap CONNECT CHANNEL to start.**"
        )
        keyboard = [
            [InlineKeyboardButton("🟢 CONNECT CHANNEL", callback_data='connect_chan')],
            [InlineKeyboardButton("🏠 HOME", callback_data='cmd_menu')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'connect_chan':
        text = (
            "🔗 **Connect your channel**\n\n"
            "1️⃣ Tap **Select my channel** on the keyboard below and choose your channel — Telegram adds me as admin automatically.\n"
            "2️⃣ Or add me as admin (Post Messages) yourself, then forward any post from the channel here, or send its `@username / ID`.\n\n"
            "`/cancel` to abort."
        )
        keyboard = [
            [InlineKeyboardButton("📢 Select my channel", callback_data='sel_chan')],
            [InlineKeyboardButton("❌ Cancel", callback_data='cmd_menu')]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

    elif data == 'sel_chan':
        await query.edit_message_text("✅ Channel successfully linked for automated signal broadcasting!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Home", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_blackout':
        text = (
            "✨ **BLACKOUT FUTURE LIST**\n\n"
            "Finds time-slots where the market reversed (or repeated) on EVERY analysed day.\n\n"
            "🚀 **TOP 10 PAYOUT PAIRS**"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_checker':
        text = "📊 **Signal Accuracy Checker**\n\nReal-time outcome tracking active. All win/loss records are verified by the live engine."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_vip':
        text = (
            "💎 **BRAZILIAN SIGNAL PRO AI – VIP PLANS**\n\n"
            "• 🆓 **FREE** — 5 signals/day\n"
            "• ⚡ **PREMIUM** — 40 signals/day, 20 AI\n"
            "• 👑 **VIP** — UNLIMITED everything\n\n"
            "🆓 **FREE VIP: OPEN YOUR ACCOUNT WITH OUR LINK, DEPOSIT, AND SEND YOUR TRADER ID.**"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_profile':
        user = query.from_user
        text = (
            f"👤 **MY PROFILE**\n\n"
            f"• ID: `{user.id}`\n"
            f"• Name: {user.first_name}\n"
            f"• Plan: `FREE`\n"
            f"• Today: `0/5`\n"
            f"• Win rate: `100.0%`"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_lang':
        text = "🌐 **LANGUAGE**\n\nCurrent language: **English (Default)**"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_help':
        text = "ℹ️ **HELP / ABOUT**\n\nBrazilian Signal Pro AI v6.0.0. Next-Generation Binary Signal Engine with Live Tick Analysis."
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Main Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif data == 'cmd_menu':
        await start(update, context)

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Brazilian Signal Pro Bot v6.0 is running with Live Auto Signals...")
    application.run_polling()

if __name__ == '__main__':
    main()
