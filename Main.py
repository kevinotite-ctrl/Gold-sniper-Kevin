import os, requests, time, threading, pytz, telebot
from flask import Flask
from datetime import datetime

BOT_TOKEN=os.environ.get("BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
bot=telebot.TeleBot(BOT_TOKEN)

prices_history=[]
btc_history=[]
active_signals=[] # To track TP hits

app=Flask(__name__)
@app.route('/')
def home(): return "Gold + BTC 3TP Sniper LIVE"

def get_gold():
    try:
        r=requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
        return float(r['price'])
    except: return 4196.90

def get_btc():
    try:
        r=requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10).json()
        return float(r['price'])
    except: return 108000.0

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

def send_signal(symbol, price, rsi, action):
    if symbol=="GOLD":
        sl = price-10 if action=="BUY" else price+10
        tp1 = price+20 if action=="BUY" else price-20
        tp2 = price+40 if action=="BUY" else price-40
        tp3 = price+60 if action=="BUY" else price-60
        emoji = "🟢" if action=="BUY" else "🔴"
        msg = f"{emoji} **{action} SIGNAL — XAU/USD**\n\n📉 RSI (7): {rsi:.2f}\n💰 Price: ${price}\n\n🎯 Entry: ${price}\n🛑 SL: ${sl:.2f}\n✅ TP1: ${tp1:.2f} (+$20) RR 1:2\n✅ TP2: ${tp2:.2f} (+$40) RR 1:4\n✅ TP3: ${tp3:.2f} (+$60) RR 1:6\n\n⚠️ Move SL to BE after TP1!\n#GOLD #XAUUSD"
    else:
        sl = price*0.99 if action=="BUY" else price*1.01
        tp1 = price*1.02 if action=="BUY" else price*0.98
        tp2 = price*1.04 if action=="BUY" else price*0.96
        tp3 = price*1.06 if action=="BUY" else price*0.94
        emoji = "🟢" if action=="BUY" else "🔴"
        msg = f"{emoji} **{action} SIGNAL — BTC/USD**\n\n📉 RSI (7): {rsi:.2f}\n💰 Price: ${price:,.2f}\n\n🎯 Entry: ${price:,.2f}\n🛑 SL: ${sl:,.2f} (-1%)\n✅ TP1: ${tp1:,.2f} (+2%) RR 1:2\n✅ TP2: ${tp2:,.2f} (+4%) RR 1:4\n✅ TP3: ${tp3:,.2f} (+6%) RR 1:6\n\n⚠️ Move SL to BE after TP1!\n#BTC #BITCOIN"

    try:
        bot.send_message(CHANNEL_ID, msg, parse_mode="Markdown")
        # Save signal to track TP hits
        active_signals.append({
            "symbol": symbol, "action": action, "entry": price,
            "sl": sl, "tp1": tp1, "tp2": tp2, "tp3": tp3,
            "tp1_hit": False, "tp2_hit": False, "tp3_hit": False
        })
        print(f"Signal saved: {symbol} {action}")
    except Exception as e: print(e)

