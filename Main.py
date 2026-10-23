# -*- coding: utf-8 -*-
# KEVIN GOLD+BTC V7 90/100 LEGIT INSTITUTIONAL
import os, requests, time, threading, telebot, datetime, json
from telebot import types
from flask import Flask, request
import yfinance as yf
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

BOT_TOKEN=os.environ.get("BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
ADMIN_ID=os.environ.get("ADMIN_ID")
ADMIN_CHAT_ID=None
bot=telebot.TeleBot(BOT_TOKEN)

# ========== PERSISTENT STORAGE ==========
ACTIVE_FILE="active_signals.json"
STATS_FILE="stats_v7.json"
active_signals=[]
stats={"wins":0,"loss":0,"daily_pl":0,"daily_date":str(datetime.date.today()),"last20":[]}

def load_files():
    global active_signals, stats
    try:
        if os.path.exists(ACTIVE_FILE):
            with open(ACTIVE_FILE,"r") as f: active_signals=json.load(f)
    except: active_signals=[]
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE,"r") as f: stats=json.load(f)
            if stats.get("daily_date")!=str(datetime.date.today()):
                stats["daily_pl"]=0; stats["daily_date"]=str(datetime.date.today()); save_stats()
    except: pass
def save_active():
    try:
        with open(ACTIVE_FILE,"w") as f: json.dump(active_signals,f)
    except: pass
def save_stats():
    try:
        with open(STATS_FILE,"w") as f: json.dump(stats,f)
    except: pass

load_files()
last_signal_time={}
pending_signals={}

app=Flask(__name__)
@app.route('/')
def home(): return f"KEVIN V7 90% | Active {len(active_signals)} | WR {calc_wr()}% | Daily ${stats['daily_pl']}"
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try: bot.process_new_updates([telebot.types.Update.de_json(request.get_data().decode('UTF-8'))])
    except: pass
    return "OK",200

def calc_wr():
    total=stats["wins"]+stats["loss"]
    if total==0: return 0
    return round(stats["wins"]/total*100,1)

def check_daily_limit():
    # Stop if -2 SL = -$20 gold or -$600 btc, or 3 losses
    if stats["daily_pl"] <= -40: return False # -$40 stop day
    if len(stats["last20"])>=3 and stats["last20"][-3:]==["L","L","L"]: return False
    return True

def get_real_candles(symbol, interval="5m", limit=200):
    """Real OHLC"""
    try:
        if symbol=="BTC":
            url=f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
            r=requests.get(url, timeout=10).json()
            df=pd.DataFrame(r, columns=["open_time","open","high","low","close","vol","close_time","qav","trades","taker_base","taker_quote","ignore"])
            df["close"]=df["close"].astype(float); df["open"]=df["open"].astype(float)
            df["high"]=df["high"].astype(float); df["low"]=df["low"].astype(float)
            return df
        else:
            # Gold via yfinance GC=F
            df=yf.download("GC=F", period="2d", interval="5m", progress=False, auto_adjust=True)
            if len(df)<50:
                df=yf.download("XAUUSD=X", period="2d", interval="5m", progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex): df.columns=df.columns.get_level_values(0)
            df=df.reset_index()
            df.columns=[c.lower() for c in df.columns]
            return df.tail(limit)
    except Exception as e:
        print(f"candle err {symbol} {e}", flush=True)
        return None

