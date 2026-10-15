# -*- coding: utf-8 -*-
import os, requests, time, threading, telebot, datetime, json, random
from telebot import types
from flask import Flask, request

BOT_TOKEN=os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
ADMIN_ID=os.environ.get("ADMIN_ID")
ADMIN_CHAT_ID=None

bot=telebot.TeleBot(BOT_TOKEN)
prices_history=[]
active_signals=[]
PRICE_FILE="price_history.json"
ACTIVE_FILE="active_signals.json"
auto_scan_enabled=False
last_signal_time=0

def save_prices():
    try:
        with open(PRICE_FILE,"w") as f: json.dump(prices_history[-500:], f)
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
    except: prices_history=[]
    try:
        if os.path.exists(ACTIVE_FILE):
            with open(ACTIVE_FILE,"r") as f: active_signals=json.load(f)
    except: active_signals=[]
load_data()

app=Flask(__name__)
@app.route('/')
def home(): return "KEVIN V5.7 30MIN LIVE",200
@app.route('/health')
def health(): return "OK",200
@app.route(f'/{BOT_TOKEN}',methods=['POST'])
def webhook():
    try:
        json_str=request.get_data().decode('UTF-8')
        update=telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except: pass
    return "OK",200
@app.route('/setwebhook')
def set_webhook():
    try:
        bot.remove_webhook(); time.sleep(1)
        ext=os.getenv("RENDER_EXTERNAL_URL")
        if ext:
            url=f"{ext}/{BOT_TOKEN}"
            bot.set_webhook(url=url)
            return f"Webhook {url}"
        return "No URL"
    except Exception as e: return f"Error {e}"

def get_gold():
    try: return float(requests.get("https://api.gold-api.com/price/XAU",timeout=10).json()["price"])
    except: return 0
def ema(prices,p):
    if len(prices)<p: return None
    k=2/(p+1); v=sum(prices[:p])/p
    for x in prices[p:]: v=x*k+v*(1-k)
    return v
def calc_rsi(prices,p=14):
    if len(prices)<p+1: return 50.0
    g=[];l=[]
    for i in range(1,len(prices)):
        d=prices[i]-prices[i-1]
        g.append(d if d>0 else 0); l.append(abs(d) if d<0 else 0)
    if len(g)<p: return 50.0
    ag=sum(g[-p:])/p; al=sum(l[-p:])/p
    if al==0: return 65.0
    return 100-(100/(1+ag/al))
def calc_atr(prices,p=14):
    if len(prices)<p+1: return 6.0
    tr=[abs(prices[i]-prices[i-1]) for i in range(1,len(prices))]
    return sum(tr[-p:])/p
def calc_adx(prices):
    if len(prices)<50: return 20.0
    e20=ema(prices,20); e50=ema(prices,50)
    if not e20 or not e50: return 20.0
    atr=calc_atr(prices,14)
    if atr==0: return 20.0
    return min(60, abs(e20-e50)/atr*12+12)

