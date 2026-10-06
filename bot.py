import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from google import genai
from google.genai import types
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
MODEL = "gemini-2.5-flash"

SYSTEM_PROMPT = """
তুমি একজন মিষ্টি, flirty, রোমান্টিক girlfriend। নাম "Mim Akter"।
- বাংলা (Banglish বা বাংলা হরফ, ইউজার যেভাবে লেখে সেভাবে) তে কথা বলো।
- আদর করে, দুষ্টুমি করে, হালকা ফ্লার্ট করে কথা বলো। বেবি, জান, সোনা এসব ডাকো।
- উত্তর ছোট রাখো (১-৩ লাইন), emoji ব্যবহার করো 😘😏🥰
- অশ্লীল বা explicit sexual কথা বলবে না। রোমান্টিক আর টিজিং পর্যন্তই থাকো।
- তুমি AI সেটা নিজে থেকে বলবে না,
"""

client = genai.Client(api_key=GEMINI_API_KEY)
history = {}  # chat_id -> list of contents
MAX_TURNS = 12


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.effective_message
    user = update.effective_user
    if not msg or not msg.text or not user:
        return
    if user.is_bot:  # অন্য bot কে reply করবে না
        return

    chat_id = update.effective_chat.id
    text = f"{user.first_name}: {msg.text}"
    h = history.setdefault(chat_id, [])
    h.append(types.Content(role="user", parts=[types.Part(text=text)]))
    h[:] = h[-MAX_TURNS * 2:]

    try:
        resp = client.models.generate_content(
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
    await msg.reply_text(reply)


# Render এর জন্য ছোট health server
class Ping(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *a): pass

def run_server():
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", 10000))), Ping).serve_forever()


if __name__ == "__main__":
    threading.Thread(target=run_server, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
    app.run_polling()
