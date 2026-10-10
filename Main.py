# -*- coding: utf-8 -*-
import os, requests, time, threading, telebot, datetime, json
from telebot import types
from flask import Flask

BOT_TOKEN=os.environ.get("BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
ADMIN_ID=os.environ.get("ADMIN_ID")
ADMIN_CHAT_ID=None

bot=telebot.TeleBot(BOT_TOKEN)
prices_history=[]
btc_history=[]
last_signal_time={}
pending_signals={}
ACTIVE_FILE="active_signals.json"

# === PERSISTENT STORAGE FIX ===
def save_active():
    try:
        with open(ACTIVE_FILE,"w") as f:
            json.dump(active_signals,f)
    except:
        pass

def load_active():
    global active_signals
    try:
        if os.path.exists(ACTIVE_FILE):
            with open(ACTIVE_FILE,"r") as f:
                active_signals=json.load(f)
        else:
            active_signals=[]
    except:
        active_signals=[]

active_signals=[]
load_active()

app=Flask(__name__)
@app.route('/')
def home():
    return "KEVIN SHORT LUXURY V2 LIVE"

def get_gold():
    try:
        r=requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
        return float(r["price"])
    except:
        return 4195.60

def get_btc():
    try:
        r=requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=10).json()
        return float(r["bitcoin"]["usd"])
    except:
        return 82714.0

def calc_rsi(prices, period=14):
    if len(prices) < period+1:
        return 50.0
    gains=[]
    losses=[]
    for i in range(1, len(prices)):
        diff=prices[i]-prices[i-1]
        if diff>0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))
    if len(gains)<period:
        return 50.0
    avg_gain=sum(gains[-period:])/period
    avg_loss=sum(losses[-period:])/period
    if avg_loss==0:
        return 70.0
    if avg_gain==0:
        return 30.0
    rs=avg_gain/avg_loss
    rsi=100-(100/(1+rs))
    if rsi==0:
        return 30.0
    return rsi

def is_forex_market_open():
    return datetime.datetime.utcnow().weekday() < 5

def build_short_msg(symbol, price, rsi, action):
    if symbol=="GOLD":
        sl=price-10 if action=="BUY" else price+10
        tp1=price+20 if action=="BUY" else price-20
        tp2=price+40 if action=="BUY" else price-40
        tp3=price+60 if action=="BUY" else price-60
        emoji="🟢 BUY" if action=="BUY" else "🔴 SELL"
        msg="👑 KEVIN TRAILBLAZE 👑\n"+emoji+" XAUUSD GOLD\n\n💠 Entry: $"+str(round(price,2))+"\n🛡️ SL: $"+str(round(sl,2))+"\n\n🎯 TP1: $"+str(round(tp1,2))+"\n🎯 TP2: $"+str(round(tp2,2))+"\n🎯 TP3: $"+str(round(tp3,2))+"\n\n📊 RSI: "+str(round(rsi,1))+"\n🔗 @KEVINTRAILBLAZE"
        data={"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3}
        return msg,data
    else:
        sl=price*0.99 if action=="BUY" else price*1.01
        tp1=price*1.02 if action=="BUY" else price*0.98
        tp2=price*1.04 if action=="BUY" else price*0.96
        tp3=price*1.06 if action=="BUY" else price*0.94
        emoji="🟢 BUY" if action=="BUY" else "🔴 SELL"
        msg="👑 KEVIN TRAILBLAZE 👑\n"+emoji+" BTC/USD\n\n💠 Entry: $"+str(round(price,2))+"\n🛡️ SL: $"+str(round(sl,2))+"\n\n🎯 TP1: $"+str(round(tp1,2))+"\n🎯 TP2: $"+str(round(tp2,2))+"\n🎯 TP3: $"+str(round(tp3,2))+"\n\n📊 RSI: "+str(round(rsi,1))+"\n🔗 @KEVINTRAILBLAZE"
        data={"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3}
        return msg,data

def request_approval(symbol, price, rsi, action):
    global ADMIN_CHAT_ID
    target=None
    if ADMIN_ID:
        try:
            target=int(ADMIN_ID)
        except:
            pass
    if not target:
        target=ADMIN_CHAT_ID
    short_msg,data=build_short_msg(symbol, price, rsi, action)
    if not target:
        try:
            bot.send_message(CHANNEL_ID, short_msg)
            active_signals.append({"symbol":data["symbol"],"action":data["action"],"entry":data["entry"],"sl":data["sl"],"tp1":data["tp1"],"tp2":data["tp2"],"tp3":data["tp3"],"tp1_hit":False,"tp2_hit":False,"tp3_hit":False})
            save_active()
        except Exception as e:
            print(e)
        return
    sig_id=symbol+"_"+str(int(time.time()))
    pending_signals[sig_id]=data
    pending_signals[sig_id]["_msg"]=short_msg
    markup=types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ SEND", callback_data="approve_"+sig_id), types.InlineKeyboardButton("❌ REJECT", callback_data="reject_"+sig_id))
    try:
        bot.send_message(target, "🔔 NEW SIGNAL 👑\n\n"+short_msg+"\n\nSend to channel?", reply_markup=markup)
    except Exception as e:
        print(e)

def check_tp_hits(current_price, symbol):
    for sig in active_signals[:]:
        if sig["symbol"]!=symbol:
            continue
        try:
            s_sym=sig["symbol"]
            s_act=sig["action"]
            s_ent=sig["entry"]
            s_tp1=sig["tp1"]
            s_tp2=sig["tp2"]
            s_tp3=sig["tp3"]
            s_sl=sig["sl"]
            if s_act=="BUY":
                if not sig["tp1_hit"] and current_price>=s_tp1:
                    sig["tp1_hit"]=True
                    save_active()
                    bot.send_message(CHANNEL_ID, "💸 TP1 HIT ✅\n"+s_sym+" BUY\n$"+str(round(s_ent,2))+" -> $"+str(round(s_tp1,2))+"\n🔒 Move SL to BE\n@KEVINTRAILBLAZE")
                if not sig["tp2_hit"] and current_price>=s_tp2:
                    sig["tp2_hit"]=True
                    save_active()
                    bot.send_message(CHANNEL_ID, "🏆 VICTORY 🏆\n"+s_sym+" TP1 + TP2 HIT\n@KEVINTRAILBLAZE")
                if not sig["tp3_hit"] and current_price>=s_tp3:
                    bot.send_message(CHANNEL_ID, "🤑 JACKPOT 🤑\n"+s_sym+" ALL TP HIT!\n$"+str(round(s_ent,2))+" -> $"+str(round(s_tp3,2))+"\n@KEVINTRAILBLAZE")
                    active_signals.remove(sig)
                    save_active()
                if current_price<=s_sl:
                    bot.send_message(CHANNEL_ID, "🛑 SL HIT "+s_sym)
                    active_signals.remove(sig)
                    save_active()
            else:
                if not sig["tp1_hit"] and current_price<=s_tp1:
                    sig["tp1_hit"]=True
                    save_active()
                    bot.send_message(CHANNEL_ID, "💸 TP1 HIT ✅\n"+s_sym+" SELL\n$"+str(round(s_ent,2))+" -> $"+str(round(s_tp1,2))+"\n@KEVINTRAILBLAZE")
                if not sig["tp2_hit"] and current_price<=s_tp2:
                    sig["tp2_hit"]=True
                    save_active()
                    bot.send_message(CHANNEL_ID, "🏆 VICTORY 🏆\n"+s_sym+" TP1 + TP2 HIT\n@KEVINTRAILBLAZE")
                if not sig["tp3_hit"] and current_price<=s_tp3:
                    bot.send_message
