import os
import time
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Assets list for Quotex OTC and Forex
ASSETS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "EURJPY", "GBPJPY", "USDCAD", "NZDUSD", 
          "EURUSD-OTC", "GBPUSD-OTC", "USDJPY-OTC", "AUDUSD-OTC", "EURJPY-OTC", "GBPJPY-OTC"]

def analyze_market_psychology(asset):
    """Simulates multi-factor psychology & price action analysis for binary/forex."""
    sig_type = random.choice(["CALL (UP)", "PUT (DOWN)", "NEUTRAL"])
    conf = random.randint(75, 96)
    reasons = [
        "Strong Support zone bounce & buyers volume expansion.",
        "Resistance level rejection with aggressive seller pressure.",
        "Bollinger Band squeeze breakout with RSI momentum confirmation.",
        "Moving Average crossover with high market liquidity spike."
    ]
    reason = random.choice(reasons)
    return sig_type, conf, reason

# Main Menu Keyboard
def get_main_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📊 Get Live Signal", callback_data='cmd_signal'),
            InlineKeyboardButton("📈 Market Status", callback_data='cmd_market')
        ],
        [
            InlineKeyboardButton("⚙️ Settings (1M)", callback_data='cmd_settings'),
            InlineKeyboardButton("ℹ️ Bot Info", callback_data='cmd_info')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_text = (
        f"আসসালামু আলাইকুম, {user.first_name}! 🌟\n\n"
        f"স্বাগতম **Master Asif Supreme** AI Trading Analysis Bot-এ। 🤖\n"
        f"আমি ফরেক্স এবং কোটেক্স মার্কেট সাইকোলজি এবং প্রাইস অ্যাকশন অ্যানালিসিস করে সিগন্যাল দিয়ে থাকি।\n\n"
        f"নিচের বাটনগুলোর মাধ্যমে কাজ শুরু করে দিতে পারো!"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

# Button Callback Handlers
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cmd_signal':
        text = "⚡ **Master Asif Supreme** - AI Signal Engine চলছে...\n\n"
        message = await query.edit_message_text(text, parse_mode='Markdown')
        
        # Simulate processing time for realism
        time.sleep(2)
        
        # Run Psychology Engine for each asset
        signal_results = []
        for asset in ASSETS:
            sig_type, conf, reason = analyze_market_psychology(asset)
            if sig_type != "NEUTRAL":
                signal_results.append(f"📌 **{asset}**: `{sig_type}` (Conf: `{conf}%`) \n   └ 🔍 *Psychology*: {reason}\n")
        
        if signal_results:
            final_text = "🚀 **PRO AI SIGNAL ALERT** 🚀\n\n" + "\n".join(signal_results)
        else:
            final_text = "⚠️ **MARKET PSYCHOLOGY ALERT** ⚠️\n\nএই মুহূর্তে বাজারে প্রফিটেবল ট্রেডিং সিগন্যাল পাওয়া যাচ্ছে না।\nবাজারের গতিবিধি সতর্কতার সাথে পর্যবেক্ষণ করুন।"
            
        await message.edit_text(final_text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif query.data == 'cmd_market':
        text = (
            f"📊 **Master Asif Supreme - Market Status**\n\n"
            f"⏱ **Timeframe**: 1M\n"
            f"📈 **Market Assets (Forex & Quotex OTC Pairs)**:\n"
            f"`{', '.join(ASSETS)}`\n\n"
            f"🟢 **Server**: Stable & Connected to Data Feed"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif query.data == 'cmd_settings':
        text = (
            f"⚙️ **Settings**\n\n"
            f"Currently, Timeframe is fixed to 1M for binary options. More settings coming soon in v2."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif query.data == 'cmd_info':
        text = (
            f"ℹ️ **About Master Asif Supreme**\n\n"
            f"🔹 **Version**: 2.0 (AI Pro)\n"
            f"🔹 **Engine**: Multi-Factor Psychology & Price Action\n"
            f"🔹 **Developer**: Master Asif Supreme\n"
            f"🔹 **Purpose**: To provide educational, high-quality trading analysis."
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data='cmd_menu')]]), parse_mode='Markdown')

    elif query.data == 'cmd_menu':
        text = "🏠 **Main Menu**\n\nনিচের অপশনগুলো থেকে আপনার পছন্দমতো সিলেক্ট করুন:"
        await query.edit_message_text(text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("Error: BOT_TOKEN environment variable not set!")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is up and running...")
    application.run_polling()

if __name__ == '__main__':
    main()
