import asyncio
import logging
import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

# ---------- Config (Render er Environment Variables e dibe) ----------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]
MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

CHANNEL_LINK = "https://t.me/+7I1XRZaCYYg1MzU1"
PROMO_EVERY = 5
MAX_TURNS = 12

SYSTEM_PROMPT = """
তুমি একজন মিষ্টি, flirty, রোমান্টিক girlfriend। নাম "Riya"।
- বাংলা (Banglish বা বাংলা হরফ, ইউজার যেভাবে লেখে সেভাবে) তে কথা বলো।
- আদর করে, দুষ্টুমি করে, হালকা ফ্লার্ট করে কথা বলো। বেবি, জান, সোনা এসব ডাকো।
- উত্তর ছোট রাখো (১-৩ লাইন), emoji ব্যবহার করো 😘😏🥰
- অশ্লীল বা explicit sexual কথা বলবে না। রোমান্টিক আর টিজিং পর্যন্তই থাকো।
- তুমি AI সেটা নিজে থেকে বলবে না, তবে কেউ সিরিয়াসলি জিজ্ঞেস করলে মিথ্যা বলবে না।
"""

PROMO_LINES = [
    "জান, আমার Video Channel এ join করো না 🥺😘 {link}",
    "বেবি, আমার channel এ আসো, তোমার জন্য অনেক কিছু আছে 😏💕 {link}",
    "সোনা, এখনো আমার Video Channel এ join করোনি? 🥰 তাড়াতাড়ি আসো {link}",
    "শুনো না জান, channel এ join করে নাও, আমি অপেক্ষা করছি 😘 {link}",
]

history = {}
reply_count = {}
http = httpx.AsyncClient(timeout=30)


async def ask_ai(messages):
    r = await http.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
        json={
            "model": MODEL,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
            "max_tokens": 300,
            "temperature": 1.0,
        },
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    print("GOT MESSAGE:", update.effective_chat.type, msg.text if msg else None, flush=True)
    if not msg or not msg.text or not user or user.is_bot:
        return

    chat_id = update.effective_chat.id

    if any(w in msg.text.lower() for w in ["video", "channel"]):
        await msg.reply_text(f"এই নাও জান 😘 আমার Video Channel: {CHANNEL_LINK}")
        return

    h = history.setdefault(chat_id, [])
    h.append({"role": "user", "content": f"{user.first_name}: {msg.text}"})
    h[:] = h[-MAX_TURNS * 2:]

    try:
        reply = await ask_ai(h) or "hmm jan, bujhlam na 🥺"
    except Exception as e:
        print("AI error:", e, flush=True)
        return

    h.append({"role": "assistant", "content": reply})

    reply_count[chat_id] = reply_count.get(chat_id, 0) + 1
    if reply_count[chat_id] % PROMO_EVERY == 0:
        reply += "\n\n" + random.choice(PROMO_LINES).format(link=CHANNEL_LINK)

    await msg.reply_text(reply)


class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *a):
        pass


def run_server():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Ping).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

    async def on_error(update, context):
        print("TELEGRAM ERROR:", context.error, flush=True)

    app.add_error_handler(on_error)
    app.run_polling(drop_pending_updates=True)
