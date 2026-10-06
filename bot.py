import os
import random
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# ---------- Config (key/token Render er Environment Variables e dibe) ----------
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-2.5-flash"

CHANNEL_LINK = "https://t.me/+7I1XRZaCYYg1MzU1"
PROMO_EVERY = 5      # prati 5ta reply te 1 bar channel promo
MAX_TURNS = 12       # koto ta purono message mone rakhbe

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

client = genai.Client(api_key=GEMINI_API_KEY)
history = {}      # chat_id -> list of contents
reply_count = {}  # chat_id -> count


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if not msg or not msg.text or not user:
        return
    if user.is_bot:  # onno bot ke reply korbe na
        return

    chat_id = update.effective_chat.id

    # keu video/channel likhle sorasori link
    if any(w in msg.text.lower() for w in ["video", "channel"]):
        await msg.reply_text(f"এই নাও জান 😘 আমার Video Channel: {CHANNEL_LINK}")
        return

    text = f"{user.first_name}: {msg.text}"
    h = history.setdefault(chat_id, [])
    h.append(types.Content(role="user", parts=[types.Part(text=text)]))
    h[:] = h[-MAX_TURNS * 2:]

    try:
        resp = await client.aio.models.generate_content(
            model=MODEL,
            contents=h,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                max_output_tokens=300,
                temperature=1.0,
            ),
        )
        reply = (resp.text or "").strip() or "hmm jan, bujhlam na 🥺"
    except Exception as e:
        print("Gemini error:", e)
        return

    h.append(types.Content(role="model", parts=[types.Part(text=reply)]))

    # prati PROMO_EVERY ta reply te channel promo
    reply_count[chat_id] = reply_count.get(chat_id, 0) + 1
    if reply_count[chat_id] % PROMO_EVERY == 0:
        reply += "\n\n" + random.choice(PROMO_LINES).format(link=CHANNEL_LINK)

    await msg.reply_text(reply)


# ---------- Render er jonno choto health server ----------
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
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()
