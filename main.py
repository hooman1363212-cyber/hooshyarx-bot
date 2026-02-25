import os
import asyncio
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ================== CONFIG ==================

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.environ.get("PORT", 10000))

if not TOKEN:
    raise ValueError("BOT_TOKEN not set in environment variables")

if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL not set in environment variables")

# ================== LOGGING ==================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ================== TELEGRAM APPLICATION ==================

telegram_app = Application.builder().token(TOKEN).build()

# ================== HANDLERS ==================

async def start(update: Update, context):
    await update.message.reply_text("ربات هوشیار ایکس فعال است 🚀")

async def echo(update: Update, context):
    await update.message.reply_text(update.message.text)

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

# ================== FLASK SERVER ==================

flask_app = Flask(__name__)

@flask_app.route("/")
def home():
    return "HooshyarX Bot is running!"

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, telegram_app.bot)

    asyncio.run(telegram_app.process_update(update))
    return "OK"

# ================== STARTUP ==================

async def init_telegram():
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
    logging.info("Webhook set successfully!")

def main():
    asyncio.run(init_telegram())
    flask_app.run(host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