def check_tp_hits(current_price, symbol):
    global active_signals
    for sig in active_signals[:]:
        if sig["symbol"]!= symbol: continue
        action = sig["action"]

        # Check TP hits
        if action == "BUY":
            if not sig["tp1_hit"] and current_price >= sig["tp1"]:
                sig["tp1_hit"]=True
                bot.send_message(CHANNEL_ID, f"💰 **TP1 HIT! {symbol}**\n\n✅ Price hit ${sig['tp1']:.2f}\n📈 +2% Profit Secured!\nMove SL to BreakEven now!\n\n#TP1 #{symbol}")
            if not sig["tp2_hit"] and current_price >= sig["tp2"]:
                sig["tp2_hit"]=True
                bot.send_message(CHANNEL_ID, f"💰💰 **TP2 HIT! {symbol}**\n\n✅ Price hit ${sig['tp2']:.2f}\n📈 +4% Profit Secured!\n\n#TP2 #{symbol}")
            if not sig["tp3_hit"] and current_price >= sig["tp3"]:
                sig["tp3_hit"]=True
                bot.send_message(CHANNEL_ID, f"💰💰💰 **TP3 HIT! {symbol} FULL TP!**\n\n🎉🎉 Price hit ${sig['tp3']:.2f}\n📈 +6% ALL TARGETS HIT!\n\n#TP3 #{symbol}")
                active_signals.remove(sig)
            if current_price <= sig["sl"]:
                bot.send_message(CHANNEL_ID, f"🛑 **SL HIT {symbol}**\n\nPrice: ${current_price:.2f}\nSignal closed at SL\n\n#SL #{symbol}")
                active_signals.remove(sig)
        else: # SELL
            if not sig["tp1_hit"] and current_price <= sig["tp1"]:
                sig["tp1_hit"]=True
                bot.send_message(CHANNEL_ID, f"💰 **TP1 HIT! {symbol}**\n\n✅ Price hit ${sig['tp1']:.2f}\n📉 +2% Profit Secured!\nMove SL to BreakEven!\n\n#TP1 #{symbol}")
            if not sig["tp2_hit"] and current_price <= sig["tp2"]:
                sig["tp2_hit"]=True
                bot.send_message(CHANNEL_ID, f"💰💰 **TP2 HIT! {symbol}**\n\n✅ Price hit ${sig['tp2']:.2f}\n📉 +4% Profit Secured!\n\n#TP2 #{symbol}")
            if not sig["tp3_hit"] and current_price <= sig["tp3"]:
                sig["tp3_hit"]=True
                bot.send_message(CHANNEL_ID, f"💰💰💰 **TP3 HIT! {symbol} FULL TP!**\n\n🎉🎉 Price hit ${sig['tp3']:.2f}\n📉 +6% ALL TARGETS HIT!\n\n#TP3 #{symbol}")
                active_signals.remove(sig)
            if current_price >= sig["sl"]:
                bot.send_message(CHANNEL_ID, f"🛑 **SL HIT {symbol}**\n\nPrice: ${current_price:.2f}\nSignal closed at SL\n\n#SL #{symbol}")
                active_signals.remove(sig)

def signal_loop():
    while True:
        try:
            g=get_gold()
            prices_history.append(g)
            if len(prices_history)>50: prices_history.pop(0)
            r=calc_rsi(prices_history)
            check_tp_hits(g, "GOLD")
            if r<30: send_signal("GOLD", g, r, "BUY")
            elif r>70: send_signal("GOLD", g, r, "SELL")

            b=get_btc()
            btc_history.append(b)
            if len(btc_history)>50: btc_history.pop(0)
            r2=calc_rsi(btc_history)
            check_tp_hits(b, "BTC")
            if r2<30: send_signal("BTC", b, r2, "BUY")
            elif r2>70: send_signal("BTC", b, r2, "SELL")

        except Exception as e: print(f"Error: {e}")
        time.sleep(60)

@bot.message_handler(commands=['start','price','active'])
def handle_start(message):
    g=get_gold(); b=get_btc()
    if message.text.startswith('/active'):
        if not active_signals: bot.reply_to(message, "No active signals running")
        else:
            txt="📊 Active Signals:\n"
            for s in active_signals: txt+=f"{s['symbol']} {s['action']} Entry {s['entry']} TP1:{s['tp1_hit']} TP2:{s['tp2_hit']}\n"
            bot.reply_to(message, txt)
    else:
        bot.reply_to(message, f"🤖 3TP Sniper LIVE ✅\n\n🥇 GOLD: ${g}\n₿ BTC: ${b:,.2f}\n📊 Active: {len(active_signals)}\n\nCommands:\n/price - prices\n/active - active signals")

threading.Thread(target=signal_loop, daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(), daemon=True).start()

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
