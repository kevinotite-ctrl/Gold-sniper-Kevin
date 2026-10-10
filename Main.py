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
prices_history=[]
btc_history=[]
active_signals=[]
last_signal_time={}
pending_signals={}

app=Flask(__name__)
@app.route('/')
def home(): return "KEVIN TRAILBLAZE LUXURY BOSS LIVE"

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
        except: return 82714.0
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

def build_luxury_msg(symbol, price, rsi, action):
    now_str = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    if symbol=="GOLD":
        sl = price-10 if action=="BUY" else price+10
        tp1 = price+20 if action=="BUY" else price-20
        tp2 = price+40 if action=="BUY" else price-40
        tp3 = price+60 if action=="BUY" else price-60
        dir_emoji = "🟢📈" if action=="BUY" else "🔴📉"
        tag = "GOLDEN BUY" if action=="BUY" else "GOLDEN SELL"
        cond = "OVERSOLD 🔥" if action=="BUY" else "OVERBOUGHT 🔥"
        msg = f"""╔══════════════════════════════╗
║ 👑 KEVIN TRAILBLAZE 👑 ║
║ ✨ LUXURY SNIPER ✨ ║
╚══════════════════════════════╝

{dir_emoji} {tag} {dir_emoji}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💠 ASSET : XAUUSD (GOLD)
💠 ACTION : {action} NOW
💠 RSI(7) : {rsi:.2f} → {cond}
💠 TIME : {now_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 ENTRY ZONE
┗━━━ ${price:.2f}

🛡️ STOP LOSS
┗━━━ ${sl:.2f} (-$10)

🎯 TAKE PROFITS
┣━━ 🥇 TP1 : ${tp1:.2f} (+$20) RR 1:2
┣━━ 🥈 TP2 : ${tp2:.2f} (+$40) RR 1:4
┗━━ 🏆 TP3 : ${tp3:.2f} (+$60) RR 1:6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 KEVIN'S MASTER PLAN
 1️⃣ Enter @ ${price:.2f}
 2️⃣ TP1 HIT → Move SL to BreakEven 🔒
 3️⃣ TP2 HIT → VICTORY 🏆 50% Close
 4️⃣ TP3 → JACKPOT 🤑 Full Bag!

🔗 Official : @KEVINTRAILBLAZE
#XAUUSD #GOLD #KEVINTRAILBLAZE"""
        data = {"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3}
        return msg, data
    else:
        sl = price*0.99 if action=="BUY" else price*1.01
        tp1 = price*1.02 if action=="BUY" else price*0.98
        tp2 = price*1.04 if action=="BUY" else price*0.96
        tp3 = price*1.06 if action=="BUY" else price*0.94
        dir_emoji = "🚀🟢" if action=="BUY" else "💥🔴"
        tag = "BITCOIN PUMP" if action=="BUY" else "BITCOIN DUMP"
        msg = f"""╔══════════════════════════════╗
║ 👑 KEVIN TRAILBLAZE 👑 ║
║ ₿ LUXURY CRYPTO ₿ ║
╚══════════════════════════════╝

{dir_emoji} {tag} {dir_emoji}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💠 ASSET : BTC/USD
💠 ACTION : {action} NOW
💠 RSI(7) : {rsi:.2f}
💠 TIME : {now_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 ENTRY
┗━━━ ${price:,.2f}

🛡️ STOP LOSS
┗━━━ ${sl:,.2f} (-1%)

🎯 TAKE PROFITS
┣━━ 🥇 TP1 : ${tp1:,.2f} (+2%)
┣━━ 🥈 TP2 : ${tp2:,.2f} (+4%)
┗━━ 🏆 TP3 : ${tp3:,.2f} (+6%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📜 PLAN: TP1→BE 🔒 | TP2=VICTORY 🏆 | TP3=JACKPOT 🤑

🔗 @KEVINTRAILBLAZE
#BTC #KEVINTRAILBLAZE"""
        data = {"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3}
        return msg, data

def request_approval(symbol, price, rsi, action):
    global ADMIN_CHAT_ID
    target = None
    if ADMIN_ID:
        try: target = int(ADMIN_ID)
        except: pass
    if not target: target = ADMIN_CHAT_ID
    luxury_msg, data = build_luxury_msg(symbol, price, rsi, action)
    if not target:
        try:
            bot.send_message(CHANNEL_ID, luxury_msg)
            active_signals.append({**data,"tp1_hit":False,"tp2_hit":False,"tp3_hit":False})
        except Exception as e: print(e)
        return
    sig_id = f"{symbol}_{int(time.time())}"
    pending_signals[sig_id]=data
    # store full luxury msg also for resend
    pending_signals[sig_id]["_luxury_msg"] = luxury_msg
    pending_signals[sig_id]["_rsi"] = rsi
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ SEND TO CHANNEL", callback_data=f"approve_{sig_id}"),
        types.InlineKeyboardButton("❌ REJECT", callback_data=f"reject_{sig_id}")
    )
    preview = f"🔔 NEW SIGNAL - BOSS APPROVAL NEEDED 👑\n\n{luxury_msg}\n\n👆 Boss, send this to {CHANNEL_ID}?"
    try: bot.send_message(target, preview, reply_markup=markup)
    except Exception as e: print(e)

def check_tp_hits(current_price, symbol):
    for sig in active_signals[:]:
        if sig["symbol"]!=symbol: continue
        try:
            s_sym=sig["symbol"]; s_act=sig["action"]; s_ent=sig["entry"]
            s_tp1=sig["tp1"]; s_tp2=sig["tp2"]; s_tp3=sig["tp3"]; s_sl=sig["sl"]
            if s_act=="BUY":
                if not sig["tp1_hit"] and current_price>=s_tp1:
                    sig["tp1_hit"]=True
                    bot.send_message(CHANNEL_ID,f"""╔════════════╗
║ 💸 TP1 HIT 💸 ║
╚════════════╝
👑 {BRAND}
{s_sym} BUY ✅
Entry ${s_ent:.2f} → TP1 ${s_tp1:.2f}
🔒 Move SL to BE NOW!
@KEVINTRAILBLAZE""")
                if not sig["tp2_hit"] and current_price>=s_tp2:
                    sig["tp2_hit"]=True
                    bot.send_message(CHANNEL_ID,f"""╔══════════════════════╗
║ 🏆 VICTORY! 🏆 ║
╚══════════════════════╝
👑 {BRAND} CALLED IT!
{s_sym} {s_act}
✅ TP1 ✅ TP2 SECURED
💰 MASSIVE PROFIT LOCKED!
Running to TP3 JACKPOT 🤑
@KEVINTRAILBLAZE""")
                if not sig["tp3_hit"] and current_price>=s_tp3:
                    bot.send_message(CHANNEL_ID,f"""╔══════════════════════════════╗
║ 🤑 JACKPOT! FULL TP 🤑 ║
╚══════════════════════════════╝
👑 {BRAND} DID IT AGAIN!
{s_sym} {s_act}
✅ TP1 ✅ TP2 ✅ TP3 BOOM!
Entry ${s_ent:.2f} → ${s_tp3:.2f}
MAX PROFIT 🤑🤑🤑
@KEVINTRAILBLAZE""")
                    active_signals.remove(sig)
                if current_price<=s_sl:
                    bot.send_message(CHANNEL_ID,f"🛑 SL HIT {s_sym} BUY"); active_signals.remove(sig)
            else:
                if not sig["tp1_hit"] and current_price<=s_tp1:
                    sig["tp1_hit"]=True
                    bot.send_message(CHANNEL_ID,f"💸 TP1 HIT {s_sym} SELL {s_ent:.2f} → {s_tp1:.2f} MOVE SL TO BE! @KEVINTRAILBLAZE")
                if not sig["tp2_hit"] and current_price<=s_tp2:
                    sig["tp2_hit"]=True
                    bot.send_message(CHANNEL_ID,f"🏆 VICTORY! {s_sym} SELL TP1+TP2 HIT! @KEVINTRAILBLAZE")
                if not sig["tp3_hit"] and current_price<=s_tp3:
                    bot.send_message(CHANNEL_ID,f"🤑 JACKPOT! {s_sym} SELL ALL TP HIT! @KEVINTRAILBLAZE")
                    active_signals.remove(sig)
                if current_price>=s_sl:
                    bot.send_message(CHANNEL_ID,f"🛑 SL HIT {s_sym} SELL"); active_signals.remove(sig)
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
                    if now-last_signal_time.get("BTC",0)>1800:
                        request_approval("BTC",b,r2,"BUY" if r2<30 else "SELL")
                        last_signal_time["BTC"]=now
        except Exception as e: print(e)
        time.sleep(60)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        data = call.data
        if data.startswith("approve_"):
            sig_id = data.replace("approve_","")
            sig_data = pending_signals.pop(sig_id, None)
            if not sig_data:
                bot.answer_callback_query(call.id, "Already handled"); return
            luxury_msg = sig_data.get("_luxury_msg")
            if not luxury_msg:
                luxury_msg,_ = build_luxury_msg(sig_data["symbol"], sig_data["entry"], sig_data.get("_rsi",50), sig_data["action"])
            bot.send_message(CHANNEL_ID, luxury_msg)
            active_signals.append({k:v for k,v in sig_data.items() if not k.startswith("_") and v is not None} | {"tp1_hit":False,"tp2_hit":False,"tp3_hit":False} if hasattr(dict, '__or__') else {**{k:v for k,v in sig_data.items() if not k.startswith("_")},"tp1_hit":False,"tp2_hit":False,"tp3_hit":False})
            # Fix for python <3.9 compatibility
            if "tp1_hit" not in active_signals[-1]:
                active_signals[-1]["tp1_hit"]=False; active_signals[-1]["tp2_hit"]=False; active_signals[-1]["tp3_hit"]=False
            bot.answer_callback_query(call.id, "✅ Sent!")
            bot.edit_message_text(f"✅ APPROVED & SENT to {CHANNEL_ID}\n\n{luxury_msg}", call.message.chat.id, call.message.message_id)
        elif data.startswith("reject_"):
            sig_id = data.replace("reject_","")
            pending_signals.pop(sig_id, None)
            bot.answer_callback_query(call.id, "❌ Rejected")
            bot.edit_message_text(f"❌ REJECTED - Not sent", call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(e); bot.answer_callback_query(call.id, "Error")

@bot.message_handler(commands=['start','price','active','signal','id','testsignal'])
def handle_start(message):
    global ADMIN_CHAT_ID
    if message.chat.type == "private":
        ADMIN_CHAT_ID = message.chat.id

    g=get_gold(); b=get_btc()
    r_gold = calc_rsi(prices_history) if len(prices_history)>2 else 50.0
    r_btc = calc_rsi(btc_history) if len(btc_history)>2 else 50.0
    market = "OPEN ✅" if is_forex_market_open() else "CLOSED ❌ Weekend"

    txt = message.text
    if txt.startswith('/id'):
        bot.reply_to(message, f"Your ID: {message.from_user.id}\nChat ID: {message.chat.id}\nPut ID in Render ENV ADMIN_ID")
        return
    if txt.startswith('/testsignal'):
        # force a luxury signal for testing approval
        bot.reply_to(message, "🔔 Creating TEST luxury signal... check your DM for approval!")
        request_approval("GOLD", g, 28.5, "BUY")
        return
    if txt.startswith('/active'):
        if not active_signals: bot.reply_to(message,"📭 No active signals")
        else:
            t=f"📊 {BRAND} Active:\n"
            for s in active_signals: t+=f"{s['symbol']} {s['action']} Entry {s['entry']:.2f}\n"
            bot.reply_to(message,t)
        return
    bot.reply_to(message,f"🤖 {BRAND} BOSS LUXURY ✅\n\n🥇 GOLD: ${g} ({market})\n₿ BTC: ${b:,.2f}\nActive: {len(active_signals)}\nAdmin: {ADMIN_CHAT_ID or ADMIN_ID}\n\nCommands:\n/testsignal - Test approval\n/price /signal /active /id")

threading.Thread(target=signal_loop,daemon=True).start()
threading.Thread(target=lambda: bot.infinity_polling(),daemon=True).start()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