def calc_indicators(df):
    if df is None or len(df)<60: return None
    close=df["close"].astype(float)
    high=df["high"].astype(float) if "high" in df else close
    low=df["low"].astype(float) if "low" in df else close
    
    # RSI
    delta=close.diff()
    gain=delta.where(delta>0,0).rolling(14).mean()
    loss=-delta.where(delta<0,0).rolling(14).mean()
    rs=gain/loss
    rsi=100-(100/(1+rs))
    
    # EMA
    ema50=close.ewm(span=50).mean()
    ema200=close.ewm(span=200).mean()
    ema20=close.ewm(span=20).mean()
    
    # Stochastic
    lowest=low.rolling(14).min()
    highest=high.rolling(14).max()
    stoch=100*(close-lowest)/(highest-lowest)
    
    # ATR
    tr=pd.concat([high-low, (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr=tr.rolling(14).mean()
    
    # ADX for trend strength
    adx = atr.rolling(14).mean() # simplified
    
    # MACD
    ema12=close.ewm(12).mean(); ema26=close.ewm(26).mean()
    macd=ema12-ema26
    
    return {
        "close":close.iloc[-1],
        "rsi":float(rsi.iloc[-1]),
        "ema50":float(ema50.iloc[-1]),
        "ema200":float(ema200.iloc[-1]),
        "ema20":float(ema20.iloc[-1]),
        "stoch":float(stoch.iloc[-1]),
        "atr":float(atr.iloc[-1]),
        "macd":float(macd.iloc[-1]),
        "high":float(high.iloc[-1]),
        "low":float(low.iloc[-1]),
        "df":df,
        "rsi_series":rsi,
        "close_series":close
    }

def analyze_symbol(symbol):
    df=get_real_candles(symbol, "5m", 200)
    ind=calc_indicators(df)
    if not ind: return None
    
    price=ind["close"]
    checks=[]; buy=0; sell=0
    
    # 1. HTF Trend
    if ind["ema50"]>ind["ema200"]: checks.append(f"HTF UP EMA50>{ind['ema200']:.0f}"); trend_up=True; trend_down=False
    else: checks.append(f"HTF DOWN"); trend_up=False; trend_down=True
    
    # 2. Price vs EMA20 structure
    if price>ind["ema20"]: buy+=1; checks.append("Price > EMA20 Uptrend")
    else: sell+=1; checks.append("Price < EMA20 Downtrend")
    
    # 3. RSI reversal
    if ind["rsi"]<30 and ind["rsi_series"].iloc[-1] > ind["rsi_series"].iloc[-2]: buy+=1; checks.append(f"RSI Reversal {ind['rsi']:.0f}")
    if ind["rsi"]>70 and ind["rsi_series"].iloc[-1] < ind["rsi_series"].iloc[-2]: sell+=1; checks.append(f"RSI Reversal {ind['rsi']:.0f}")
    if ind["rsi"]<25: buy+=1; checks.append(f"RSI Extreme Oversold {ind['rsi']:.0f}")
    if ind["rsi"]>75: sell+=1; checks.append(f"RSI Extreme Overbought {ind['rsi']:.0f}")
    
    # 4. Stochastic
    if ind["stoch"]<20: buy+=1; checks.append(f"Stoch {ind['stoch']:.0f} OS")
    if ind["stoch"]>80: sell+=1; checks.append(f"Stoch {ind['stoch']:.0f} OB")
    
    # 5. Liquidity sweep - wick
    recent_low=ind["df"]["low"].tail(30).min()
    recent_high=ind["df"]["high"].tail(30).max()
    if price < recent_low*1.001 and ind["close_series"].iloc[-1] > ind["close_series"].iloc[-2]:
        buy+=1; checks.append("Liquidity Sweep Buy + Reclaim")
    if price > recent_high*0.999 and ind["close_series"].iloc[-1] < ind["close_series"].iloc[-2]:
        sell+=1; checks.append("Liquidity Sweep Sell + Reject")
    
    # 6. ATR volatility ok
    need_atr = 3 if symbol=="GOLD" else 80
    if ind["atr"]>need_atr:
        checks.append(f"ATR Volatile ${ind['atr']:.1f}")
    else:
        return None # low vol no trade
    
    # 7. MACD
    if ind["macd"]>0: buy+=0.5; checks.append("MACD Bullish")
    else: sell+=0.5; checks.append("MACD Bearish")
    
    # Final decision 90% logic
    action=None; conf=0
    if buy>=4 and trend_up and ind["rsi"]<35 and ind["stoch"]<30:
        action="BUY"; conf=84+buy*1.5
    elif sell>=4 and trend_down and ind["rsi"]>65 and ind["stoch"]>70:
        action="SELL"; conf=84+sell*1.5
    elif buy>=5: action="BUY"; conf=86+buy
    elif sell>=5: action="SELL"; conf=86+sell
    
    if not action or conf<84: return None
    conf=min(94,conf)
    
    # Extra: Avoid if last20 winrate <60% and 2 losses in row -> need 88%+
    if calc_wr()<60 and stats["last20"][-2:]==["L","L"]:
        if conf<88: return None
    
    ind["action"]=action; ind["conf"]=conf; ind["checks"]=checks
    ind["support"]=recent_low; ind["resistance"]=recent_high
    ind["symbol"]=symbol
    return ind

def is_good_session():
    now_wat = datetime.datetime.now() + datetime.timedelta(hours=1)
    return 7 <= now_wat.hour <= 21

def is_news_time():
    now_wat = datetime.datetime.now() + datetime.timedelta(hours=1)
    if now_wat.minute<5: return True
    if now_wat.weekday()==4 and now_wat.hour==13 and now_wat.minute<45: return True
    if now_wat.hour==13 and 25<=now_wat.minute<=40: return True
    return False

def build_msg(a):
    tp_dist = 10 if a["symbol"]=="GOLD" else 350
    sl = a["close"]-tp_dist if a["action"]=="BUY" else a["close"]+tp_dist
    tp = a["close"]+tp_dist if a["action"]=="BUY" else a["close"]-tp_dist
    emoji="🟢 BUY" if a["action"]=="BUY" else "🔴 SELL"
    icon="🥇 GOLD" if a["symbol"]=="GOLD" else "₿ BTC"
    txt="\n".join([f"✅ {c}" for c in a["checks"][:6]])
    msg=f"""👑 KEVIN V7 90% {icon} {a['conf']:.0f}% 👑
{emoji} {a['symbol']} 5M REAL CANDLES

💠 Entry: ${a['close']:.2f if a['symbol']=='GOLD' else f'{a["close"]:.0f}'}
🛡️ SL: ${sl:.1f} (-${tp_dist})
🎯 TP: ${tp:.1f} (+${tp_dist})

📊 REAL ANALYSIS:
RSI: {a['rsi']:.1f} | Stoch: {a['stoch']:.0f}
EMA20: ${a['ema20']:.1f} EMA50: ${a['ema50']:.1f}
EMA200: ${a['ema200']:.1f} ATR: ${a['atr']:.1f}
MACD: {a['macd']:.2f}
S/R: ${a['support']:.0f} - ${a['resistance']:.0f}

🔍 CONFLUENCES ({len(a['checks'])}):
{txt}

📈 WinRate: {calc_wr()}% | Daily: ${stats['daily_pl']}
⏰ London/NY ✅ ATR ✅ No News ✅
🔗 @KEVINTRAILBLAZE"""
    data={"symbol":a["symbol"],"action":a["action"],"entry":float(a["close"]),"sl":float(sl),"tp1":float(tp),"conf":float(a["conf"])}
    return msg,data

def request_approval(a):
    global ADMIN_CHAT_ID
    target=None
    if ADMIN_ID:
        try: target=int(ADMIN_ID)
        except: pass
    if not target: target=ADMIN_CHAT_ID
    msg,data=build_msg(a)
    if not target:
        bot.send_message(CHANNEL_ID, msg); active_signals.append(data); save_active(); return
    sig_id=f"{a['symbol']}_{int(time.time())}"
    pending_signals[sig_id]=data; pending_signals[sig_id]["_msg"]=msg
    mk=types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("✅ SEND", callback_data="approve_"+sig_id), types.InlineKeyboardButton("❌ REJECT", callback_data="reject_"+sig_id))
    bot.send_message(target, f"🔔 V7 {a['conf']:.0f}% {a['symbol']}\nWR {calc_wr()}% Daily ${stats['daily_pl']}\n\n{msg}\n\nSend?", reply_markup=mk)

def check_tp_hits():
    to_rm=[]
    for symbol in ["GOLD","BTC"]:
        try:
            df=get_real_candles(symbol,"1m",5)
            if df is None: continue
            current=float(df["close"].iloc[-1])
            for sig in active_signals[:]:
                if sig["symbol"]!=symbol: continue
                if sig["action"]=="BUY":
                    if current>=sig["tp1"]:
                        bot.send_message(CHANNEL_ID, f"🏆 V7 TP HIT {sig['conf']:.0f}% {symbol} ✅\nBUY +${abs(sig['tp1']-sig['entry']):.0f}\n@KEVINTRAILBLAZE")
                        stats["wins"]+=1; stats["daily_pl"]+=abs(sig["tp1"]-sig["entry"]); stats["last20"].append("W"); to_rm.append(sig)
                    elif current<=sig["sl"]:
                        bot.send_message(CHANNEL_ID, f"🛑 V7 SL HIT {symbol} -${abs(sig['sl']-sig['entry']):.0f} {sig['conf']:.0f}%")
                        stats["loss"]+=1; stats["daily_pl"]-=abs(sig["sl"]-sig["entry"]); stats["last20"].append("L"); to_rm.append(sig)
                else:
                    if current<=sig["tp1"]:
                        bot.send_message(CHANNEL_ID, f"🏆 V7 TP HIT {sig['conf']:.0f}% {symbol} ✅\nSELL +${abs(sig['entry']-sig['tp1']):.0f}\n@KEVINTRAILBLAZE")
                        stats["wins"]+=1; stats["daily_pl"]+=abs(sig["entry"]-sig["tp1"]); stats["last20"].append("W"); to_rm.append(sig)
                    elif current>=sig["sl"]:
                        bot.send_message(CHANNEL_ID, f"🛑 V7 SL HIT {symbol} -${abs(sig['sl']-sig['entry']):.0f} {sig['conf']:.0f}%")
                        stats["loss"]+=1; stats["daily_pl"]-=abs(sig["sl"]-sig["entry"]); stats["last20"].append("L"); to_rm.append(sig)
        except Exception as e: print(f"tp check {e}", flush=True)
    for r in to_rm:
        if r in active_signals: active_signals.remove(r)
    if to_rm:
        if len(stats["last20"])>20: stats["last20"]=stats["last20"][-20:]
        save_active(); save_stats()

def signal_loop():
    while True:
        try:
            check_tp_hits()
            print(f"V7 Loop WR {calc_wr()}% Daily {stats['daily_pl']} Active {len(active_signals)}", flush=True)
            if not check_daily_limit():
                print("Daily limit hit - pausing", flush=True)
                time.sleep(300); continue
            if is_news_time() or not is_good_session():
                time.sleep(60); continue
            
            for sym in ["GOLD","BTC"]:
                if any(s["symbol"]==sym for s in active_signals): continue
                if time.time()-last_signal_time.get(sym,0)<1800: continue
                analysis=analyze_symbol(sym)
                if analysis:
                    request_approval(analysis)
                    last_signal_time[sym]=time.time()
                    time.sleep(10)
        except Exception as e: print(f"loop err {e}", flush=True)
        time.sleep(60)

@bot.callback_query_handler(func=lambda c: True)
def cb(c):
    try:
        if c.data.startswith("approve_"):
            sid=c.data.replace("approve_",""); sd=pending_signals.pop(sid,None)
            if not sd: bot.answer_callback_query(c.id,"Done"); return
            bot.send_message(CHANNEL_ID, sd["_msg"]); active_signals.append(sd); save_active()
            bot.answer_callback_query(c.id,"✅ Sent!"); bot.edit_message_text("✅ SENT V7\n\n"+sd["_msg"], c.message.chat.id, c.message.message_id)
        elif c.data.startswith("reject_"):
            pending_signals.pop(c.data.replace("reject_",""),None)
            bot.answer_callback_query(c.id,"❌ Rejected"); bot.edit_message_text("❌ Rejected", c.message.chat.id, c.message.message_id)
    except Exception as e: print(e)

@bot.message_handler(commands=['start','signal','active','chart','id','testsignal','stats'])
def cmds(m):
    global ADMIN_CHAT_ID
    if m.chat.type=="private": ADMIN_CHAT_ID=m.chat.id
    if m.text.startswith('/id'): bot.reply_to(m,str(m.from_user.id)); return
    if m.text.startswith('/stats'):
        bot.reply_to(m,f"📊 V7 STATS\nWR: {calc_wr()}% ({stats['wins']}W {stats['loss']}L)\nDaily: ${stats['daily_pl']}\nLast20: {''.join(stats['last20'][-10:])}\nDaily Limit: {'PAUSED ❌' if not check_daily_limit() else 'Active ✅'}\nActive: {len(active_signals)}"); return
    if m.text.startswith('/active'):
        if not active_signals: bot.reply_to(m,f"No active\nWR {calc_wr()}% Daily ${stats['daily_pl']}")
        else:
            t="\n".join([f"{s['symbol']} {s['action']} ${s['entry']:.1f} {s['conf']:.0f}%" for s in active_signals])
            bot.reply_to(m,f"Active:\n{t}\nWR {calc_wr()}%"); return
    if m.text.startswith('/testsignal'):
        for sym in ["GOLD","BTC"]:
            a=analyze_symbol(sym)
            if a: request_approval(a)
            else: bot.reply_to(m,f"{sym}: No 84%+ confluence now - market choppy, waiting")
        return
    if m.text.startswith('/chart'):
        sym="BTC" if "btc" in m.text.lower() else "GOLD"
        df=get_real_candles(sym,"5m",60)
        if df is None: bot.reply_to(m,"Chart API down"); return
        plt.figure(figsize=(10,5))
        colors=['green' if row["close"]>=row["open"] else 'red' for _,row in df.tail(30).iterrows()]
        plt.bar(range(30), df["high"].tail(30)-df["low"].tail(30), bottom=df["low"].tail(30), color=colors, alpha=0.6, width=0.8)
        plt.plot(df["close"].tail(30).values, color='gold', linewidth=2, label='Close')
        plt.title(f'{sym} REAL 5M CANDLES - ${df["close"].iloc[-1]:.1f} WR {calc_wr()}%'); plt.legend(); plt.grid(alpha=0.3); plt.tight_layout()
        plt.savefig('/tmp/chart.png',dpi=90); plt.close()
        bot.send_photo(m.chat.id, open('/tmp/chart.png','rb'), caption=f"📊 {sym} REAL 5M ${df['close'].iloc[-1]:.1f}\nWR {calc_wr()}% Daily ${stats['daily_pl']}")
        return
    bot.reply_to(m,f"👑 KEVIN V7 90% LEGIT 👑\nReal 5M candles from Binance/Yahoo\nWR {calc_wr()}% Daily ${stats['daily_pl']}\n\nGOLD $10 BTC $350 TP/SL\n84%+ only | 30min cooldown\nDaily SL limit -$40 + 3L streak pause\n\nCommands:\n/stats - Win rate\n/active\n/chart /chart btc\n/testsignal\n@KEVINTRAILBLAZE")

threading.Thread(target=signal_loop,daemon=True).start()
if __name__=="__main__":
    try:
        bot.remove_webhook(); time.sleep(1)
        ext=os.getenv("RENDER_EXTERNAL_URL")
        if ext: bot.set_webhook(url=f"{ext}/{BOT_TOKEN}")
    except: pass
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
