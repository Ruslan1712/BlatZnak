import logging
import os
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === Логирование ===
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# === Google Sheets Setup ===
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("blat-znak-2f081fa17909.json", SCOPE)
CLIENT = gspread.authorize(CREDS)
SHEET = CLIENT.open("все_номера_для_бота").sheet1

# === Telegram Bot ===
PAGE_SIZE_DEFAULT = 10
PAGE_SIZE_MOTO = 30
user_pages = {}
user_categories = {}
user_limits = {}
user_totals = {}

def get_main_keyboard():
    keyboard = [
        ["🛵 Мото номера", "🚛 Прицеп номера"],
        ["🔢 Поиск по цифрам"],
        ["📋 Показать все номера"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_page_keyboard(current_page, total_pages):
    keyboard = []
    row = []
    if current_page > 0:
        row.append("◀️ Предыдущая")
    if current_page < total_pages - 1:
        row.append("▶️ Следующая")
    row.append("⬅️ Назад")
    keyboard.append(row)
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def load_all_numbers_from_gsheet():
    rows = SHEET.get_all_records()
    result = []
    for row in rows:
        number = str(row.get("Номер", "")).lower()
        region = str(row.get("Регион", ""))
        price_raw = str(row.get("Стоимость", "")).replace(" ", "").replace(".", "")
        try:
            price = int(price_raw)
            formatted = f"<b>{number}</b> ({region})\n<b>{price:,} ₽</b>".replace(",", ".")
            result.append((number, formatted))
        except ValueError:
            continue
    return result

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.debug(f"Получен /start от пользователя {update.effective_user.id}")
    await update.message.reply_text("Добро пожаловать! Выберите категорию номеров:", reply_markup=get_main_keyboard())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    text = update.message.text.strip().lower()
    logger.debug(f"Сообщение от {user_id}: {text}")

    if text == "⬅️ назад":
        user_pages.pop(user_id, None)
        user_categories.pop(user_id, None)
        user_limits.pop(user_id, None)
        user_totals.pop(user_id, None)
        await update.message.reply_text("↩️ Возвращаемся в главное меню:", reply_markup=get_main_keyboard())
        return

    if text == "🔢 поиск по цифрам":
        await update.message.reply_text("Отправьте последние цифры номера для поиска (например, 777):")
        return

    if text == "📋 показать все номера":
        all_numbers = load_all_numbers_from_gsheet()
        formatted_list = [entry[1] for entry in all_numbers]
        chunks = [formatted_list[i:i + 10] for i in range(0, len(formatted_list), 10)]
        for chunk in chunks:
            await update.message.reply_text("\n\n".join(chunk), parse_mode="HTML")
        return

    if user_id in user_pages and user_id in user_categories:
        page = user_pages[user_id]
        category_data = user_categories[user_id]
        page_limit = user_limits.get(user_id, PAGE_SIZE_DEFAULT)
        total = user_totals.get(user_id, len(category_data))
        total_pages = max((total + page_limit - 1) // page_limit, 1)

        if text == "◀️ предыдущая" and page > 0:
            page -= 1
        elif text == "▶️ следующая" and page < total_pages - 1:
            page += 1
        user_pages[user_id] = page

        start = page * page_limit
        end = start + page_limit
        await update.message.reply_text(
            f"Страница {page + 1} из {total_pages}\n\n" + "\n\n".join(category_data[start:end]),
            reply_markup=get_page_keyboard(page, total_pages),
            parse_mode="HTML"
        )
        return

    # Поиск по последним 3 цифрам номера (строго по порядку)
    if text.isdigit():
        if len(text) != 3:
            await update.message.reply_text("❗ Введите ровно 3 последние цифры номера (например, 777).")
            return

        matches = []
        for number, formatted in load_all_numbers_from_gsheet():
            digits = re.sub(r"\D", "", number)
            if digits.endswith(text):
                matches.append(formatted)

        if matches:
            chunks = [matches[i:i + 10] for i in range(0, len(matches), 10)]
            for chunk in chunks:
                await update.message.reply_text("\n\n".join(chunk), parse_mode="HTML")
        else:
            await update.message.reply_text("❗ Номеров с такими цифрами не найдено.")
        return

    await update.message.reply_text("❗ Выберите кнопку с категорией.", reply_markup=get_main_keyboard())

if __name__ == '__main__':
    application = Application.builder().token("7799074981:AAFKHc41FKQb_yDI-gemhq6stMagiIfQ680").build()

    logger.info("Бот запущен (DEBUG режим)")

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()
