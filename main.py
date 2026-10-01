# ============================================================
# QUOTEX DEMO BOT - MOBILE FRIENDLY
# ============================================================

# ---------- STEP 1: Install ----------
print("লাইব্রেরি ইনস্টল হচ্ছে... (২-৩ মিনিট লাগবে)")
!pip install -q pyquotex smartmoneyconcepts pandas numpy colorama
print("✅ Install সম্পন্ন!\n")

# ---------- STEP 2: Imports ----------
import asyncio, pandas as pd, numpy as np
from datetime import datetime

# ============================================================
# ⚠️ এখানে আপনার ডেমো অ্যাকাউন্টের তথ্য বসান
# ============================================================
EMAIL = "এখানে_তোমার_ডেমো_ইমেইল"
PASSWORD = "এখানে_তোমার_ডেমো_পাসওয়ার্ড"

# ============================================================
# সেটিংস (এগুলো পরিবর্তন করতে পারেন)
# ============================================================
ASSET = "EURUSD_otc"        # অ্যাসেট
TIMEFRAME = 60              # ৬০ সেকেন্ড ক্যান্ডেল
TRADE_DURATION = 60         # ট্রেড ৬০ সেকেন্ডের
MIN_CONFIDENCE = 65         # এর নিচে ট্রেড করবে না

SIGNAL_ONLY = True          # True = শুধু সিগন্যাল দেখাবে (নিরাপদ!)
                            # False = ডেমোতে ট্রেড বসাবে

BASE_AMOUNT = 1.0           # প্রতি ট্রেডে $১
MAX_TRADES = 20             # সেশন প্রতি সর্বোচ্চ ২০ ট্রেড
MAX_LOSS = 50.0             # $৫০ লস হলে বন্ধ

# ============================================================
# সিগন্যাল ইঞ্জিন
# ============================================================
def analyze(df):
    if len(df) < 50:
        return {"dir": "NONE", "conf": 0, "reasons": []}
    
    df = df.copy()
    df["ema20"] = df["close"].ewm(span=20).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    
    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = -delta.where(delta < 0, 0).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    
    last, prev = df.iloc[-1], df.iloc[-2]
    
    bull, bear, reasons = 0, 0, []
    
    # Engulfing
    if prev["close"] < prev["open"] and last["close"] > last["open"] and last["close"] > prev["open"]:
        bull += 2; reasons.append("Bullish Engulfing")
    if prev["close"] > prev["open"] and last["close"] < last["open"] and last["close"] < prev["open"]:
        bear += 2; reasons.append("Bearish Engulfing")
    
    # Trend
    if last["close"] > last["ema20"] > last["ema50"]:
        bull += 1; reasons.append("Uptrend")
    elif last["close"] < last["ema20"] < last["ema50"]:
        bear += 1; reasons.append("Downtrend")
    
    # RSI
    if last["rsi"] < 30:
        bull += 1; reasons.append(f"RSI oversold {last['rsi']:.0f}")
    elif last["rsi"] > 70:
        bear += 1; reasons.append(f"RSI overbought {last['rsi']:.0f}")
    
    if bull >= 3 and bull > bear:
        return {"dir": "CALL", "conf": min(100, bull*20), "reasons": reasons}
    if bear >= 3 and bear > bull:
        return {"dir": "PUT", "conf": min(100, bear*20), "reasons": reasons}
    return {"dir": "NONE", "conf": 0, "reasons": reasons}

