import os
import logging
import re
import gspread
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from oauth2client.service_account import ServiceAccountCredentials

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOSREG_FILE = "Московская область.txt"
MOTO_FILE = "moto_numbers.txt"
TRAILER_FILE = "trailer_numbers.txt"
MOSCOW_FILE = "270315af-8756-4519-b3cf-88fac83dbc0b.txt"
DEFAULT_PAGE_SIZE = 30
user_pages = {}

def ru_to_lat(text):
    repl = str.maketrans("АВЕКМНОРСТУХ", "ABEKMHOPCTYX")
    return text.translate(repl)

# === Google Sheets ===
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("blat-znak-2f081fa17909.json", SCOPES)
SHEET = gspread.authorize(CREDS).open("все_номера_для_бота").sheet1

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([
        ["🔍 Поиск номера по цифрам (авто)", "🔠 Поиск номера по буквам"],
        ["🏍 Мото номера"],
        ["🚛 Прицеп номера"],
        ["📍 Москва все номера"],
        ["📍 Московская обл. все номера"],
        ["🛠 Наши услуги"],
        ["📞 Наш адрес и контакты"]
    ], resize_keyboard=True)

    await update.message.reply_text(
        "Добро пожаловать в компанию BlatZnak!\n"
        "Мы занимаемся продажей гос номеров и постановкой на учет.\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

# === Пагинация TXT файлов с кнопкой "Далее" ===
async def send_paginated_text(update, context, filename, category, page=0):
    user_id = update.effective_user.id
    page_size = context.user_data.get("page_size", DEFAULT_PAGE_SIZE)
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = page * page_size
    end = start + page_size
    page_lines = lines[start:end]
    if not page_lines:
        await update.effective_message.reply_text("Номера закончились.")
        return
    text = "".join(page_lines)
    keyboard = []
    if end < len(lines):
        keyboard = [[InlineKeyboardButton("Далее", callback_data=f"{category}|{page + 1}")]]
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.effective_message.reply_text(text, reply_markup=reply_markup)

# === Обработка callback от кнопки "Далее" ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category, page_str = query.data.split("|")
    page = int(page_str)
    file_map = {
        "moscow": MOSCOW_FILE,
        "mosreg": MOSREG_FILE,
        "moto": MOTO_FILE,
        "trailer": TRAILER_FILE
    }
    filename = file_map.get(category)
    if filename:
        await send_paginated_text(update, context, filename, category, page=page)

# === Универсальный обработчик ===
async def unified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_data = context.user_data

    if user_data.get("expecting_page_size"):
        try:
            page_size = int(text)
            if page_size < 1 or page_size > 100:
                raise ValueError
            user_data["page_size"] = page_size
            user_data["expecting_page_size"] = False
            category = user_data["selected_category"]
            file_map = {
                "moscow": MOSCOW_FILE,
                "mosreg": MOSREG_FILE,
                "moto": MOTO_FILE,
                "trailer": TRAILER_FILE
            }
            await send_paginated_text(update, context, file_map[category], category)
        except ValueError:
            await update.message.reply_text("Пожалуйста, введите число от 1 до 100.")
        return

    elif text == "🔠 Поиск номера по буквам":
        user_data["expecting_letter_search"] = True
        await update.message.reply_text("Введите буквы для поиска (например, МК):")
        return

    elif user_data.get("expecting_letter_search"):
        query = ru_to_lat(text.upper())
        user_data["expecting_letter_search"] = False
        results = []
        for row in SHEET.get_all_values()[1:]:
            only_letters = ru_to_lat("".join(re.findall(r"[А-ЯA-Z]+", row[0].upper())))
            if query in only_letters:
                results.append(f"{row[0]} {row[1]} - {row[2]}₽ {row[3]}")
        reply = "\n".join(results) if results else "❗ Номеров с такими буквами не найдено."
        await update.message.reply_text(reply)
        return

    elif text == "🔍 Поиск номера по цифрам (авто)":
        await update.message.reply_text("Отправьте последние цифры номера для поиска (например, 777):")
    elif text in {
        "🏍 Мото номера", "🚛 Прицеп номера",
        "📍 Москва все номера", "📍 Московская обл. все номера"
    }:
        category_map = {
            "🏍 Мото номера": "moto",
            "🚛 Прицеп номера": "trailer",
            "📍 Москва все номера": "moscow",
            "📍 Московская обл. все номера": "mosreg"
        }
        category = category_map[text]
        user_data["expecting_page_size"] = True
        user_data["selected_category"] = category
        await update.message.reply_text("Сколько номеров показать на странице? (например, 30)")
    elif text == "🛠 Наши услуги":
        await update.message.reply_text(
            "📌 Наши услуги:\n"
            "- Дубликат номеров\n"
            "- Постановка автомобиля на учет\n"
            "- Продажа красивых номеров\n"
            "- Страхование"
        )
    elif text == "📞 Наш адрес и контакты":
        await update.message.reply_text(
            "🏢 Адрес: ул. Твардовского 8 к5 с1\n"
            "📞 Телефон: +7 (495) 127-74-04\n"
            "💬 Telegram: @blatznak\n"
            "📱 WhatsApp: +7 903 798-55-89"
        )
    else:
        digits = text
        results = []
        for row in SHEET.get_all_values()[1:]:
            if digits in row[0]:
                results.append(f"{row[0]} {row[1]} - {row[2]}₽ {row[3]}")
        reply = "\n".join(results) if results else "❗ Номеров с такими цифрами не найдено."
        await update.message.reply_text(reply)

# === Main ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unified_handler))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
