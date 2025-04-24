
import logging
import os
import re

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Настройка Google Sheets ===
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name("blat-znak-2f081fa17909.json", SCOPES)
client = gspread.authorize(creds)
sheet = client.open("все_номера_для_бота").sheet1

# === Telegram Bot ===
TOKEN = os.getenv("BOT_TOKEN")
application = Application.builder().token(TOKEN).build()


# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("🔢 Поиск по цифрам")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Добро пожаловать! Выберите категорию номеров:", reply_markup=reply_markup)


# === Обработка текста ===
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    if query.startswith("/"):
        return  # Команды не обрабатываем

    if "поиск" in query.lower():
        await update.message.reply_text("Отправьте последние цифры номера для поиска (например, 777):")
        return

    user_digits = re.sub(r"\D", "", query)

    if not user_digits:
        await update.message.reply_text("❗ Введите только цифры для поиска.")
        return

    rows = sheet.get_all_records()
    results = []

    for row in rows:
        number = str(row.get("Номер", "")).lower().strip()
        digits_only = re.sub(r"\D", "", number)

        if digits_only.endswith(user_digits):
            region = row.get("Регион", "")
            price = row.get("Цена", "")
            comment = row.get("Комментарий", "")
            result_line = f"• {number.upper()} | Регион: {region} | {price} ₽ {f'({comment})' if comment else ''}"
            results.append(result_line)

    if results:
        await update.message.reply_text("🔎 Найдено:\n" + "\n".join(results))
    else:
        await update.message.reply_text("❗ Номеров с такими цифрами не найдено.")


# === Регистрация хендлеров ===
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

# === Запуск бота ===
if __name__ == "__main__":
    application.run_polling()
