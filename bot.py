
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Настройки ===
BOT_TOKEN = "7799074981:AAFKHc41FKQb_yDI-gemhq6stMagiIfQ680"
MOTO_FILE = "moto_numbers.txt"
PAGE_SIZE = 20
user_pages = {}  # user_id: page_index


# === Команды ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏍️ Мото номера", callback_data="show_moto")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите категорию номеров:", reply_markup=reply_markup)


# === Callback обработчик ===
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "show_moto":
        user_pages[user_id] = 0
        await send_moto_page(query, user_id, context)

    elif query.data == "next_moto":
        user_pages[user_id] += 1
        await send_moto_page(query, user_id, context)


# === Отправка страницы с мото номерами ===
async def send_moto_page(query, user_id, context):
    try:
        with open(MOTO_FILE, "r", encoding="utf-8") as f:
            numbers = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        await query.edit_message_text("❌ Файл с мото номерами не найден.")
        return

    page = user_pages.get(user_id, 0)
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    page_numbers = numbers[start_idx:end_idx]

    if not page_numbers:
        await query.edit_message_text("✅ Все мото номера уже показаны.")
        return

    text = "\n".join(page_numbers)
    keyboard = []

    if end_idx < len(numbers):
        keyboard.append([InlineKeyboardButton("➡️ Дальше", callback_data="next_moto")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))


# === Основной запуск ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()


if __name__ == "__main__":
    main()
