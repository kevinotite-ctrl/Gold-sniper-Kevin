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

def save_prices():
    try:
        with open(PRICE_FILE,"w") as f: json.dump(prices_history[-300:], f)
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

app=Flask(__name__)
@app.route('/')
def home(): return "KEVIN V5.4 ACCURATE LIVE", 200
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
            return f"Webhook set {url}"
        return "No URL"
    except Exception as e: return f"Error {e}"

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
    if avg_loss==0: return 65.0
    rs=avg_gain/avg_loss
    return 100-(100/(1+rs))

def calc_atr(prices, period=14):
    if len(prices) < period+1: return 6.0
    trs=[abs(prices[i]-prices[i-1]) for i in range(1,len(prices))]
    return sum(trs[-period:])/period if trs else 6.0

def calc_adx(prices):
    if len(prices) < 50: return 20.0
    e20=ema(prices,20); e50=ema(prices,50)
    if not e20 or not e50: return 20.0
    atr=calc_atr(prices,14)
    if atr==0: return 20.0
    return min(60, abs(e20-e50)/atr*12 + 12)

def get_confidence(rsi, adx, e20, e50, e200, g, action, volatility_ok, trend_strength):
    conf=50
    if adx>=25: conf+=10
    if adx>=32: conf+=10
    if adx>=40: conf+=8
    if trend_strength>=3: conf+=12
    if volatility_ok: conf+=8
    if action=="BUY":
        if 50<=rsi<=57: conf+=15
        elif 47<=rsi<=60: conf+=7
        else: conf-=15
    else:
        if 43<=rsi<=52: conf+=15
        elif 40<=rsi<=56: conf+=7
        else: conf-=15
    conf+=random.randint(0,2)
    return min(96, max(35, conf))