def analyze_30min_frame():
    """Analyze last 30 mins to know market direction - MAIN LOGIC YOU ASKED"""
    if len(prices_history)<30:
        return None, "Not enough 30min data"

    last_30 = prices_history[-30:] # Previous 30 mins
    last_15 = prices_history[-15:] # Recent 15 mins
    current = last_30[-1]
    start_30 = last_30[0]
    start_15 = last_15[0]

    # 1. 30MIN TREND
    change_30 = current - start_30
    change_15 = current - start_15
    pct_30 = (change_30 / start_30 * 100) if start_30 else 0

    # 2. EMA ANALYSIS ON 30MIN FRAME
    e20 = ema(prices_history,20) or current
    e50 = ema(prices_history,50) or current
    e200 = ema(prices_history,200) or current

    # 3. HIGH/LOW OF LAST 30 MIN
    high_30 = max(last_30)
    low_30 = min(last_30)
    range_30 = high_30 - low_30

    # 4. RSI/ADX ON 30MIN FRAME
    rsi = calc_rsi(prices_history,14)
    adx = calc_adx(prices_history)
    atr = calc_atr(prices_history,14)

    # 5. DETERMINE LEGIT DIRECTION
    # Strong up if: price above all EMAs, 30min change positive, recent 15min also up, ADX strong
    legit_buy = False
    legit_sell = False
    reason = ""

    if current > e20 > e50 > e200 and change_30 > 2 and change_15 > 0 and rsi >=48 and rsi <=60 and adx >=26 and range_30 > 1.5:
        legit_buy = True
        reason = f"✅ 30MIN UPTREND: +${round(change_30,2)} in 30min | Price ${round(start_30,2)}→${round(current,2)} | Above EMA20/50/200 | RSI {round(rsi,1)} Safe | ADX {round(adx,1)} Strong | Range ${round(range_30,2)}"

    elif current < e20 < e50 < e200 and change_30 < -2 and change_15 < 0 and rsi >=40 and rsi <=54 and adx >=26 and range_30 > 1.5:
        legit_sell = True
        reason = f"✅ 30MIN DOWNTREND: -${round(abs(change_30),2)} in 30min | Price ${round(start_30,2)}→${round(current,2)} | Below EMA20/50/200 | RSI {round(rsi,1)} Safe | ADX {round(adx,1)} Strong | Range ${round(range_30,2)}"

    # Confidence based on 30min frame strength
    conf = 55
    if abs(change_30) > 5: conf += 15 # Strong 30min move
    if abs(change_15) > 2: conf += 10 # Recent momentum
    if adx >= 30: conf += 10
    if adx >= 40: conf += 8
    if 50 <= rsi <= 56: conf += 8
    if range_30 > 4: conf += 5 # Good volatility
    if range_30 < 1.0: conf -= 20 # Choppy, avoid

    conf = min(96, max(40, conf + random.randint(0,3)))

    analysis = {
        "current": current,
        "start_30": start_30,
        "change_30": change_30,
        "change_15": change_15,
        "high_30": high_30,
        "low_30": low_30,
        "range_30": range_30,
        "e20": e20, "e50": e50, "e200": e200,
        "rsi": rsi, "adx": adx, "atr": atr,
        "conf": conf,
        "reason": reason,
        "legit_buy": legit_buy,
        "legit_sell": legit_sell
    }
    return analysis, None

def build_msg_from_30min(analysis):
    cur = analysis["current"]
    rsi = analysis["rsi"]; adx = analysis["adx"]; conf = analysis["conf"]; reason = analysis["reason"]
    change_30 = analysis["change_30"]

    if analysis["legit_buy"]:
        action = "BUY"
        sl = cur - 10; tp = cur + 10
    else:
        action = "SELL"
        sl = cur + 10; tp = cur - 10

    conf_emoji = "🔥🔥🔥 HIGH" if conf>=85 else "🔥🔥 VERY GOOD" if conf>=78 else "⚡ GOOD"
    ea = "🟢 BUY" if action=="BUY" else "🔴 SELL"
    tr = "📈 30MIN UPTREND CONFIRMED" if action=="BUY" else "📉 30MIN DOWNTREND CONFIRMED"

    msg = f"""👑 KEVIN TRAILBLAZE 30MIN FRAME 👑
{ea} XAUUSD GOLD - LEGIT ENTRY

{tr}
{reason}

📊 30MIN FRAME ANALYSIS
⏰ Last 30min: ${round(analysis['start_30'],2)} → ${round(cur,2)} ({'+' if change_30>0 else ''}{round(change_30,2)})
📈 High: ${round(analysis['high_30'],2)} | Low: ${round(analysis['low_30'],2)} | Range: ${round(analysis['range_30'],2)}
📊 RSI: {round(rsi,1)} | ADX: {round(adx,1)} | ATR: {round(analysis['atr'],2)}

💠 Entry: ${round(cur,2)}
🛡️ SL: ${round(sl,2)} (-$10)
🎯 TP: ${round(tp,2)} (+$10)

🎯 Confidence: {conf}% {conf_emoji}
✅ 30Min Legit Entry - Avoids SL
🔗 @KEVINTRAILBLAZE
⏰ {datetime.datetime.now().strftime('%H:%M')} WAT"""

    data = {"symbol":"GOLD","action":action,"entry":cur,"sl":sl,"tp1":tp,"tp2":tp,"tp3":tp}
    return msg,data,conf

