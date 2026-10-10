import os, requests, time, threading, telebot, datetime
from flask import Flask

BOT_TOKEN=os.environ.get("BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
BRAND = "KEVIN TRAILBLAZE 👑"
bot=telebot.TeleBot(BOT_TOKEN)

prices_history=[]
btc_history=[]
active_signals=[]
last_signal_time={}

app=Flask(__name__)
@app.route('/')
def home(): return "KEVIN TRAILBLAZE MAGNIFICENT LIVE"

def get_gold():
    try:
        r=requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
        return float(r['price'])
    except: return 4195.60

def get_btc():
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()
        return float(r['bitcoin']['usd'])
    except:
        try:
            r=requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10).json()
            return float(r['data']['amount'])
        except: return 82600.0

def calc_rsi(prices, period=7):
    if len(prices)<period+1: return 50.0
    gains=[]; losses=[]
    for i in range(1, len(prices)):
        diff=prices[i]-prices[i-1]
        if diff>0: gains.append(diff); losses.append(0)
        else: gains.append(0); losses.append(abs(diff))
    if len(gains)<period: return 50.0
    avg_gain=sum(gains[-period:])/period
    avg_loss=sum(losses[-period:])/period
    if avg_loss==0: return 100.0
    rs=avg_gain/avg_loss
    return 100-(100/(1+rs))

def is_forex_market_open():
    return datetime.datetime.utcnow().weekday() < 5

def send_signal(symbol, price, rsi, action):
    if symbol=="GOLD":
        sl = price-10 if action=="BUY" else price+10
        tp1 = price+20 if action=="BUY" else price-20
        tp2 = price+40 if action=="BUY" else price-40
        tp3 = price+60 if action=="BUY" else price-60
        msg = f"""
╔════════════════════════════╗
║ {BRAND} ║
║ ⚡ MAGNIFICENT SNIPER ⚡ ║
╚════════════════════════════╝

{'💎🟢 GOLDEN BUY OPPORTUNITY 🟢💎' if action=='BUY' else '💎🔴 GOLDEN SELL OPPORTUNITY 🔴💎'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ ASSET: XAU/USD — GOLD
📈 SIGNAL: {action} NOW
📊 RSI(7): {rsi:.2f} → {'EXTREME OVERSOLD 🟢' if action=='BUY' else 'EXTREME OVERBOUGHT 🔴'}
⏰ TIME: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 ENTRY ZONE:
└─ ${price:.2f}

🛡️ STOP LOSS:
└─ ${sl:.2f} (-$10)

🎯 TAKE PROFIT LADDER:
├─ 🥇 TP1: ${tp1:.2f} (+$20) RR 1:2
├─ 🥈 TP2: ${tp2:.2f} (+$40) RR 1:4
└─ 🏆 TP3: ${tp3:.2f} (+$60) RR 1:6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 KEVIN'S PLAN:
1. Enter at ${price:.2f}
2. After TP1 → Move SL to BE (BreakEven)
3. Hold for TP2 = VICTORY 🏆
4. Hold for TP3 = JACKPOT 🤑

🔗 VIP: @KEVINTRAILBLAZE | TRAILBLAZE FX
#GOLD #XAUUSD #KEVINTRAILBLAZE
"""
    else:
        sl = price*0.99 if action=="BUY" else price*1.01
        tp1 = price*1.02 if action=="BUY" else price*0.98
        tp2 = price*1.04 if action=="BUY" else price*0.96
        tp3 = price*1.06 if action=="BUY" else price*0.94
        msg = f"""
╔════════════════════════════╗
║ {BRAND} ║
║ ₿ MAGNIFICENT CRYPTO ₿ ║
╚════════════════════════════╝

{'🚀🟢 BITCOIN PUMP ALERT 🟢🚀' if action=='BUY' else '💥🔴 BITCOIN DUMP ALERT 🔴💥'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏷️ ASSET: BTC/USD
📈 SIGNAL: {action} NOW
📊 RSI(7): {rsi:.2f} → {'OVERSOLD 🟢' if action=='BUY' else 'OVERBOUGHT 🔴'}
⏰ TIME: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 ENTRY ZONE:
└─ ${price:,.2f}

🛡️ STOP LOSS:
└─ ${sl:,.2f} (-1%)

🎯 TAKE PROFIT LADDER:
├─ 🥇 TP1: ${tp1:,.2f} (+2%)
├─ 🥈 TP2: ${tp2:,.2f} (+4%)
└─ 🏆 TP3: ${tp3:,.2f} (+6%)

📜 KEVIN'S PLAN: TP1 → BE, TP2 = VICTORY 🏆, TP3 = 🤑 JACKPOT!

🔗 VIP: @KEVINTRAILBLAZE
#BTC #BITCOIN #KEVINTRAILBLAZE
"""
    try:
        bot.send_message(CHANNEL_ID, msg)
        active_signals.append({"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"tp1_hit":False,"tp2_hit":False,"tp3_hit":False})
    except Exception as e: print(e)

def check_tp_hits(current_price, symbol):
    for sig in active_signals[:]:
        if sig["symbol"]!=symbol: continue
        try:
            if sig["action"]=="BUY":
                if not sig["tp1_hit"] and current_price>=sig["tp1"]:
                    sig["tp1_hit"]=True
                    bot.send_message(CHANNEL_ID,f"💸 TP1 SECURED! {symbol} BUY 💸\n{BRAND}\nEntry ${sig['entry']:.2f} → TP1 ${sig['tp1']:.2f} ✅\n🔒 MOVE SL TO BE NOW!")
                if not sig["tp2_hit"] and current_price>=sig["tp2"]:
                    sig["tp2_hit"]=True
                    bot.send_message(CHANNEL_ID,f"""
╔════════════════════╗
║ 🏆 VICTORY 🏆 ║
╚════════════════════╝
{BRAND} CALL IS WINNING!

{symbol} {sig['action
