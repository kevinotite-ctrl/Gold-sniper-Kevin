# -*- coding: utf-8 -*-
import os, requests, time, threading, telebot, datetime, json
from telebot import types
from flask import Flask, request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io

BOT_TOKEN=os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
ADMIN_ID=os.environ.get("ADMIN_ID")
ADMIN_CHAT_ID=None

bot=telebot.TeleBot(BOT_TOKEN)
prices_history=[]
last_signal_time={}
pending_signals={}
ACTIVE_FILE="active_signals.json"
PRICE_CACHE={"price":4195.60, "time":0}

def save_active():
    try:
        with open(ACTIVE_FILE,"w") as f:
            json.dump(active_signals,f)
    except: pass

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
    return f"KEVIN GOLD V5 FINAL - TP $10 + CHART LIVE | Active {len(active_signals)} | Gold ${get_gold()} | RSI {calc_rsi(prices_history) if prices_history else 50}"

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except: pass
    return "OK", 200

def get_gold():
    now=time.time()
    if now - PRICE_CACHE["time"] < 30:
        return PRICE_CACHE["price"]
    try:
        r=requests.get("https://api.gold-api.com/price/XAU", timeout=8).json()
        price=float(r["price"])
        PRICE_CACHE["price"]=price
        PRICE_CACHE["time"]=now
        return price
    except:
        try:
            r=requests.get("https://api.metals.live/v1/spot/gold", timeout=8).json()
            price=float(r[0]) if isinstance(r, list) else 4195.60
            PRICE_CACHE["price"]=price
            PRICE_CACHE["time"]=now
            return price
        except:
            return PRICE_CACHE["price"]

def calc_rsi(prices, period=14):
    if len(prices) < period+1:
        return 50.0
    gains=[]; losses=[]
    for i in range(1, len(prices)):
        diff=prices[i]-prices[i-1]
        if diff>0:
            gains.append(diff); losses.append(0)
        else:
            gains.append(0); losses.append(abs(diff))
    if len(gains)<period:
        return 50.0
    avg_gain=sum(gains[-period:])/period
    avg_loss=sum(losses[-period:])/period
    if avg_loss==0: return 75.0
    if avg_gain==0: return 25.0
    rs=avg_gain/avg_loss
    return 100-(100/(1+rs))

def calc_ema(prices, period=50):
    if len(prices) < period:
        return prices[-1] if prices else 0
    k = 2/(period+1)
    ema = prices[0]
    for p in prices[1:]:
        ema = p*k + ema*(1-k)
    return ema

def is_good_session():
    now_wat = datetime.datetime.now() + datetime.timedelta(hours=1)
    hour = now_wat.hour
    return 13 <= hour <= 21

def is_news_time():
    now_wat = datetime.datetime.now() + datetime.timedelta(hours=1)
    if now_wat.minute < 5:
        return True
    if now_wat.weekday() == 4 and now_wat.hour == 13 and now_wat.minute < 45:
        return True
    return False

# === CHART GENERATOR WITH SIGNAL MARK ===
def create_xauusd_chart(signal_price=None, signal_type=None):
    try:
        if len(prices_history) < 5:
            return None
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10,5))
        ax.plot(prices_history, color='#00FF9D', linewidth=2, label='XAUUSD')
        # EMA50
        ema_vals = []
        temp_ema = prices_history[0]
        k = 2/(50+1)
        for p in prices_history:
            temp_ema = p*k + temp_ema*(1-k)
            ema_vals.append(temp_ema)
        ax.plot(ema_vals, color='#FF6B00', linewidth=1, linestyle='--', label='EMA50')
        
        # Mark signal
        if signal_price:
            color = '#00FF00' if signal_type=='BUY' else '#FF0000'
            ax.scatter(len(prices_history)-1, signal_price, color=color, s=150, marker='^' if signal_type=='BUY' else 'v', label=f'{signal_type} SIGNAL', zorder=5)
            ax.axhline(signal_price, color=color, linestyle=':', alpha=0.5)
        
        rsi_val = calc_rsi(prices_history)
        ax.set_title(f'XAUUSD GOLD V5 - ${prices_history[-1]:.2f} | RSI {rsi_val:.1f} | {signal_type if signal_type else ""}', color='white', fontsize=12, fontweight='bold')
        ax.set_xlabel('Last 200 candles (60s)', color='gray')
        ax.set_ylabel('Price $', color='gray')
        ax.legend(loc='upper left')
        ax.grid(alpha=0.2)
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format='png', dpi=150, facecolor='#0e0e0e')
        buf.seek(0)
        plt.close(fig)
        return buf
    except Exception as e:
        print(f"Chart error {e}")
        return None

