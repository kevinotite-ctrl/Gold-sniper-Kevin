# -*- coding: utf-8 -*-
import os, requests, time, threading, telebot, datetime
from telebot import types
from flask import Flask

BOT_TOKEN=os.environ.get("BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
BRAND="KEVIN TRAILBLAZE"
ADMIN_ID = os.environ.get("ADMIN_ID")
ADMIN_CHAT_ID = None

bot=telebot.TeleBot(BOT_TOKEN)
prices_history=[]; btc_history=[]; active_signals=[]; last_signal_time={}; pending_signals={}

app=Flask(__name__)
@app.route('/')
def home(): return "KEVIN SHORT LUXURY LIVE"

def get_gold():
    try: return float(requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()["price"])
    except: return 4195.60
def get_btc():
    try: return float(requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()["bitcoin"]["usd"])
    except: return 82714.0
def calc_rsi(prices, period=7):
    if len(prices)<period+1: return 50.0
    gains=[]; losses=[]
    for i in range(1, len(prices)):
        diff=prices[i]-prices[i-1]
        if diff>0: gains.append(diff); losses.append(0)
        else: gains.append(0); losses.append(abs(diff))
    if len(gains)<period: return 50.0
    avg_gain=sum(gains[-period:])/period; avg_loss=sum(losses[-period:])/period
    if avg_loss==0: return 100.0
    rs=avg_gain/avg_loss; return 100-(100/(1+rs))
def is_forex_market_open(): return datetime.datetime.utcnow().weekday() < 5

def build_short_msg(symbol, price, rsi, action):
    # SHORT LUXURY DESIGN
    if symbol=="GOLD":
        sl = price-10 if action=="BUY" else price+10
        tp1 = price+20 if action=="BUY" else price-20
        tp2 = price+40 if action=="BUY" else price-40
        tp3 = price+60 if action=="BUY" else price-60
        emoji = "🟢 BUY" if action=="BUY" else "🔴 SELL"
        msg = f"""👑 KEVIN TRAILBLAZE 👑
{emoji} XAUUSD GOLD

💠 Entry: ${price:.2f}
🛡️ SL: ${sl:.2f}

🎯 TP1: ${tp1:.2f}
🎯 TP2: ${tp2:.2f}
🎯 TP3: ${tp3:.2f}

📊 RSI: {rsi:.1f}
🔗 @KEVINTRAILBLAZE"""
        data = {"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3}
        return msg, data
    else:
        sl = price*0.99 if action=="BUY" else price*1.01
        tp1 = price*1.02 if action=="BUY" else price*0.98
        tp2 = price*1.04 if action=="BUY" else price*0.96
        tp3 = price*1.06 if action=="BUY" else price*0.94
        emoji = "🟢 BUY" if action=="BUY" else "🔴 SELL"
        msg = f"""👑 KEVIN TRAILBLAZE 👑
{emoji} BTC/USD

💠 Entry: ${price:,.2f}
🛡️ SL: ${sl:,.2f}

🎯 TP1: ${tp1:,.2f}
🎯 TP2: ${tp2:,.2f}
🎯 TP3: ${tp3:,.2f}

📊 RSI: {rsi:.1f}
🔗 @KEVINTRAILBLAZE"""
        data = {"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3}
        return msg, data

def request_approval(symbol, price, rsi, action):
    global ADMIN_CHAT_ID
    target = None
    if ADMIN_ID:
        try: target = int(ADMIN_ID)
        except: pass
    if not target: target = ADMIN_CHAT_ID
    short_msg, data = build_short_msg(symbol, price, rsi, action)
    if not target:
        try:
            bot.send_message(CHANNEL_ID, short_msg)
            active_signals.append({**data,"tp1_hit":False,"tp2_hit":False,"tp3_hit":False})
        except Exception as e: print(e)
        return
    sig_id = f"{symbol}_{int(time.time())}"
    pending_signals[sig_id]=data
    pending_signals[sig_id]["_msg"] = short_msg
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ SEND", callback_data=f"approve_{sig_id}"), types.InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{sig_id}"))
    try: bot.send_message(target, f"🔔 NEW SIGNAL 👑\n\n{short_msg}\n\nSend to channel?", reply_markup=markup)
    except Exception as e: print(e)

def check_tp_hits(current_price, symbol):
    for sig in active_signals[:]:
        if sig["symbol"]!=symbol: continue
        try:
            s_sym=sig["symbol"]; s_act=sig["action"]; s_ent=sig["entry"]; s_tp1=sig["tp1"]; s_tp2=sig["tp2"]; s_tp3=sig["tp3"]; s_sl=sig["sl"]
            if s_act=="BUY":
                if not sig["tp1_hit"] and current_price>=s_tp1:
                    sig["tp1_hit"]=True
                    bot.send_message(CHANNEL_ID,f"💸 TP1 HIT ✅\n{s_sym} BUY\n${s_ent:.2f} → ${s_tp1:.2f}\n🔒 Move SL to BE\n@KEVINTRAILBLAZE")
                if not sig["tp2_hit"] and current_price>=s_tp2:
                    sig["tp2_hit"]=True
                    bot.send_message(CHANNEL_ID,f"🏆 VICTORY 🏆\n{s_sym} TP1 + TP2 HIT\n@KEVINTRAILBLAZE")
                if not sig["tp3_hit"] and current_price>=s_tp3:
                    bot.send_message(CHANNEL_ID,f"🤑 JACKPOT 🤑\n{s_sym} ALL TP HIT!\n${s_ent:.2f} → ${s_tp3:.2f}\n@KEVINTRAILBLAZE")
                    active_signals.remove(sig)
                if current_price<=s_sl:
                    bot.send_message(CHANNEL_ID,f"🛑 SL HIT {s_sym}"); active_signals.remove(sig)
            else:
                if not sig["tp1_hit"] and current_price<=s_tp1:
                    sig["tp1_hit"]=True
                    bot.send_message(CHANNEL_ID,f"💸 TP1 HIT ✅\n{s_sym} SELL\n${s_ent:.2f} → ${s_tp1:.2f}\n@KEVINTRAILBLAZE")
                if not sig["tp2_hit"] and current_price<=s_tp2:
                    sig["tp2_hit"]=True
                    bot.send_message(CHANNEL_ID,f"🏆 VICTORY 🏆\n{s_sym} TP1 + TP2 HIT\n@KEVINTRAILBLAZE")
                if not sig["tp3_hit"] and current_price<=s_tp3:
                    bot.send_message(CHANNEL_ID,f"🤑 JACKPOT 🤑\n{s_sym} ALL TP HIT!\n@KEVINTRAILBLAZE")
                    active_signals.remove(sig)
                if current_price>=s_sl:
                    bot.send_message(CHANNEL_ID,f"🛑 SL HIT {s_sym}"); active_signals.remove(sig)
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
                            request_approval("GOLD",g,r,"BUY" if r<30 else "SELL")
                            last_signal_time["GOLD"]=now
            else:
                if active_signals:
                    g=get_gold(); check_tp_hits(g,"GOLD")
            b=get_btc(); btc_history.append(b)
            if len(btc_history)>50: btc_history.pop(0)
            r2=calc_rsi(btc_history); check_tp_hits(b,"BTC")
            if (r2<30 or r2>70):
                if not any(s["symbol"]=="BTC" for s in active_signals):
                    if now-last_signal_time.get
