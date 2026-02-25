import os
import sqlite3
import asyncio
import random
from datetime import datetime, timedelta

from telegram import (Update, ReplyKeyboardMarkup, InlineKeyboardMarkup,
                      InlineKeyboardButton)
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler,
                          ContextTypes, CallbackQueryHandler, filters)
from telegram.constants import ChatAction
from openai import OpenAI

# ================= CONFIG =================

BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")  # بدون @
AVALAI_API_KEY = os.getenv("AVALAI_API_KEY")

BASE_URL = "https://api.avalai.ir/v1"
MODEL_NAME = "gpt-4o-mini"

client = OpenAI(api_key=AVALAI_API_KEY, base_url=BASE_URL)

# ================= DATABASE =================

conn = sqlite3.connect("hooshyarx.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    requests_today INTEGER DEFAULT 0,
    last_request_date TEXT,
    is_vip INTEGER DEFAULT 0,
    vip_expiry TEXT,
    invite_count INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    role TEXT,
    content TEXT,
    timestamp TEXT
)
""")

conn.commit()

# ================= KEYBOARDS =================


def main_menu(user_id):
    keyboard = [["✍ تولید محتوا", "📱 کپشن اینستاگرام"],
                ["🎓 کمک درسی", "🌍 ترجمه متن"], ["🧠 گفت‌وگو با هوشیار"],
                ["💎 حساب من"]]

    if user_id == OWNER_ID:
        keyboard.append(["👑 پنل مدیریت"])

    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def back_menu():
    return ReplyKeyboardMarkup([["🔙 بازگشت به منوی اصلی"]],
                               resize_keyboard=True)


def admin_menu():
    keyboard = [["👥 تعداد کاربران"], ["💎 فعالسازی VIP"], ["❌ حذف VIP"],
                ["🔙 بازگشت به منوی اصلی"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def join_channel_keyboard():
    keyboard = [[
        InlineKeyboardButton("📢 عضویت در کانال",
                             url=f"https://t.me/{CHANNEL_USERNAME}")
    ], [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check_join")]]
    return InlineKeyboardMarkup(keyboard)


# ================= MODE ENTRY MESSAGES =================

mode_entry_messages = {
    "✍ تولید محتوا": [
        "موضوعت رو بگو تا برات یه متن حرفه‌ای بسازم ✍✨",
        "ایده‌ت چیه؟ رسمی، دوستانه یا تبلیغاتی؟ 🚀"
    ],
    "📱 کپشن اینستاگرام": ["عکس درباره چیه؟ یه کپشن وایرال برات می‌چینم 📸🔥"],
    "🎓 کمک درسی": ["سوالتو بفرست، باهم حلش می‌کنیم 👨🏻‍🏫"],
    "🌍 ترجمه متن": ["متن رو بفرست، دقیق ترجمه می‌کنم 🌍"],
    "🧠 گفت‌وگو با هوشیار": ["من اینجام. راحت حرف بزن 💬"]
}

# ================= UTILITIES =================


def get_user(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id, ))
    return cursor.fetchone()


def add_user(user_id, first_name):
    if not get_user(user_id):
        cursor.execute(
            """
        INSERT INTO users (user_id, first_name, last_request_date)
        VALUES (?, ?, ?)
        """, (user_id, first_name, datetime.now().date().isoformat()))
        conn.commit()


async def is_user_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(
            chat_id=f"@{CHANNEL_USERNAME}", user_id=update.effective_user.id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def enforce_join(update: Update, context: ContextTypes.DEFAULT_TYPE):
    joined = await is_user_joined(update, context)
    if not joined:
        if update.message:
            await update.message.reply_text(
                "برای استفاده از هوشیار باید عضو کانال ما باشی 👇",
                reply_markup=join_channel_keyboard())
        return False
    return True


def check_limit(user):
    today = datetime.now().date().isoformat()

    if user[4] == 1 and user[5]:
        expiry = datetime.fromisoformat(user[5])
        if expiry > datetime.now():
            return True
        else:
            cursor.execute("UPDATE users SET is_vip=0 WHERE user_id=?",
                           (user[0], ))
            conn.commit()

    if user[3] != today:
        cursor.execute(
            """
        UPDATE users SET requests_today=0, last_request_date=?
        WHERE user_id=?
        """, (today, user[0]))
        conn.commit()
        return True

    if user[2] >= 5:
        return False

    return True


def increase_request(user_id):
    cursor.execute(
        "UPDATE users SET requests_today = requests_today + 1 WHERE user_id=?",
        (user_id, ))
    conn.commit()


# ================= HANDLERS =================


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await enforce_join(update, context):
        return

    user = update.effective_user
    add_user(user.id, user.first_name)

    await update.message.reply_text(
        f"سلام {user.first_name} 👋\nمن هوشیارم.\nاز منو انتخاب کن 👇",
        reply_markup=main_menu(user.id))


async def check_join_callback(update: Update,
                              context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    joined = await is_user_joined(update, context)

    if joined:
        await query.message.delete()
        await query.message.reply_text(
            "عضویت تایید شد ✅\nحالا میتونی از هوشیار استفاده کنی 👇",
            reply_markup=main_menu(update.effective_user.id))
    else:
        await query.answer("هنوز عضو نشدی ❌", show_alert=True)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await enforce_join(update, context):
        return

    user = update.effective_user
    text = update.message.text
    user_data = get_user(user.id)

    if text == "🔙 بازگشت به منوی اصلی":
        context.user_data.clear()
        await update.message.reply_text("برگشتیم 👌",
                                        reply_markup=main_menu(user.id))
        return

    if text == "💎 حساب من":
        status = "VIP" if user_data[4] == 1 else "عادی"
        await update.message.reply_text(f"وضعیت حساب: {status}\n"
                                        f"درخواست امروز: {user_data[2]}/5\n"
                                        f"دعوت‌ها: {user_data[6]}")
        return

    if text == "👑 پنل مدیریت":
        if user.id != OWNER_ID:
            await update.message.reply_text("دسترسی نداری.")
            return
        await update.message.reply_text("پنل مدیریت 👇",
                                        reply_markup=admin_menu())
        return

    if text == "👥 تعداد کاربران" and user.id == OWNER_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await update.message.reply_text(f"تعداد کاربران: {count}")
        return

    if text in mode_entry_messages:
        context.user_data["mode"] = text
        await update.message.reply_text(random.choice(
            mode_entry_messages[text]),
                                        reply_markup=back_menu())
        return

    if not check_limit(user_data):
        await update.message.reply_text("به سقف 5 درخواست امروز رسیدی 👀")
        return

    mode = context.user_data.get("mode")
    if mode:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id,
                                           action=ChatAction.TYPING)
        await asyncio.sleep(2)

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{
                "role": "system",
                "content": "تو یک دستیار هوشمند فارسی هستی."
            }, {
                "role": "user",
                "content": text
            }],
            temperature=0.7)

        answer = response.choices[0].message.content
        increase_request(user.id)
        await update.message.reply_text(answer)
        return

    await update.message.reply_text("از منو انتخاب کن 👇",
                                    reply_markup=main_menu(user.id))


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(
        CallbackQueryHandler(check_join_callback, pattern="check_join"))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("HooshyarX is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
