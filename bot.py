import logging
import os
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Настройка Google Таблицы ===
SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive"
]

CREDS = ServiceAccountCredentials.from_json_keyfile_name("blat-znak-2f081fa17909.json", SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open("все_номера_для_бота").sheet1

# === Telegram бот ===
user_states = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    user_states[user_id] = None
    keyboard = [["🔢 Поиск по цифрам"]]
    await update.message.reply_text("Добро пожаловать! Выберите категорию номеров:",
                                    reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_chat.id
    text = update.message.text.strip()

    if text == "🔢 Поиск по цифрам":
        user_states[user_id] = "search_digits"
        await update.message.reply_text("Отправьте последние цифры номера для поиска (например, 777):")
        return

    if user_states.get(user_id) == "search_digits":
        digits = re.sub(r"\D", "", text)
        if not digits:
            await update.message.reply_text("Введите только цифры.")
            return

        rows = SHEET.get_all_records()
        results = []

        for row in rows:
            number = str(row.get("Номер", ""))
            if number[-len(digits):] == digits:
                price = row.get("Цена", "—")
                region = row.get("Регион", "—")
                comment = row.get("Комментарий", "")
                formatted = f"🚗 *{number}* | {region} | 💰 {price}" + (f"\n💬 {comment}" if comment else "")
                results.append(formatted)

        if results:
            reply = "\n\n".join(results)
        else:
            reply = "❗ Номеров с такими цифрами не найдено."

        await update.message.reply_text(reply, parse_mode="Markdown")
        return

    await update.message.reply_text("Выберите категорию или введите цифры номера.")

# === Запуск ===
def main():
    TOKEN = os.getenv("BOT_TOKEN")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
