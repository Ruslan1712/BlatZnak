import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
MOTO_FILE = "moto_numbers.txt"
TRAILER_FILE = "trailer_numbers.txt"
MOSCOW_FILE = "270315af-8756-4519-b3cf-88fac83dbc0b.txt"
PAGE_SIZE = 20
MOSCOW_PAGE_SIZE = 30
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
        [InlineKeyboardButton("🔍 Поиск номера по цифрам (авто)", callback_data="search_auto")],
        [InlineKeyboardButton("🏍 Мото номера", callback_data="moto")],
        [InlineKeyboardButton("🚛 Прицеп номера", callback_data="trailer")],
        [InlineKeyboardButton("📍 Москва все номера", callback_data="moscow")],
        [InlineKeyboardButton("🛠 Наши услуги", callback_data="services")],
        [InlineKeyboardButton("📞 Наш адрес и контакты", callback_data="contacts")]
    ]
    await update.message.reply_text(
        "Добро пожаловать в компанию BlatZnak!\nМы занимаемся продажей гос номеров и постановкой на учет.\nВыберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === Callback обработчик ===
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "search_auto":
        await query.message.reply_text("Отправьте последние цифры номера для поиска (например, 777):")
        return

    elif data == "moto":
        await send_paginated_text(query, context, MOTO_FILE, "moto")

    elif data == "trailer":
        await send_paginated_text(query, context, TRAILER_FILE, "trailer")

    elif data == "moscow":
        await send_paginated_text(query, context, MOSCOW_FILE, "moscow", page_size=MOSCOW_PAGE_SIZE)

    elif data == "services":
        await query.message.reply_text(
            "📌 Наши услуги:\n"
            "- Дубликат номеров\n"
            "- Постановка автомобиля на учет\n"
            "- Продажа красивых номеров\n"
            "- Страхование"
        )

    elif data == "contacts":
        await query.message.reply_text(
            "🏢 Адрес: ул. Твардовского 8 к5 с1\n"
            "📞 Телефон: +7 (495) 127-74-04 [Позвонить](tel:+74951277404)\n"
            "💬 Telegram: @blatznak\n"
            "📱 WhatsApp: +7 903 798-55-89"
        )

    elif data.startswith("next_"):
        category = data.split("_")[1]
        filename = {
            "moto": MOTO_FILE,
            "trailer": TRAILER_FILE,
            "moscow": MOSCOW_FILE
        }.get(category)
        size = MOSCOW_PAGE_SIZE if category == "moscow" else PAGE_SIZE
        await send_paginated_text(query, context, filename, category, next_page=True, page_size=size)

# === Хендлер сообщений (поиск по цифрам) ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        digits = update.message.text.strip()
        results = []
        for row in SHEET.get_all_values()[1:]:
            if digits in row[0]:
                results.append(f"{row[0]} {row[1]} - {row[2]}₽ {row[3]}")
        reply = "\n".join(results) if results else "❗ Номеров с такими цифрами не найдено."
        await update.message.reply_text(reply)

# === Пагинация TXT файлов ===
async def send_paginated_text(query, context, filename, category, next_page=False, page_size=PAGE_SIZE):
    user_id = query.from_user.id
    key = f"{user_id}_{category}"
    page = user_pages.get(key, 0)
    if next_page:
        page += 1
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    start = page * page_size
    end = start + page_size
    page_lines = lines[start:end]
    if not page_lines:
        await query.message.reply_text("Номера закончились.")
        return
    text = "".join(page_lines)
    user_pages[key] = page
    buttons = [[InlineKeyboardButton("➡️ Далее", callback_data=f"next_{category}")]] if end < len(lines) else []
    await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)

# === Main ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
