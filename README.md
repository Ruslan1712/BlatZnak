# Telegram Bot — Deploy to Render

## 🔧 Как развернуть

1. Залей этот репозиторий на GitHub
2. Перейди на https://render.com и нажми **New → Web Service**
3. Подключи репозиторий, выбери Python окружение
4. Настрой:

- Build command: `pip install -r requirements.txt`
- Start command: `python bot.py`
- Environment:
    - BOT_TOKEN = (твой токен от BotFather)
    - GOOGLE_JSON = blat-znak-2f081fa17909.json

5. В секции Secret Files:
    - Добавь файл `blat-znak-2f081fa17909.json`
    - Назови его **blat-znak-2f081fa17909.json**

6. Нажми Deploy ✅
