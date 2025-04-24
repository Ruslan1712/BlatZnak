import logging
import os
import re

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# === Настройки ===
BOT_TOKEN = os.getenv("7799074981:AAFKHc41FKQb_yDI-gemhq6stMagiIfQ680")
MOTO_FILE = "moto_numbers.txt"
TRAILER_FILE = "trailer_numbers.txt"
PAGE_SIZE = 20
user_pages = {}

# === Google Sheets ===
SCOPES = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
          "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("blat-znak-2f081fa17909.json", SCOPES)
SHEET = gspread.authorize(CREDS).open("все_номера_для_бота").sheet1

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Старт ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔢 Поиск по цифрам (авто)", callback_data="search_auto")],
        [InlineKeyboardButton("🚗 Все авто номера", callback_data="all_auto")],
        [InlineKeyboardButton("🏍️ Мото номера", callback_data="moto")],
        [InlineKeyboardButton("🚛 Прицеп номера", callback_data="trailer")],
        [InlineKeyboardButton("🛠 Наши услуги", callback_data="services")],
        [InlineKeyboardButton("📍 Наш адрес и контакты", callback_data="contacts")]
    ]
    await update.message.reply_text(
        "Добро пожаловать в компанию BlatZnak!
Мы занимаемся продажей гос номеров и постановкой на учет.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# === Обработка кнопок ===
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "search_auto":
        await query.message.reply_text("Введите цифры для поиска номера (например, 777):")
        context.user_data["state"] = "search_digits"

    elif query.data == "all_auto":
        rows = SHEET.get_all_records()
        if not rows:
            await query.message.reply_text("Данные не найдены.")
            return
        text = "\n".join(
            f"{row['Номер']} | Регион: {row['Регион']} | {row['Цена']} ₽ {f'({row['Комментарий']})' if row.get('Комментарий') else ''}"
            for row in rows
        )
        await query.message.reply_text(text[:4000])

    elif query.data in ["moto", "trailer"]:
        user_pages[user_id] = 0
        context.user_data["type"] = query.data
        await send_page(query, user_id, context)

    elif query.data == "next_page":
        user_pages[user_id] += 1
        await send_page(query, user_id, context)

    elif query.data == "services":
        text = "🛠 Наши услуги:
• Дубликат номеров
• Постановка автомобиля на учет
• Продажа красивых номеров
• Страхование"
        await query.message.reply_text(text)

    elif query.data == "contacts":
        await query.message.reply_text("📍 Адрес: Твардовского 8, к5, с1
📞 Тел: +7 (999) 123-45-67
💬 Telegram: @blatznak
📲 WhatsApp: +7 (999) 123-45-67")

# === Обработка сообщений ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") == "search_digits":
        digits = re.sub(r"\D", "", update.message.text)
        rows = SHEET.get_all_records()
        results = []
        for row in rows:
            plate = str(row.get("Номер", "")).lower()
            digits_only = re.sub(r"\D", "", plate)
            if digits_only.endswith(digits):
                formatted = f"{plate.upper()} | Регион: {row.get('Регион', '')} | {row.get('Цена', '')} ₽"
                if row.get("Комментарий"):
                    formatted += f" ({row['Комментарий']})"
                results.append(formatted)

        if results:
            await update.message.reply_text("\n".join(results[:40]))
        else:
            await update.message.reply_text("❗ Совпадений не найдено.")

        context.user_data["state"] = None

# === Показ мото/прицепов ===
async def send_page(query, user_id, context):
    file_path = MOTO_FILE if context.user_data["type"] == "moto" else TRAILER_FILE
    try:
        with open(file_path, encoding="utf-8") as f:
            items = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await query.edit_message_text("Файл не найден.")
        return

    page = user_pages.get(user_id, 0)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    data = items[start:end]

    if not data:
        await query.edit_message_text("Больше номеров нет.")
        return

    text = "\n".join(data)
    keyboard = []
    if end < len(items):
        keyboard.append([InlineKeyboardButton("➡️ Дальше", callback_data="next_page")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# === Запуск ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()


if __name__ == "__main__":
    main()