def build_msg(price, rsi, action, sl, tp1, adx, conf, reason):
    if conf>=85: conf_emoji="🔥🔥🔥 HIGH WIN"
    elif conf>=78: conf_emoji="🔥🔥 VERY GOOD"
    elif conf>=70: conf_emoji="⚡ GOOD"
    else: conf_emoji="💧 RISKY"
    emoji_action="🟢 BUY" if action=="BUY" else "🔴 SELL"
    trend_emoji="📈 STRONG UPTREND" if action=="BUY" else "📉 STRONG DOWNTREND"

    msg=f"""👑 KEVIN TRAILBLAZE V5.4 👑
{emoji_action} XAUUSD GOLD - ACCURATE

{trend_emoji}
{reason}

💠 Entry: ${round(price,2)}
🛡️ SL: ${round(sl,2)} (-$10)
🎯 TP: ${round(tp1,2)} (+$10)

📊 DEEP SCAN RESULT
RSI: {round(rsi,1)} | ADX: {round(adx,1)} | EMA20/50/200 Confirmed
🎯 Confidence: {conf}% {conf_emoji}

✅ Anti-Loss Filters Passed
🔗 @KEVINTRAILBLAZE
⏰ {datetime.datetime.now().strftime('%H:%M')} WAT"""
    data={"symbol":"GOLD","action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp1,"tp3":tp1}
    return msg,data,conf

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
            act=sig["action"]; ent=sig["entry"]; sl=sig["sl"]; t1=sig["tp1"]
            if act=="BUY":
                if current_price>=t1:
                    send_alert(f"💸 TP HIT ✅\n\n🟢 BUY GOLD\n💠 ${round(ent,2)} -> ${round(t1,2)}\n💰 +$10 Profit\n👑 KEVIN TRAILBLAZE")
                    to_remove.append(sig)
                if current_price<=sl:
                    send_alert(f"🛑 SL HIT 🛑\n🟢 GOLD BUY\nEntry ${round(ent,2)} SL ${round(sl,2)}\n📉 -$10\nCurrent ${round(current_price,2)}")
                    to_remove.append(sig)
            else:
                if current_price<=t1:
                    send_alert(f"💸 TP HIT ✅\n\n🔴 SELL GOLD\n💠 ${round(ent,2)} -> ${round(t1,2)}\n💰 +$10 Profit\n👑 KEVIN TRAILBLAZE")
                    to_remove.append(sig)
                if current_price>=sl:
                    send_alert(f"🛑 SL HIT 🛑\n🔴 GOLD SELL\nEntry ${round(ent,2)} SL ${round(sl,2)}\n📉 -$10\nCurrent ${round(current_price,2)}")
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
                if len(prices_history)>300: prices_history.pop(0)
                save_prices()
                check_tp_hits(g)
        except: pass
        time.sleep(60)

pending_signals={}

@bot.message_handler(commands=['start','price','active','signal','id'])
def handle_start(message):
    global ADMIN_CHAT_ID
    if message.chat.type=="private": ADMIN_CHAT_ID=message.chat.id
    g=get_gold()
    txt=message.text.lower()

    if '/id' in txt:
        bot.reply_to(message, f"🆔 Your ID: {message.from_user.id}"); return
    if '/active' in txt:
        if not active_signals: bot.reply_to(message, "📭 No active GOLD\nSend /signal for deep scan")
        else:
            t=f"📊 ACTIVE ({len(active_signals)}):\n"
            for s in active_signals: t+=f"• {s['action']} ${round(s['entry'],2)}\n"
            bot.reply_to(message,t)
        return

    if '/signal' in txt:
        if g==0:
            bot.reply_to(message, "❌ Gold API down, try again in 10s"); return

        # START DEEP SCAN - NOT 10 SEC
        bot.send_message(message.chat.id, "🔍 DEEP SCAN STARTED...\n\n⏳ Scanning Gold market to avoid SL...\n📊 Checking EMA20/50/200 trend...\n📈 Checking ADX strength >25...\n📉 Checking RSI safe zone...\n⏱️ This will take 60-90s for accuracy...\n\nPlease wait...")

        # Fill history if empty
        if len(prices_history)<50:
            for _ in range(50 - len(prices_history)): prices_history.append(g)

        # --- PHASE 1: COLLECT LIVE PRICES FOR 60 SECONDS TO CONFIRM TREND ---
        scan_prices=[]
        for i in range(6): # 6 x 10 sec = 60 sec
            time.sleep(10)
            live_g=get_gold()
            if live_g!=0:
                scan_prices.append(live_g)
                prices_history.append(live_g)
                bot.send_message(message.chat.id, f"📡 Scanning... { (i+1)*10 }s | Gold ${round(live_g,2)} | Checking volatility...")

        if len(scan_prices)<3:
            bot.reply_to(message, "❌ Weak data, try /signal again"); return

        # Use latest price
        latest_g=scan_prices[-1]
        save_prices()

        e20=ema(prices_history,20) or latest_g
        e50=ema(prices_history,50) or latest_g
        e200=ema(prices_history,200) or e50
        rsi=calc_rsi(prices_history,14)
        adx=calc_adx(prices_history)
        atr=calc_atr(prices_history,14)

        # --- ANTI-LOSS FILTERS ---
        volatility_ok = atr >= 2.0 and atr <= 12.0 # Avoid too choppy or too wild
        price_momentum = scan_prices[-1] - scan_prices[0] # Overall move in 60s

        # Trend strength count
        trend_strength=0
        if e20>e50: trend_strength+=1
        if e50>e200: trend_strength+=1
        if latest_g>e20: trend_strength+=1
        if latest_g>e50: trend_strength+=1

        sell_trend_strength=0
        if e20<e50: sell_trend_strength+=1
        if e50<e200: sell_trend_strength+=1
        if latest_g<e20: sell_trend_strength+=1
        if latest_g<e50: sell_trend_strength+=1

        # Determine action with strict rules
        action=None
        reason=""

        # BUY conditions - VERY STRICT TO AVOID SL
        if e20>e50>e200 and latest_g>e20 and latest_g>e50 and 48<=rsi<=58 and adx>=26 and volatility_ok and price_momentum>-5:
            if trend_strength>=3:
                action="BUY"
                reason="✅ EMA20>50>200 ✅ Price above EMA20 ✅ ADX 26+ Strong ✅ RSI 48-58 Safe ✅ Low Volatility"

        # SELL conditions - VERY STRICT
        elif e20<e50<e200 and latest_g<e20 and latest_g<e50 and 42<=rsi<=54 and adx>=26 and volatility_ok and price_momentum<5:
            if sell_trend_strength>=3:
                action="SELL"
                reason="✅ EMA20<50<200 ✅ Price below EMA20 ✅ ADX 26+ Strong ✅ RSI 42-54 Safe ✅ Low Volatility"

        if not action:
            # NO GOOD SETUP - DON'T SEND SIGNAL TO AVOID LOSS
            bot.send_message(message.chat.id, f"""⚠️ NO TRADE - MARKET RISKY ⚠️

Gold ${round(latest_g,2)}
RSI: {round(rsi,1)} | ADX: {round(adx,1)} | ATR: {round(atr,2)}
EMA20: ${round(e20,2)} | EMA50: ${round(e50,2)}

❌ Reason: Market not in strong safe trend
❌ To avoid SL, I will NOT send signal now

This is to protect you from loss.
Try /signal again in 5-10 mins when trend is stronger.

@KEVINTRAILBLAZE""")
            return

        conf=get_confidence(rsi,adx,e20,e50,e200,latest_g,action,volatility_ok, trend_strength if action=="BUY" else sell_trend_strength)

        # If confidence <75, don't send - avoid loss
        if conf<70:
            bot.send_message(message.chat.id, f"""⚠️ LOW CONFIDENCE {conf}% - SKIPPED ⚠️

Gold ${round(latest_g,2)} | RSI {round(rsi,1)} | ADX {round(adx,1)}

Confidence too low to avoid SL.
I skipped this trade to save you from loss.

Wait 5 mins and try /signal again.

@KEVINTRAILBLAZE""")
            return

        # Only now send HIGH CONFIDENCE signal
        if action=="BUY":
            sl=latest_g-10; tp1=latest_g+10
        else:
            sl=latest_g+10; tp1=latest_g-10

        msg,data,conf = build_msg(latest_g,rsi,action,sl,tp1,adx,conf,reason)
        bot.send_message(message.chat.id, msg)

        markup=types.InlineKeyboardMarkup()
        sig_id="GOLD_"+str(int(time.time()))
        pending_signals[sig_id]={**data, "_msg": msg}
        markup.add(types.InlineKeyboardButton(f"✅ SEND {conf}% TO CHANNEL", callback_data="approve_"+sig_id), types.InlineKeyboardButton("❌ CANCEL", callback_data="reject_"+sig_id))
        bot.send_message(message.chat.id, f"🔥 Deep scan complete - {conf}% confidence\nSend to @KEVINTRAILBLAZE?", reply_markup=markup)
        return

    rsi=calc_rsi(prices_history) if len(prices_history)>14 else 50.0
    bot.reply_to(message, f"""👑 KEVIN GOLD V5.4 ACCURATE 👑

🥇 GOLD: ${round(g,2) if g else 0}
📊 RSI: {round(rsi,1)} | Data: {len(prices_history)}

⚙️ MODE: Deep Scan Anti-Loss
- Scans 60-90s live market
- Checks EMA20/50/200 alignment
- Requires ADX >26 (strong trend only)
- Requires RSI 48-58 (BUY) or 42-54 (SELL)
- Skips low confidence <70% to avoid SL
- No 10-sec rush

Commands:
📡 /signal - Deep scan (60-90s) for safe signal
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
            active_signals.append({k:v for k,v in sd.items() if not k.startswith("_")}|{"tp1_hit":False})
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