def build_short_msg(symbol, price, rsi, action, ema50):
    sl=price-10 if action=="BUY" else price+10
    tp1=price+10 if action=="BUY" else price-10
    emoji="🟢 BUY" if action=="BUY" else "🔴 SELL"
    trend = "Uptrend ✅" if price > ema50 else "Downtrend ✅"
    msg=f"👑 KEVIN V5 80% 👑\n{emoji} XAUUSD GOLD\n\n💠 Entry: ${round(price,2)}\n🛡️ SL: ${round(sl,2)}\n🎯 TP: ${round(tp1,2)} (+$10)\n\n📊 RSI: {round(rsi,1)} | {trend}\nEMA50: ${round(ema50,2)}\n⏰ Session: London/NY ✅\n🔗 @KEVINTRAILBLAZE"
    data={"symbol":symbol,"action":action,"entry":price,"sl":sl,"tp1":tp1}
    return msg,data

def request_approval(symbol, price, rsi, action):
    global ADMIN_CHAT_ID
    target=None
    if ADMIN_ID:
        try: target=int(ADMIN_ID)
        except: pass
    if not target: target=ADMIN_CHAT_ID
    
    ema50 = calc_ema(prices_history, 50)
    short_msg,data=build_short_msg(symbol, price, rsi, action, ema50)
    chart_buf = create_xauusd_chart(price, action)
    
    if not target:
        try:
            # AUTO SEND TO CHANNEL WITH CHART
            if chart_buf:
                bot.send_photo(CHANNEL_ID, chart_buf, caption=short_msg)
            else:
                bot.send_message(CHANNEL_ID, short_msg)
            active_signals.append({"symbol":data["symbol"],"action":data["action"],"entry":data["entry"],"sl":data["sl"],"tp1":data["tp1"]})
            save_active()
        except Exception as e: print(e)
        return
    
    sig_id=symbol+"_"+str(int(time.time()))
    pending_signals[sig_id]=data
    pending_signals[sig_id]["_msg"]=short_msg
    pending_signals[sig_id]["_price"]=price
    pending_signals[sig_id]["_action"]=action
    markup=types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ SEND", callback_data="approve_"+sig_id), types.InlineKeyboardButton("❌ REJECT", callback_data="reject_"+sig_id))
    try:
        if chart_buf:
            bot.send_photo(target, chart_buf, caption=f"🔔 V5 80% SIGNAL 👑\n\n{short_msg}\n\nSend to channel?", reply_markup=markup)
        else:
            bot.send_message(target, f"🔔 V5 80% SIGNAL 👑\n\n{short_msg}\n\nSend to channel?", reply_markup=markup)
    except Exception as e: print(e)

def check_tp_hits(current_price, symbol):
    to_remove=[]
    for sig in active_signals[:]:
        if sig["symbol"]!=symbol: continue
        try:
            s_act=sig["action"]; s_ent=sig["entry"]; s_tp1=sig["tp1"]; s_sl=sig["sl"]
            if s_act=="BUY":
                if current_price>=s_tp1:
                    try: bot.send_message(CHANNEL_ID, f"🏆 TP HIT ✅\nGOLD BUY +$10\n${round(s_ent,2)} -> ${round(s_tp1,2)}\n@KEVINTRAILBLAZE")
                    except: pass
                    to_remove.append(sig)
                elif current_price<=s_sl:
                    try: bot.send_message(CHANNEL_ID, f"🛑 SL HIT GOLD -$10")
                    except: pass
                    to_remove.append(sig)
            else:
                if current_price<=s_tp1:
                    try: bot.send_message(CHANNEL_ID, f"🏆 TP HIT ✅\nGOLD SELL +$10\n${round(s_ent,2)} -> ${round(s_tp1,2)}\n@KEVINTRAILBLAZE")
                    except: pass
                    to_remove.append(sig)
                elif current_price>=s_sl:
                    try: bot.send_message(CHANNEL_ID, f"🛑 SL HIT GOLD -$10")
                    except: pass
                    to_remove.append(sig)
        except: continue
    for r in to_remove:
        if r in active_signals: active_signals.remove(r)
    if to_remove: save_active()