# ============================================================
# মেইন বট
# ============================================================
async def run_bot():
    from pyquotex.stable_api import Quotex
    
    print("="*50)
    print("  QUOTEX BOT চালু হচ্ছে")
    print("="*50)
    print(f"অ্যাসেট: {ASSET}")
    print(f"সিগন্যাল অনলি: {SIGNAL_ONLY}")
    print(f"প্রতি ট্রেড: ${BASE_AMOUNT}\n")
    
    client = Quotex(email=EMAIL, password=PASSWORD)
    ok, msg = await client.connect()
    if not ok:
        print(f"❌ কানেক্ট ফেইল: {msg}")
        return
    
    bal = await client.get_balance()
    print(f"✅ কানেক্টেড! ব্যালেন্স: ${bal}\n")
    
    await client.start_candles_stream(ASSET, TIMEFRAME, 200)
    print(f"📊 {ASSET} ডেটা স্ট্রিম শুরু...\n")
    
    trades, wins, total_pnl = 0, 0, 0.0
    last_sig_time = 0
    
    try:
        while True:
            await asyncio.sleep(5)
            
            raw = await client.get_realtime_candles(ASSET, TIMEFRAME)
            if not raw:
                continue
            
            rows = [{"time": pd.to_datetime(int(t), unit="s"),
                     "open": c["open"], "high": c["high"],
                     "low": c["low"], "close": c["close"],
                     "volume": c.get("volume", 0)} for t, c in raw.items()]
            df = pd.DataFrame(rows).sort_values("time").reset_index(drop=True).iloc[:-1]
            
            if len(df) < 50:
                continue
            
            sig = analyze(df)
            if sig["dir"] == "NONE":
                continue
            
            now = datetime.now().timestamp()
            if now - last_sig_time < 120:
                continue
            last_sig_time = now
            
            # সিগন্যাল প্রিন্ট
            emoji = "🟢" if sig["dir"] == "CALL" else "🔴"
            print(f"\n{'='*50}")
            print(f"{emoji} সিগন্যাল: {sig['dir']}  |  কনফিডেন্স: {sig['conf']}%")
            print(f"💰 প্রাইস: {df.iloc[-1]['close']}")
            print(f"🕐 সময়: {datetime.now().strftime('%H:%M:%S')}")
            for r in sig["reasons"]:
                print(f"   • {r}")
            print(f"{'='*50}")
            
            if SIGNAL_ONLY:
                continue
            
            if sig["conf"] < MIN_CONFIDENCE:
                print(f"⏭️ কনফিডেন্স কম, স্কিপ করছি")
                continue
            
            if trades >= MAX_TRADES or total_pnl <= -MAX_LOSS:
                print("🛑 সীমা শেষ। বট বন্ধ।")
                break
            
            # ট্রেড
            print(f"🚀 ট্রেড: ${BASE_AMOUNT} {sig['dir']}")
            try:
                ok2, info = await client.buy(
                    amount=BASE_AMOUNT, asset=ASSET,
                    direction=sig["dir"].lower(), duration=TRADE_DURATION
                )
                if not ok2:
                    print(f"❌ রিজেক্ট: {info}")
                    continue
                
                tid = info.get("id") if isinstance(info, dict) else info
                print(f"⏳ অপেক্ষা {TRADE_DURATION}s...")
                win = await client.check_win(tid)
                
                trades += 1
                if win:
                    wins += 1
                    pnl = BASE_AMOUNT * 0.85
                    total_pnl += pnl
                    print(f"✅ WIN! +${pnl:.2f}")
                else:
                    total_pnl -= BASE_AMOUNT
                    print(f"❌ LOSS! -${BASE_AMOUNT:.2f}")
                
                nb = await client.get_balance()
                wr = (wins/trades*100) if trades else 0
                print(f"📊 ট্রেড {trades} | উইন {wins} ({wr:.0f}%) | PnL ${total_pnl:.2f} | Bal ${nb:.2f}")
                
            except Exception as e:
                print(f"❌ এরর: {e}")
    
    except KeyboardInterrupt:
        print("\n🛑 বন্ধ।")
    except Exception as e:
        print(f"\n❌ বট এরর: {e}")
    finally:
        try:
            await client.stop_candles_stream(ASSET)
            await client.close()
        except:
            pass
        print("\n=== শেষ ===")

await run_bot()