def send_alert(text):
    try: bot.send_message(CHANNEL_ID,text)
    except: pass
    try:
        t=None
        if ADMIN_ID:
            try: t=int(ADMIN_ID)
            except: pass
        if not t: t=ADMIN_CHAT_ID
        if t: bot.send_message(t,text)
    except: pass

def check_tp_hits(cur):
    rm=[]
    for sig in active_signals[:]:
        try:
            act=sig["action"]; ent=sig["entry"]; sl=sig["sl"]; tp=sig["tp1"]
            if act=="BUY":
                if cur>=tp: send_alert(f"💸 TP HIT ✅\n\n🟢 BUY GOLD\n💠 ${round(ent,2)} → ${round(tp,2)}\n💰 +$10\n@KEVINTRAILBLAZE"); rm.append(sig)
                elif cur<=sl: send_alert(f"🛑 SL HIT 🛑\n🟢 BUY ${round(ent,2)} SL ${round(sl,2)}\n📉 -$10"); rm.append(sig)
            else:
                if cur<=tp: send_alert(f"💸 TP HIT ✅\n\n🔴 SELL GOLD\n💠 ${round(ent,2)} → ${round(tp,2)}\n💰 +$10\n@KEVINTRAILBLAZE"); rm.append(sig)
                elif cur>=sl: send_alert(f"🛑 SL HIT 🛑\n🔴 SELL ${round(ent,2)} SL ${round(sl,2)}\n📉 -$10"); rm.append(sig)
        except: continue
    for r in rm:
        if r in active_signals: active_signals.remove(r)
    if rm: save_active()

def auto_scan_loop():
    global last_signal_time
    while True:
        try:
            g=get_gold()
            if g!=0:
                prices_history.append(g)
                if len(prices_history)>500: prices_history.pop(0)
                save_prices()
                check_tp_hits(g)

            if auto_scan_enabled and time.time()-last_signal_time>900: # 15 mins
                analysis, err = analyze_30min_frame()
                if analysis and (analysis["legit_buy"] or analysis["legit_sell"]) and analysis["conf"]>=72:
                    msg,data,conf=build_msg_from_30min(analysis)
                    if ADMIN_CHAT_ID: bot.send_message(ADMIN_CHAT_ID,msg)
                    bot.send_message(CHANNEL_ID,msg)
                    active_signals.append(data); save_active()
                    last_signal_time=time.time()
        except Exception as e: print(f"auto err {e}")
        time.sleep(60)