def signal_loop():
    while True:
        try:
            now=time.time()
            g=get_gold()
            prices_history.append(g)
            if len(prices_history)>200: prices_history.pop(0)
            if len(prices_history) < 60:
                print(f"Building history {len(prices_history)}/60", flush=True)
                time.sleep(60)
                continue
            r=calc_rsi(prices_history)
            ema50=calc_ema(prices_history, 50)
            check_tp_hits(g,"GOLD")
            print(f"GOLD ${g} RSI {round(r,1)} EMA50 ${round(ema50,2)} Active {len(active_signals)} GoodSession:{is_good_session()}", flush=True)
            if not is_good_session():
                time.sleep(60)
                continue
            if is_news_time():
                print("News time skip", flush=True)
                time.sleep(60)
                continue
            has_gold = any(s["symbol"]=="GOLD" for s in active_signals)
            if has_gold:
                time.sleep(60)
                continue
            if now - last_signal_time.get("GOLD",0) < 900:
                time.sleep(60)
                continue
            signal_action = None
            if r < 30 and g > ema50:
                signal_action = "BUY"
            elif r > 70 and g < ema50:
                signal_action = "SELL"
            elif r < 25:
                signal_action = "BUY"
            elif r > 75:
                signal_action = "SELL"
            if signal_action:
                request_approval("GOLD", g, r, signal_action)
                last_signal_time["GOLD"] = now
        except Exception as e:
            print("loop error", e, flush=True)
        time.sleep(60)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        d=call.data
        if d.startswith("approve_"):
            sid=d.replace("approve_","")
            sd=pending_signals.pop(sid,None)
            if not sd:
                bot.answer_callback_query(call.id,"Done"); return
            msg=sd.get("_msg")
            price=sd.get("_price")
            action=sd.get("_action")
            chart_buf = create_xauusd_chart(price, action)
            if chart_buf:
                bot.send_photo(CHANNEL_ID, chart_buf, caption=msg)
            else:
                bot.send_message(CHANNEL_ID, msg)
            active_signals.append({"symbol":sd["symbol"],"action":sd["action"],"entry":sd["entry"],"sl":sd["sl"],"tp1":sd["tp1"]})
            save_active()
            bot.answer_callback_query(call.id,"✅ Sent with Chart!")
            bot.edit_message_text("✅ SENT to @KEVINTRAILBLAZE with Chart\n\n"+msg, call.message.chat.id, call.message.message_id)
        elif d.startswith("reject_"):
            pending_signals.pop(d.replace("reject_",""),None)
            bot.answer_callback_query(call.id,"❌ Rejected")
            bot.edit_message_text("❌ Rejected", call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(e)

@bot.message_handler(commands=['start','price','active','signal','id','testsignal','chart'])
def handle_start(message):
    global ADMIN_CHAT_ID
    if message.chat.type=="private":
        ADMIN_CHAT_ID=message.chat.id
    g=get_gold()
    rg=calc_rsi(prices_history) if len(prices_history)>2 else 50.0
    ema50=calc_ema(prices_history,50) if len(prices_history)>50 else g
    txt=message.text
    if txt.startswith('/chart'):
        bot.send_chat_action(message.chat.id, 'upload_photo')
        chart_buf = create_xauusd_chart()
        if chart_buf:
            caption = f"📊 XAUUSD GOLD V5 LIVE CHART\n\n🥇 Price: ${round(g,2)}\n📈 RSI: {round(rg,1)}\n📉 EMA50: ${round(ema50,2)}\n⏰ {datetime.datetime.now().strftime('%H:%M:%S')} WAT\n\n@KEVINTRAILBLAZE"
            bot.send_photo(message.chat.id, chart_buf, caption=caption)
        else:
            bot.reply_to(message, f"⏳ Building chart... {len(prices_history)}/200\nGold: ${round(g,2)} RSI {round(rg,1)}")
        return
    if txt.startswith('/id'):
        bot.reply_to(message, "Your ID: "+str(message.from_user.id)); return
    if txt.startswith('/testsignal'):
        bot.reply_to(message, "🔍 Creating TEST V5 signal with CHART...")
        request_approval("GOLD", g, 28.5, "BUY"); return
    if txt.startswith('/active'):
        if len(active_signals)==0:
            bot.reply_to(message, f"📭 No active GOLD - Waiting\nGold ${round(g,2)} RSI {round(rg,1)} EMA50 ${round(ema50,2)}\nSession {is_good_session()} - Bot scanning 60s")
        else:
            t="📊 ACTIVE GOLD ("+str(len(active_signals))+"):\n"
            for s in active_signals:
                t+=s["symbol"]+" "+s["action"]+" Entry $"+str(round(s["entry"],2))+"\n"
            bot.reply_to(message,t)
        return
    if txt.startswith('/signal') or txt.startswith('/price'):
        bot.reply_to(message, f"🔍 GOLD V5 ANALYSIS 👑\n\n🥇 GOLD: ${round(g,2)}\nRSI: {round(rg,1)} | EMA50: ${round(ema50,2)}\nSession Good: {is_good_session()}\n\nStrategy: RSI<30 + Price>EMA50 = BUY (80%)\nRSI>70 + Price<EMA50 = SELL\nTP $10 / SL $10\nScanning 60s AUTO...\nActive: {len(active_signals)}\n\nChannel: @KEVINTRAILBLAZE"); return
    bot.reply_to(message, f"👑 KEVIN GOLD V5 80% + CHART ✅\n\n🥇 GOLD: ${g}\nRSI: {round(rg,1)} EMA50: ${round(ema50,2)}\n\nGOLD ONLY - TP $10 / SL $10 + LIVE CHART\n80% Strategy: RSI + EMA + Session\n\nCommands:\n/signal - Analyze\n/active - Check active\n/chart - Show XAUUSD Chart 📊\n/testsignal - Test with Chart\n/price /id\n\nBot AUTO 60s!")

threading.Thread(target=signal_loop,daemon=True).start()

if __name__=="__main__":
    try:
        bot.remove_webhook()
        time.sleep(1)
        ext_url = os.getenv("RENDER_EXTERNAL_URL")
        if ext_url:
            bot.set_webhook(url=f"{ext_url}/{BOT_TOKEN}")
            print(f"Webhook set {ext_url}", flush=True)
    except Exception as e:
        print(f"Webhook err {e}", flush=True)
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
