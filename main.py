import os
import threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")

# ------------------ Flask Server (برای Render) ------------------

app = Flask(__name__)

@app.route("/")
def home():
    return "HooshyarX is alive!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

# ------------------ Telegram Bot ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("سلام 👋\nHooshyarX آماده خدمته!")

def run_bot():
    telegram_app = ApplicationBuilder().token(TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", start))
    telegram_app.run_polling()

# ------------------ Main ------------------

if __name__ == "__main__":
    print("HooshyarX is running...")

    # اجرای سرور برای باز کردن پورت
    threading.Thread(target=run_web).start()

    # اجرای ربات
    run_bot()