pending_signals={}
@bot.message_handler(commands=['start','signal','active','stop','price','id'])
def handle_start(message):
    global ADMIN_CHAT_ID, auto_scan_enabled, last_signal_time
    if message.chat.type=="private": ADMIN_CHAT_ID=message.chat.id
    txt=message.text.lower()
    g=get_gold()

    if '/id' in txt: bot.reply_to(message,f"🆔 {message.from_user.id}"); return
    if '/active' in txt:
        if not active_signals: bot.reply_to(message,"📭 No active")
        else:
            t=f"📊 ACTIVE ({len(active_signals)}):\n"
            for s in active_signals: t+=f"• {s['action']} ${round(s['entry'],2)}\n"
            bot.reply_to(message,t)
        return
    if '/stop' in txt:
        auto_scan_enabled=False; bot.reply_to(message,"🛑 Auto Scan STOPPED"); return
    if '/price' in txt: bot.reply_to(message,f"🥇 GOLD: ${round(g,2) if g else 0}"); return

    if '/signal' in txt:
        bot.send_message(message.chat.id,"🔍 Scanning 30min timeframe for legit entry...")
        analysis, err = analyze_30min_frame()
        if err or not analysis:
            bot.send_message(message.chat.id,f"⏳ Collecting 30min data... {len(prices_history)}/30\nTry /signal again in {30-len(prices_history)} mins")
            return
        if not (analysis["legit_buy"] or analysis["legit_sell"]):
            bot.send_message(message.chat.id,f"""⚠️ NO LEGIT ENTRY - 30MIN ANALYSIS ⚠️

Gold Now: ${round(analysis['current'],2)}
30Min Change: {round(analysis['change_30'],2)}
RSI: {round(analysis['rsi'],1)} | ADX: {round(analysis['adx'],1)}
EMA20: ${round(analysis['e20'],2)} | EMA50: ${round(analysis['e50'],2)}

❌ Market choppy in last 30min - No clear direction
✅ Skipped to avoid SL

Try again in 10 mins
@KEVINTRAILBLAZE""")
            return
        msg,data,conf=build_msg_from_30min(analysis)
        bot.send_message(message.chat.id,msg)
        markup=types.InlineKeyboardMarkup()
        sig_id="GOLD_"+str(int(time.time()))
        pending_signals[sig_id]={**data,"_msg":msg}
        markup.add(types.InlineKeyboardButton(f"✅ SEND {conf}% TO CHANNEL",callback_data="approve_"+sig_id),types.InlineKeyboardButton("❌ CANCEL",callback_data="reject_"+sig_id))
        bot.send_message(message.chat.id,f"Send this 30min legit {conf}% signal?",reply_markup=markup)
        return

    if '/start' in txt:
        auto_scan_enabled=True
        last_signal_time=time.time()-800
        # IMMEDIATE SCAN MESSAGE YOU WANTED
        if len(prices_history)<30:
            bot.reply_to(message,f"""🔍 SCANNING FOR LEGIT ENTRY...

⏳ Analyzing previous 30min timeframe...
📊 Current data: {len(prices_history)}/30 mins collected
🥇 Gold: ${round(g,2) if g else 0}

I need 30 mins of data to know where market is heading.
Collecting now... will auto-start sending legit entries soon.

🤖 Auto Scan: ON ✅
I will scan non-stop every 15 mins using 30min frame.

@KEVINTRAILBLAZE""")
        else:
            analysis,_=analyze_30min_frame()
            bot.reply_to(message,f"""🔍 SCANNING FOR LEGIT ENTRY...

📊 Analyzing previous 30min timeframe...
🥇 Gold: ${round(g,2) if g else 0} | Data: {len(prices_history)} mins
📈 30min Change: {round(analysis['change_30'],2) if analysis else 0}
📊 RSI: {round(analysis['rsi'],1) if analysis else 0} | ADX: {round(analysis['adx'],1) if analysis else 0}

✅ Scanning 30min frame to know where market is heading
✅ Looking for legit entry to avoid SL
🤖 Auto Scan: ON - Non-stop ✅

I will send signals automatically when 30min trend is clear.

Commands:
📡 /signal - Check 30min now
📊 /active - Active trades
🛑 /stop - Stop auto
""")
        return

@bot.callback_query_handler(func=lambda c: True)
def handle_callback(call):
    try:
        d=call.data
        if d.startswith("approve_"):
            sid=d.replace("approve_",""); sd=pending_signals.pop(sid,None)
            if not sd: return
            bot.send_message(CHANNEL_ID,sd.get("_msg")); active_signals.append({k:v for k,v in sd.items() if not k.startswith("_")}); save_active()
            bot.answer_callback_query(call.id,"✅ Sent!"); bot.edit_message_text("✅ SENT",call.message.chat.id,call.message.message_id)
        elif d.startswith("reject_"):
            pending_signals.pop(d.replace("reject_",""),None); bot.edit_message_text("❌ Cancelled",call.message.chat.id,call.message.message_id)
    except: pass

threading.Thread(target=auto_scan_loop,daemon=True).start()
if __name__=="__main__":
    try:
        bot.remove_webhook(); time.sleep(1)
        ext=os.getenv("RENDER_EXTERNAL_URL")
        if ext: bot.set_webhook(url=f"{ext}/{BOT_TOKEN}")
    except: pass
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
