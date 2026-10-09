import os, requests, time, threading, pytz, telebot
from flask import Flask
from datetime import datetime
BOT_TOKEN=os.environ.get("BOT_TOKEN")
CHANNEL_ID="@KEVINTRAILBLAZE"
bot=telebot.TeleBot(BOT_TOKEN)
prices_history=[]; active_signals=[]; last_signal_time=0
app=Flask(__name__)
@app.route('/')
def home(): return "Gold Sniper LIVE @KEVINTRAILBLAZE"
def get_gold():
 try: return float(requests.get("https://api.gold-api.com/price/XAU",timeout=10).json().get('price',4196.90))
 except: return 4196.90
def calc_rsi(prices,period=7):
 if len(prices)<period+1: return 50.0
 gains=[]; losses=[]
 for i in range(1,len(prices)):
  d=prices[i]-prices[i-1]; gains.append(max(d,0)); losses.append(abs(min(d,0)))
 ag=sum(gains[-period:])/period; al=sum(losses[-period:])/period
 if al==0: return 78.5 if ag>0 else 21.5
 return round(100-(100/(1+ag/al)),1)
def is_session():
 wat=datetime.now(pytz.timezone('Africa/Lagos')); return 8<=wat.hour<=22
def check_hits(price):
 for s in active_signals[:]:
  if s['status']=='closed': continue
  if s['type']=='SELL':
   if price<=s['tp']: bot.send_message(CHANNEL_ID,f"✅ TP HIT +$20 | SELL {s['entry']:.2f}->{price:.2f} 🔥"); s['status']='closed'
   if price>=s['sl']: bot.send_message(CHANNEL_ID,f"❌ SL HIT -$10 | SELL @KEVINTRAILBLAZE"); s['status']='closed'
  else:
   if price>=s['tp']: bot.send_message(CHANNEL_ID,f"✅ TP HIT +$20 | BUY {s['entry']:.2f}->{price:.2f} 🔥"); s['status']='closed'
   if price<=s['sl']: bot.send_message(CHANNEL_ID,f"❌ SL HIT -$10 | BUY @KEVINTRAILBLAZE"); s['status']='closed'
def scanner():
 global last_signal_time
 while True:
  try:
   if not is_session(): time.sleep(60); continue
   price=get_gold(); prices_history.append(price)
   if len(prices_history)>100: prices_history.pop(0)
   rsi=calc_rsi(prices_history); check_hits(price)
   if time.time()-last_signal_time>1800:
    if rsi>=70:
     sl=price+10; tp=price-20; bot.send_message(CHANNEL_ID,f"🔻 SELL XAUUSD M5\nRSI:{rsi}\nEntry:{price:.2f}\nSL:{sl:.2f} (-$10)\nTP:{tp:.2f} (+$20)\n@KEVINTRAILBLAZE"); active_signals.append({'type':'SELL','entry':price,'sl':sl,'tp':tp,'status':'open'}); last_signal_time=time.time()
    elif rsi<=30:
     sl=price-10; tp=price+20; bot.send_message(CHANNEL_ID,f"🟢 BUY XAUUSD M5\nRSI:{rsi}\nEntry:{price:.2f}\nSL:{sl:.2f} (-$10)\nTP:{tp:.2f} (+$20)\n@KEVINTRAILBLAZE"); active_signals.append({'type':'BUY','entry':price,'sl':sl,'tp':tp,'status':'open'}); last_signal_time=time.time()
  except Exception as e: print(e)
  time.sleep(60)
threading.Thread(target=scanner,daemon=True).start()
@bot.message_handler(commands=['start','price'])
def handle(m): bot.reply_to(m,f"Bot LIVE ✅ Gold:{get_gold()}")
if __name__=="__main__":
 threading.Thread(target=lambda: app.run(host='0.0.0.0',port=int(os.environ.get("PORT",8080))),daemon=True).start()
 bot.infinity_polling()
