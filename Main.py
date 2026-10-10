import os, requests, time, threading, telebot, datetime
from flask import Flask

BOT_TOKEN=os.environ.get("BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
BRAND="KEVIN TRAILBLAZE"
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
        return float(r["price"])
    except: return 4195.60

def get_btc():
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()
        return float(r["bitcoin"]["usd"])
    except:
        try:
            r=requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10).json()
            return float(r["data"]["amount"])
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
        tag = "BULLISH LIFT-OFF" if action=="BUY" else "BEARISH DROP"
        emoji = "BUY" if action=="BUY" else "SELL"
        msg = f"""
{BRAND} - MAGNIFICENT SNIPER

{tag}
Asset: XAU/USD GOLD
Action: {action}
RSI: {rsi:.2f}
Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

ENTRY: ${price:.2f}
STOP LOSS: ${sl:.2f}

TAKE PROFITS:
TP1: ${tp1:.2f} +$20 RR 1:2
TP2: ${tp2:.2f} +$40 RR 1:4
TP3: ${tp3:.2f} +$60 RR 1:6

PLAN: Move SL to BE after TP1! Hold for TP2 VICTORY and TP3 JACKPOT!

VIP: @KEVINTRAILBLAZE
"""
    else:
        sl = price*0.99 if action=="BUY" else price*1.01
        tp1 = price*1.02 if action=="BUY" else price*0.98
        tp2 = price*1.04 if action=="BUY" else price*0.96
        tp3 = price*1.06 if action=="BUY" else price*0.94
        tag = "BITCOIN PUMP" if action=="BUY" else "BITCOIN DUMP"
        msg = f"""
{BRAND} - CRYPTO SNIPER

{tag}
Asset: BTC/USD
Action: {action}
RSI: {rsi:.2f}
Time: {datetime.datetime.utcnow().strftime('%H:%M UTC')}

ENTRY: ${price:,.2f}
SL: ${sl:,.2f}
TP1: ${tp1:,.2f} +2%
TP2: ${tp2:,.2f} +4%
TP3: ${tp3:,.2f} +6%

PLAN: TP1->BE, TP2=VICTORY, TP3=JACKPOT!

@KEVINTRAILBLAZE
"""
    try:
        bot.send_message(CHANNEL_ID, msg)
        active_signals.append({"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"tp1_hit":False,"tp2_hit":False,"tp3_hit":False})
    except Exception as e: print(e)

def check_tp_hits(current_price, symbol):
    for sig in active_signals[:]:
        if sig["symbol"]!=symbol: continue
        try:
            s_symbol = sig["symbol"]
            s_action = sig["action"]
            s_entry = sig["entry"]
            s_tp1 = sig["tp1"]
            s_tp2 = sig["tp2"]
            s_tp3 = sig["tp3"]
            s_sl = sig["sl"]
            if s_action=="BUY":
                if not sig["tp1_hit"] and current_price>=s_tp1:
                    sig["tp1_hit"]=True
                    bot.send_message(CHANNEL_ID,f"TP1 SECURED! {s_symbol} BUY - Entry {s_entry:.2f} -> TP1 {s_tp1:.2f} MOVE SL TO BE!")
                if not sig["tp2_hit"] and current_price>=s_tp2:
                    sig["tp2_hit"]=True
                    bot.send_message(CHANNEL_ID,f"VICTORY! {s_symbol} {s_action} WINNING! TP1 + TP2 HIT! Massive profit locked! Running to TP3 for JACKPOT! @KEVINTRAILBLAZE")
                if not sig["tp3_hit"] and current_price>=s_tp3:
                    bot.send_message(CHANNEL_ID,f"JACKPOT! ALL TP HIT! {s_symbol} {s_action} Entry {s_entry:.2f} -> {s_tp3:.2f} MAX PROFIT! @KEVINTRAILBLAZE")
                    active_signals.remove(sig)
                if current_price<=s_sl:
                    bot.send_message(CHANNEL_ID,f"SL HIT {s_symbol} BUY - Closed"); active_signals.remove(sig)
            else:
                if not sig["tp1_hit"] and current_price<=s_tp1:
                    sig["tp1_hit"]=True
                    bot.send_message(CHANNEL_ID,f"TP1 SECURED! {s_symbol} SELL - Entry {s_entry:.2f} -> TP1 {s_tp1:.2f} MOVE SL TO BE!")
                if not sig["tp2_hit"] and current_price<=s_tp2:
                    sig["tp2_hit"]=True
                    bot.send_message(CHANNEL_ID,f"VICTORY! {s_symbol} {s_action} WINNING! TP1 + TP2 HIT! Massive profit! Running to TP3! @KEVINTRAILBLAZE")
                if not sig["tp3_hit"] and current_price<=s_tp3:
                    bot.send_message(CHANNEL_ID,f"JACKPOT! ALL TP HIT! {s_symbol} {s_action} Entry {s_entry:.2f} -> {s_tp3:.2f} MAX PROFIT! @KEVINTRAILBLAZE")
                    active_signals.remove(sig)
                if current_price>=s_sl:
                    bot.send_message(CHANNEL_ID,f"SL HIT {s_symbol} SELL - Closed"); active_signals.remove(sig)
        except Exception as e: print(e)

def signal_loop():
    while True:
        try:
            now=time.time()
            if is_forex_market_open():
                g=get_gold(); prices_history.append(g)
                if len(prices_history)>50: prices_history.pop(0)
                r=calc_rsi(prices_history); check_tp_hits(g,"GOLD")
                if (r<30 or r>70):
                    if not any(s["symbol"]=="GOLD" for s in active_signals):
                        if now-last_signal_time.get("GOLD",0)>1800:
                            send_signal("GOLD",g,r,"BUY" if r<30 else "SELL")
                            last_signal_time["GOLD"]=now
            else:
                if active_signals:
                    g=get_gold(); check_tp_hits(g,"GOLD")
            b=get_btc(); btc_history.append(b)
            if len(btc_history)>50: btc_history.pop(0)
            r2=calc_rsi(btc_history); check_tp_hits(b,"BTC")
            if (r2<30 or r2>70):
                if not any(s["symbol"]=="BTC" for s in active_signals):
                    if now-last_signal_time.get("BTC",0)>1800:
                        send_signal("BTC",b,r2,"BUY" if r2<30 else "SELL")
                        last_signal_time["BTC"]=now
        except Exception as e: print(e)
        time.sleep(60)

@bot.message_handler(commands=['start','price','active','signal','analyze'])
def handle_start(message):
    g=get_gold(); b=get_btc()
    r_gold = calc_rsi(prices_history) if len(prices_history)>2 else 50.0
    r_btc = calc_rsi(btc_history) if len(btc_history)>2 else 50.0
    market = "OPEN" if is_forex_market_open() else "CLOSED Weekend"
    if message.text.startswith('/active'):
        if not active_signals: bot.reply_to(message,"No active signals - Bot analyzing...")
        else:
            txt=f"{BRAND} Active:\n"
            for s in active_signals:
                act = s["symbol"]; ent = s["entry"]
                txt+=f"{act} Entry {ent:.2f}\n"
            bot.reply_to(message,txt)
    elif message.text.startswith('/signal') or message.text.startswith('/analyze'):
        bot.reply_to(message,f"Analyzing...\nGOLD: ${g} RSI:{r_gold:.2f} Market: {market}\nBTC: ${b:,.2f} RSI:{r_btc:.2f} 24/7 OPEN\nWaiting RSI <30 BUY >70 SELL")
    else:
        bot.reply_to(message,f"{BRAND} MAGNIFICENT LIVE\nGOLD: ${g} ({market})\nBTC: ${b:,.2f}\nActive: {len(active_signals)}\n/price /signal /active")

threading.Thread(target=signal_loop,daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(),daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
