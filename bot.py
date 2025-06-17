import os
import logging
import csv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import re

# === Настройки ===
BOT_TOKEN = os.getenv("BOT_TOKEN")
CSV_FILE = "номера.csv"  # CSV файл с номерами
DEFAULT_PAGE_SIZE = 30

def ru_to_lat(text):
    """Преобразует русские буквы в латинские аналоги"""
    repl = str.maketrans("АВЕКМНОРСТУХ", "ABEKMHOPCTYX")
    return text.translate(repl)

def extract_letters_from_number(number):
    """Извлекает только буквы из номера и преобразует в заглавные"""
    letters = re.findall(r"[А-ЯA-Z]+", number.upper())
    letters_only = "".join(letters)
    return ru_to_lat(letters_only)

def load_numbers_from_csv():
    """Загружает номера из CSV файла"""
    numbers_data = []
    try:
        if not os.path.exists(CSV_FILE):
            logger.error(f"CSV файл не найден: {CSV_FILE}")
            return []
        
        with open(CSV_FILE, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            next(csv_reader, None)  # Пропускаем заголовок
            
            for row in csv_reader:
                if len(row) >= 4:
                    numbers_data.append({
                        'number': row[0].strip(),
                        'region': row[1].strip(),
                        'price': row[2].strip(),
                        'comment': row[3].strip()
                    })
        
        logger.info(f"Загружено {len(numbers_data)} номеров из CSV файла")
        return numbers_data
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке CSV файла: {e}")
        return []

# Глобальная переменная для хранения данных
NUMBERS_DATA = []

def search_numbers_by_letters(search_query, max_results=50):
    """Поиск номеров по буквам"""
    try:
        query = ru_to_lat(search_query.upper().strip())
        if not query:
            return []
        
        results = []
        for data in NUMBERS_DATA:
            number_letters = extract_letters_from_number(data['number'])
            if query in number_letters:
                result_line = f"{data['number']}"
                if data['region'] and data['region'] != "None":
                    result_line += f" (регион {data['region']})"
                if data['price'] and data['price'] != "None":
                    result_line += f" - {data['price']}₽"
                if data['comment'] and data['comment'] != "None":
                    result_line += f" {data['comment']}"
                
                results.append(result_line)
                if len(results) >= max_results:
                    break
        
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске по буквам: {e}")
        return []

def search_numbers_by_digits(search_query, max_results=50):
    """Поиск номеров по цифрам"""
    try:
        query = search_query.strip()
        if not query:
            return []
        
        results = []
        for data in NUMBERS_DATA:
            full_number = f"{data['number']}{data['region']}"
            if query in full_number:
                result_line = f"{data['number']}"
                if data['region'] and data['region'] != "None":
                    result_line += f" (регион {data['region']})"
                if data['price'] and data['price'] != "None":
                    result_line += f" - {data['price']}₽"
                if data['comment'] and data['comment'] != "None":
                    result_line += f" {data['comment']}"
                
                results.append(result_line)
                if len(results) >= max_results:
                    break
        
        return results
    except Exception as e:
        logger.error(f"Ошибка при поиске по цифрам: {e}")
        return []

# === Логирование ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === /start ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = ReplyKeyboardMarkup([
        ["🔁 Старт"],
        ["\U0001F50D Поиск номера по цифрам (авто)", "\U0001F520 Поиск номера по буквам"],
        ["\U0001F6E0 Наши услуги", "\U0001F4DE Наш адрес и контакты"]
    ], resize_keyboard=True)

    await update.message.reply_text(
        "Добро пожаловать в компанию BlatZnak!\n"
        "Мы занимаемся продажей гос номеров и постановкой на учет.\n"
        "Выберите действие:",
        reply_markup=keyboard
    )

# === Универсальный обработчик ===
async def unified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_data = context.user_data

    if text == "🔁 Старт":
        await start(update, context)
        return

    elif text == "\U0001F520 Поиск номера по буквам":
        user_data["expecting_letter_search"] = True
        await update.message.reply_text("Введите буквы для поиска (например, СС, АА, МК):")
        return

    elif user_data.get("expecting_letter_search"):
        user_data["expecting_letter_search"] = False
        results = search_numbers_by_letters(text, max_results=50)
        
        if results:
            reply = f"🔍 Найдено номеров с буквами '{text.upper()}': {len(results)}\n\n"
            reply += "\n".join(results)
        else:
            reply = f"❌ Номеров с буквами '{text.upper()}' не найдено."
        
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])
        return

    elif text == "\U0001F50D Поиск номера по цифрам (авто)":
        user_data["expecting_digit_search"] = True
        await update.message.reply_text("Отправьте цифры номера для поиска (например, 777, 123):")
        return

    elif user_data.get("expecting_digit_search"):
        user_data["expecting_digit_search"] = False
        results = search_numbers_by_digits(text, max_results=50)
        
        if results:
            reply = f"🔍 Найдено номеров с цифрами '{text}': {len(results)}\n\n"
            reply += "\n".join(results)
        else:
            reply = f"❌ Номеров с цифрами '{text}' не найдено."
        
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])
        return

    elif text == "\U0001F6E0 Наши услуги":
        await update.message.reply_text(
            "\U0001F4CC Наши услуги:\n"
            "- Дубликат номеров\n"
            "- Постановка автомобиля на учет\n"
            "- Продажа красивых номеров\n"
            "- Страхование"
        )

    elif text == "\U0001F4DE Наш адрес и контакты":
        await update.message.reply_text(
            "\U0001F3E2 Адрес: улица Твардовского, 8к5с1, Москва\n"
            "\U0001F4CD [Открыть в Яндекс.Навигаторе](https://yandex.ru/navi/?ol=geo&text=%D1%83%D0%BB%D0%B8%D1%86%D0%B0%20%D0%A2%D0%B2%D0%B0%D1%80%D0%B4%D0%BE%D0%B2%D1%81%D0%BA%D0%BE%D0%B3%D0%BE,%208%D0%BA5%D1%811&sll=37.388268,55.792574)\n"
            "\u260E [Позвонить: +7 (966) 000-26-26](tel:+79660002626)\n"
            "\U0001F4AC Telegram: @blatznak77\n"
            "\U0001F4F1 [Написать в WhatsApp](https://wa.me/79660002626)",
            parse_mode="Markdown"
        )
    else:
        # Поиск по цифрам по умолчанию
        results = search_numbers_by_digits(text, max_results=50)
        
        if results:
            reply = f"🔍 Найдено номеров с '{text}': {len(results)}\n\n"
            reply += "\n".join(results)
        else:
            reply = f"❌ Номеров с '{text}' не найдено."
        
        for i in range(0, len(reply), 4000):
            await update.message.reply_text(reply[i:i+4000])

# === Main ===
def main():
    global NUMBERS_DATA
    
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN не установлен в переменных окружения!")
        return
    
    # Загружаем данные о номерах при запуске
    logger.info("Загрузка данных о номерах...")
    NUMBERS_DATA = load_numbers_from_csv()
    
    if not NUMBERS_DATA:
        logger.warning("Данные о номерах не загружены! Проверьте наличие CSV файла.")
    
    logger.info("Запуск бота...")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unified_handler))
    
    logger.info("Бот запущен и готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()

