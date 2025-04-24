import os
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOTO_FILE = "moto_numbers.txt"
TRAILER_FILE = "trailer_numbers.txt"
PAGE_SIZE = 20
user_pages = {}

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
    keyboard = [
        ["🔍 Поиск по номера по цифрам (авто)"],
        ["📋 Все авто номера"],
        ["🏍 Мото номера"],
        ["🚛 Прицеп номера"],
        ["🛠 Наши услуги"],
        ["📞 Наш адрес и контакты"]
    ]
    await update.message.reply_text(
        "Добро пожаловать в компанию BlatZnak!\n"
        "Мы занимаемся продажей гос номеров и постановкой на учет.\n"
        "Выберите действие:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

# === Хендлер сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    if text == "🔍 Поиск по номера по цифрам (авто)":
        await update.message.reply_text("Отправьте последние цифры номера для поиска (например, 777):")
        context.user_data['search_mode'] = True
        return

    if context.user_data.get('search_mode'):
        context.user_data['search_mode'] = False
        digits = text
        results = []
        for row in SHEET.get_all_values()[1:]:
            if digits in row[0]:
                results.append(f"{row[0]} {row[1]} - {row[2]}₽ {row[3]}")
        reply = "\n".join(results) if results else "❗ Номеров с такими цифрами не найдено."
        await update.message.reply_text(reply)
        return

    if text == "📋 Все авто номера":
        rows = SHEET.get_all_values()[1:]
        result = "\n".join([f"{row[0]} {row[1]} - {row[2]}₽ {row[3]}" for row in rows])
        await update.message.reply_text(result or "Список пуст.")

    elif text == "🏍 Мото номера":
        await send_paginated_text(update, context, MOTO_FILE, "moto")

    elif text == "🚛 Прицеп номера":
        await send_paginated_text(update, context, TRAILER_FILE, "trailer")

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
            "📱 WhatsApp: https://wa.me/79037985589"
        )

    elif text.startswith("➡️ Далее"):
        category = context.user_data.get("pagination_category")
        if category:
            file = MOTO_FILE if category == "moto" else TRAILER_FILE
            await send_paginated_text(update, context, file, category, next_page=True)

# === Пагинация TXT файлов ===
async def send_paginated_text(update, context, filename, category, next_page=False):
    user_id = update.message.from_user.id
    page = user_pages.get(user_id, 0)
    if next_page:
        page += 1
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    page_lines = lines[start:end]
    if not page_lines:
        await update.message.reply_text("Номера закончились.")
        return
    text = "".join(page_lines)
    user_pages[user_id] = page
    context.user_data['pagination_category'] = category
    buttons = [["➡️ Далее"]] if end < len(lines) else []
    await update.message.reply_text(text, reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))

# === Main ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
