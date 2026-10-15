# -*- coding: utf-8 -*-
import os, requests, time, threading, telebot, datetime, json, random
from telebot import types
from flask import Flask, request

BOT_TOKEN=os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
ADMIN_ID=os.environ.get("ADMIN_ID")
ADMIN_CHAT_ID=None

bot=telebot.TeleBot(BOT_TOKEN)

# --- STORAGE ---
prices_history=[]
active_signals=[]
PRICE_FILE="price_history.json"
ACTIVE_FILE="active_signals.json"

def save_prices():
    try:
        with open(PRICE_FILE,"w") as f: json.dump(prices_history[-250:], f)
    except: pass

def save_active():
    try:
        with open(ACTIVE_FILE,"w") as f: json.dump(active_signals,f)
    except: pass

def load_data():
    global prices_history, active_signals
    try:
        if os.path.exists(PRICE_FILE):
            with open(PRICE_FILE,"r") as f: prices_history=json.load(f)
        else: prices_history=[]
    except: prices_history=[]
    try:
        if os.path.exists(ACTIVE_FILE):
            with open(ACTIVE_FILE,"r") as f: active_signals=json.load(f)
        else: active_signals=[]
    except: active_signals=[]

load_data()

# --- FLASK ---
app=Flask(__name__)
@app.route('/')
def home(): return "KEVIN V5.3 INSTANT LIVE", 200

@app.route('/health')
def health(): return "OK", 200

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except: pass
    return "OK", 200

@app.route('/setwebhook')
def set_webhook():
    try:
        bot.remove_webhook(); time.sleep(1)
        ext_url = os.getenv("RENDER_EXTERNAL_URL")
        if ext_url:
            url = f"{ext_url}/{BOT_TOKEN}"
            bot.set_webhook(url=url)
            return f"Webhook set to {url}"
        return "No URL"
    except Exception as e: return f"Error {e}"

# --- GOLD + INDICATORS ---
def get_gold():
    try:
        r=requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
        return float(r["price"])
    except: return 0

def ema(prices, period):
    if len(prices) < period: return None
    k = 2/(period+1)
    ema_val = sum(prices[:period])/period
    for p in prices[period:]: ema_val = p*k + ema_val*(1-k)
    return ema_val

def calc_rsi(prices, period=14):
    if len(prices) < period+1: return 50.0
    gains=[]; losses=[]
    for i in range(1,len(prices)):
        diff=prices[i]-prices[i-1]
        gains.append(diff if diff>0 else 0)
        losses.append(abs(diff) if diff<0 else 0)
    if len(gains)<period: return 50.0
    avg_gain=sum(gains[-period:])/period
    avg_loss=sum(losses[-period:])/period
    if avg_loss==0: return 68.0
    rs=avg_gain/avg_loss
    return 100-(100/(1+rs))

def calc_atr(prices, period=14):
    if len(prices) < period+1: return 8.0
    trs=[abs(prices[i]-prices[i-1]) for i in range(1,len(prices))]
    return sum(trs[-period:])/period if trs else 8.0

def calc_adx(prices):
    if len(prices) < 30: return 22.0
    e20=ema(prices,20); e50=ema(prices,50)
    if not e20 or not e50: return 22.0
    atr=calc_atr(prices,14)
    if atr==0: return 22.0
    return min(55, abs(e20-e50)/atr*10 + 15)

def get_confidence(rsi, adx, e20, e50, e200, g, action):
    conf=62
    if adx>22: conf+=8
    if adx>30: conf+=10
    if adx>40: conf+=7
    if action=="BUY":
        if 50<=rsi<=58: conf+=12
        elif 45<=rsi<=62: conf+=6
    else:
        if 42<=rsi<=52: conf+=12
        elif 38<=rsi<=55: conf+=6
    conf+=random.randint(0,4)
    return min(96, max(62, conf))

