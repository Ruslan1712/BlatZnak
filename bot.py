import os
import logging
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Убедитесь, что BOT_TOKEN задан в переменных окружения
DEFAULT_PAGE_SIZE = 30

# === Пути к файлам (если используете текстовые списки номеров) ===
MOSREG_FILE = "Московская область.txt"
MOTO_FILE = "moto_numbers.txt"
TRAILER_FILE = "trailer_numbers.txt"
MOSCOW_FILE = "270315af-8756-4519-b3cf-88fac83dbc0b.txt"

# === Преобразование кириллицы в латиницу ===
def ru_to_lat(text):
    repl = str.maketrans("АВЕКМНОРСТУХ", "ABEKMHOPCTYX")
    return text.translate(repl)

# === Подключение к Google Sheets ===
SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
CREDS = ServiceAccountCredentials.from_json_keyfile_name("blat-znak-2f081fa17909.json", SCOPES)
SHEET = gspread.authorize(CREDS).open("все_номера_для_бота").sheet1

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === Команда /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([
        ["🔁 Старт"],
        ["🔍 Поиск номера по цифрам", "🔠 Поиск номера по буквам"],
        ["🏍 Мото номера", "🚛 Прицеп номера"],
        ["📍 Москва все номера", "📍 Московская обл. все номера"],
        ["🛠 Наши услуги", "📞 Наш адрес и контакты"]
    ], resize_keyboard=True)

    await update.message.reply_text(
        "Добро пожаловать в компанию BlatZnak!\n"
        "Мы занимаемся продажей гос номеров и постановкой на учет.\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

# === Отправка файла ===
async def send_full_file(update: Update, context: ContextTypes.DEFAULT_TYPE, filename: str):
    if not os.path.exists(filename):
        await update.message.reply_text("Файл с номерами не найден.")
        return
    with open(filename, "r", encoding="utf-8") as f:
        content = f.read()
        for i in range(0, len(content), 4000):
            await update.message.reply_text(content[i:i+4000])

# === Универсальный обработчик ===
async def unified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_data = context.user_data

    # Кнопка возврата в меню
    if text == "🔁 Старт":
        await start(update, context)
        return

    # Запрос количества номеров на страницу
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
                "trailer": TRAILER_FILE
            }
            filename = file_map[category]
            with open(filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i in range(0, len(lines), page_size):
                chunk = "".join(lines[i:i + page_size])
                await update.message.reply_text(chunk)
        except ValueError:
            user_data["expecting_page_size"] = False
            await update.message.reply_text(
                "❗ Введите число от 1 до 100. Или нажмите 🔁 Старт для возврата в меню."
            )
        return

    # Запуск поиска по буквам
    elif text == "🔠 Поиск номера по буквам":
        user_data["expecting_letter_search"] = True
        await update.message.reply_text("Введите буквы для поиска (например, МК):")
        return

    # Обработка поиска по буквам
    elif user_data.get("expecting_letter_search"):
        query = ru_to_lat(text.upper())
        user_data["expecting_letter_search"] = False

        try:
            sheet_data = SHEET.get_all_values()
        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")
            await update.message.reply_text("❗ Ошибка при подключении к таблице.")
            return

        results = []
        for row in sheet_data:
            raw = row[0]
            letters = ru_to_lat("".join(re.findall(r"[А-ЯA-Z]+", raw.upper())))
            if query in letters:
                results.append(raw)
        reply = "\n".join(results) if results else "❗ Номеров с такими буквами не найдено."
        await update.message.reply_text(reply)
        return

    # Запуск поиска по цифрам
    elif text == "🔍 Поиск номера по цифрам":
        await update.message.reply_text("Введите последние цифры номера для поиска (например, 777):")
        user_data["expecting_digit_search"] = True
        return

    # Обработка поиска по цифрам
    elif user_data.get("expecting_digit_search"):
        digits = text
        user_data["expecting_digit_search"] = False

        try:
            sheet_data = SHEET.get_all_values()
        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")
            await update.message.reply_text("❗ Ошибка при подключении к таблице.")
            return

        results = [row[0] for row in sheet_data if digits in row[0]]
        reply = "\n".join(results) if results else "❗ Номеров с такими цифрами не найдено."
        await update.message.reply_text(reply)
        return

    # Обработка кнопок с файлами
    elif text in {"🏍 Мото номера", "🚛 Прицеп номера", "📍 Москва все номера", "📍 Московская обл. все номера"}:
        category_map = {
            "🚛 Прицеп номера": "trailer",
            "📍 Москва все номера": "moscow",
            "📍 Московская обл. все номера": "mosreg",
            "🏍 Мото номера": "moto"
        }
        if text == "🏍 Мото номера":
            await send_full_file(update, context, MOTO_FILE)
        else:
            category = category_map[text]
            user_data["expecting_page_size"] = True
            user_data["selected_category"] = category
            await update.message.reply_text("Сколько номеров показать на странице? (например, 30)")
        return

    # Услуги
    elif text == "🛠 Наши услуги":
        await update.message.reply_text(
            "📌 Наши услуги:\n"
            "- Дубликат номеров\n"
            "- Постановка на учет\n"
            "- Продажа красивых номеров\n"
            "- Страхование"
        )
        return

    # Контакты
    elif text == "📞 Наш адрес и контакты":
        await update.message.reply_text(
            "🏢 Адрес: улица Твардовского, 8к5с1, Москва\n"
            "📍 [Открыть в Яндекс.Навигаторе](https://yandex.ru/navi/?ol=geo&text=%D1%83%D0%BB%D0%B8%D1%86%D0%B0%20%D0%A2%D0%B2%D0%B0%D1%80%D0%B4%D0%BE%D0%B2%D1%81%D0%BA%D0%BE%D0%B3%D0%BE,%208%D0%BA5%D1%811&sll=37.388268,55.792574)\n"
            "📞 [Позвонить: +7 (966) 000-26-26](tel:+79660002626)\n"
            "💬 Telegram: @blatznak77\n"
            "📲 [Написать в WhatsApp](https://wa.me/79660002626)",
            parse_mode="Markdown"
        )
        return

    # Неизвестный ввод — обработка как цифры
    else:
        digits = text
        try:
            sheet_data = SHEET.get_all_values()
        except Exception as e:
            logger.error(f"Ошибка подключения к Google Sheets: {e}")
            await update.message.reply_text("❗ Ошибка при подключении к таблице.")
            return

        results = [row[0] for row in sheet_data if digits in row[0]]
        reply = "\n".join(results) if results else "❗ Номеров с такими данными не найдено."
        await update.message.reply_text(reply)

# === Запуск бота ===
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unified_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
