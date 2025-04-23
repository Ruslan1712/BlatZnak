
import logging
import os
import re

import gspread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from oauth2client.service_account import ServiceAccountCredentials

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Настройка Google Таблицы ===
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("blat-znak-2f081fa17909.json", SCOPES)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open("все_номера_для_бота").sheet1

# === Telegram Бот ===
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("🔢 Поиск по цифрам", callback_data='search_by_digits')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Выберите категорию номеров:", reply_markup=reply_markup)

async def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    if query.data == 'search_by_digits':
        await query.message.reply_text("Отправьте последние цифры номера для поиска (например, 777):")

async def search(update: Update, context: CallbackContext) -> None:
    digits = update.message.text.strip()
    if not digits.isdigit():
        await update.message.reply_text("Введите только цифры.")
        return

    try:
        rows = SHEET.get_all_records()
    except Exception as e:
        logger.error(f"Ошибка чтения из таблицы: {e}")
        await update.message.reply_text("Произошла ошибка при обращении к базе данных.")
        return

    matches = []
    for row in rows:
        plate = str(row.get("Номер", "")).lower()
        if re.search(f"{digits}$", plate):
            price = row.get("Цена", "")
            comment = row.get("Комментарий", "")
            info = f"🚘 <b>{plate.upper()}</b>
💰 <b>{price}</b>"
            if comment:
                info += f"
📝 {comment}"
            matches.append(info)

    if matches:
        await update.message.reply_text("

".join(matches), parse_mode="HTML")
    else:
        await update.message.reply_text("❗ Номеров с такими цифрами не найдено.")

def main() -> None:
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search))
    application.run_polling()

if __name__ == "__main__":
    main()