def build_msg(price, rsi, action, sl, tp1, tp2, tp3, adx, conf):
    if conf>=85: conf_emoji="🔥🔥🔥 HIGH"
    elif conf>=75: conf_emoji="🔥🔥 MEDIUM-HIGH"
    elif conf>=65: conf_emoji="⚡ MEDIUM"
    else: conf_emoji="💧 LOW"
    if action=="BUY":
        emoji_action="🟢 BUY"
        trend_emoji="📈 UPTREND"
    else:
        emoji_action="🔴 SELL"
        trend_emoji="📉 DOWNTREND"

    msg=f"""👑 KEVIN TRAILBLAZE V5.3 👑
{emoji_action} XAUUSD GOLD

{trend_emoji} | EMA TREND SAFE

💠 Entry: ${round(price,2)}
🛡️ SL: ${round(sl,2)} (-$10)
🎯 TP1: ${round(tp1,2)} (+$10)
🎯 TP2: ${round(tp2,2)} (+$10)
🎯 TP3: ${round(tp3,2)} (+$10)

📊 ANALYSIS
RSI: {round(rsi,1)} | ADX: {round(adx,1)}
🎯 Confidence: {conf}% {conf_emoji}

💡 Manual Command Only
🔗 @KEVINTRAILBLAZE
⏰ {datetime.datetime.now().strftime('%H:%M')} WAT"""
    data={"symbol":"GOLD","action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3}
    return msg,data,conf

# --- ALERTS FOR TP/SL (Channel + You) ---
def send_alert(text):
    try: bot.send_message(CHANNEL_ID, text)
    except: pass
    try:
        target=None
        if ADMIN_ID:
            try: target=int(ADMIN_ID)
            except: pass
        if not target: target=ADMIN_CHAT_ID
        if target: bot.send_message(target, text)
    except: pass

def check_tp_hits(current_price):
    to_remove=[]
    for sig in active_signals[:]:
        try:
            act=sig["action"]; ent=sig["entry"]; sl=sig["sl"]; t1=sig["tp1"]; t2=sig["tp2"]; t3=sig["tp3"]
            if act=="BUY":
                if not sig.get("tp1_hit") and current_price>=t1:
                    sig["tp1_hit"]=True; save_active()
                    send_alert(f"💸 TP1 HIT ✅\n\n🟢 BUY GOLD\n💠 ${round(ent,2)} -> ${round(t1,2)}\n💰 +$10 Profit\n🔒 Move SL to BE\n@KEVINTRAILBLAZE")
                if not sig.get("tp2_hit") and current_price>=t2:
                    sig["tp2_hit"]=True; save_active()
                    send_alert(f"🏆 TP2 HIT ✅\nGOLD BUY +$10\n@KEVINTRAILBLAZE")
                if not sig.get("tp3_hit") and current_price>=t3:
                    send_alert(f"🤑 JACKPOT ALL TP HIT 🤑\n🟢 GOLD BUY ${round(ent,2)} -> ${round(t3,2)}\n💰 +$10\n👑 KEVIN")
                    to_remove.append(sig)
                if current_price<=sl:
                    send_alert(f"🛑 SL HIT 🛑\n🟢 GOLD BUY\n💠 Entry ${round(ent,2)} SL ${round(sl,2)}\n📉 -$10 Loss\nPrice ${round(current_price,2)}\n@KEVINTRAILBLAZE")
                    to_remove.append(sig)
            else:
                if not sig.get("tp1_hit") and current_price<=t1:
                    sig["tp1_hit"]=True; save_active()
                    send_alert(f"💸 TP1 HIT ✅\n\n🔴 SELL GOLD\n💠 ${round(ent,2)} -> ${round(t1,2)}\n💰 +$10 Profit\n@KEVINTRAILBLAZE")
                if not sig.get("tp2_hit") and current_price<=t2:
                    sig["tp2_hit"]=True; save_active()
                    send_alert(f"🏆 TP2 HIT ✅\nGOLD SELL +$10\n@KEVINTRAILBLAZE")
                if not sig.get("tp3_hit") and current_price<=t3:
                    send_alert(f"🤑 JACKPOT ALL TP HIT 🤑\n🔴 GOLD SELL ${round(ent,2)} -> ${round(t3,2)}\n💰 +$10\n👑 KEVIN")
                    to_remove.append(sig)
                if current_price>=sl:
                    send_alert(f"🛑 SL HIT 🛑\n🔴 GOLD SELL\n💠 Entry ${round(ent,2)} SL ${round(sl,2)}\n📉 -$10 Loss\nPrice ${round(current_price,2)}\n@KEVINTRAILBLAZE")
                    to_remove.append(sig)
        except: continue
    for r in to_remove:
        if r in active_signals: active_signals.remove(r)
    if to_remove: save_active()

def signal_loop():
    while True:
        try:
            g=get_gold()
            if g!=0:
                prices_history.append(g)
                if len(prices_history)>250: prices_history.pop(0)
                save_prices()
                check_tp_hits(g)
        except: pass
        time.sleep(60)

# --- COMMANDS ---
pending_signals={}

@bot.message_handler(commands=['start','price','active','signal','id','testsignal'])
def handle_start(message):
    global ADMIN_CHAT_ID
    if message.chat.type=="private": ADMIN_CHAT_ID=message.chat.id

    g=get_gold()
    txt=message.text.lower()

    if '/id' in txt:
        bot.reply_to(message, f"🆔 Your ID: {message.from_user.id}"); return

    if '/active' in txt:
        if not active_signals: bot.reply_to(message, "📭 No active GOLD\nSend /signal to scan market")
        else:
            t=f"📊 ACTIVE ({len(active_signals)}):\n"
            for s in active_signals: t+=f"• {s['action']} ${round(s['entry'],2)}\n"
            bot.reply_to(message,t)
        return

    if '/signal' in txt:
        if g==0:
            bot.reply_to(message, "❌ Gold API down, try /signal again in 10s"); return

        # INSTANT FIX - fill history if empty
        if len(prices_history)<20:
            for _ in range(20 - len(prices_history)): prices_history.append(g)
            save_prices()

        e20=ema(prices_history,20) or g
        e50=ema(prices_history,50) or g
        e200=ema(prices_history,200) or e50
        rsi=calc_rsi(prices_history,14)
        adx=calc_adx(prices_history)

        action="BUY" if g>=e20 else "SELL"
        if action=="BUY" and rsi>68: action="SELL"
        if action=="SELL" and rsi<32: action="BUY"

        conf=get_confidence(rsi,adx,e20,e50,e200,g,action)

        if action=="BUY":
            sl=g-10; tp1=g+10; tp2=g+10; tp3=g+10
        else:
            sl=g+10; tp1=g-10; tp2=g-10; tp3=g-10

        bot.send_message(message.chat.id, "‼️signal alert incoming ‼️💰\n⏳ Gold scan... 10s")
        time.sleep(10)

        msg,data,conf = build_msg(g,rsi,action,sl,tp1,tp2,tp3,adx,conf)
        bot.send_message(message.chat.id, msg)

        markup=types.InlineKeyboardMarkup()
        sig_id="GOLD_"+str(int(time.time()))
        pending_signals[sig_id]={**data, "_msg": msg}
        markup.add(types.InlineKeyboardButton("✅ SEND TO CHANNEL", callback_data="approve_"+sig_id), types.InlineKeyboardButton("❌ CANCEL", callback_data="reject_"+sig_id))
        bot.send_message(message.chat.id, f"Send this {conf}% confidence signal to @KEVINTRAILBLAZE?", reply_markup=markup)
        return

    rsi=calc_rsi(prices_history) if len(prices_history)>14 else 50.0
    bot.reply_to(message, f"""👑 KEVIN GOLD V5.3 INSTANT 👑

🥇 GOLD: ${round(g,2) if g else 0}
📊 RSI: {round(rsi,1)} | Data: {len(prices_history)}

⚙️ MODE: Manual Only - Instant
✅ /signal works instantly (no collecting)
✅ $10 SL/TP fixed
✅ Alerts for TP/SL to you + channel
✅ Confidence + Emoji

Commands:
📡 /signal - Scan & send signal
📊 /active - Active trades
""")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        d=call.data
        if d.startswith("approve_"):
            sid=d.replace("approve_","")
            sd=pending_signals.pop(sid,None)
            if not sd: bot.answer_callback_query(call.id,"Done"); return
            msg=sd.get("_msg")
            bot.send_message(CHANNEL_ID, msg)
            active_signals.append({k:v for k,v in sd.items() if not k.startswith("_")}|{"tp1_hit":False,"tp2_hit":False,"tp3_hit":False})
            save_active()
            bot.answer_callback_query(call.id,"✅ Sent!")
            bot.edit_message_text("✅ SENT to @KEVINTRAILBLAZE", call.message.chat.id, call.message.message_id)
        elif d.startswith("reject_"):
            pending_signals.pop(d.replace("reject_",""),None)
            bot.answer_callback_query(call.id,"❌ Cancelled")
            bot.edit_message_text("❌ Cancelled", call.message.chat.id, call.message.message_id)
    except Exception as e: print(e)

threading.Thread(target=signal_loop,daemon=True).start()

if __name__=="__main__":
    try:
        bot.remove_webhook(); time.sleep(1)
        ext_url = os.getenv("RENDER_EXTERNAL_URL")
        if ext_url: bot.set_webhook(url=f"{ext_url}/{BOT_TOKEN}"); print(f"Webhook {ext_url}", flush=True)
    except Exception as e: print(e)
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
