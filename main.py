import os
import asyncio
import logging
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота из переменной окружения (установим на Railway)
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Клавиатура ----------
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📖 Чтения дня")],
        [KeyboardButton(text="🙏 Молитвы")],
        [KeyboardButton(text="📅 Календарь")],
        [KeyboardButton(text="🏛️ Храмы")],
        [KeyboardButton(text="💝 Поддержать")],
    ],
    resize_keyboard=True
)

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "Добро пожаловать в «Спутник верующего»!\n\n"
        "Я помогаю православным христианам:\n"
        "• Читать жития святых и Священное Писание\n"
        "• Следить за церковным календарём\n"
        "• Находить молитвы\n"
        "• Поддерживать храмы\n\n"
        "Выберите раздел в меню:",
        reply_markup=keyboard
    )

@dp.message(lambda m: m.text == "📖 Чтения дня")
async def reading_of_day(message: types.Message):
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://azbyka.ru/days/api/saints/{today}/group.json"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
        except Exception as e:
            logging.error(f"Ошибка при запросе к API: {e}")
            await message.answer("Не удалось загрузить данные. Попробуйте позже.")
            return

    if data and len(data) > 0:
        saint = data[0]
        name = saint.get("name", "Святой")
        life = saint.get("life", "Описание временно недоступно")
        # Обрезаем длинный текст
        if len(life) > 1500:
            life = life[:1500] + "..."
        text = f"📖 *{name}*\n\n{life}"
    else:
        text = "Данные о святом сегодня недоступны. Загляните позже."

    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda m: m.text == "🙏 Молитвы")
async def prayers(message: types.Message):
    text = (
        "🙏 *Утренние молитвы*\n\n"
        "Господи, благослови день сей...\n\n"
        "🙏 *Вечерние молитвы*\n\n"
        "Господи, прости согрешения мои...\n\n"
        "📖 *Полный текст молитв* будет добавлен позже.\n"
        "Вы можете поделиться своими пожеланиями в комментариях к боту."
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda m: m.text == "📅 Календарь")
async def calendar(message: types.Message):
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://azbyka.ru/days/api/presentations/{today}.json"

    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
        except Exception:
            await message.answer("Не удалось загрузить календарь. Попробуйте позже.")
            return

    if data and "presentations" in data and data["presentations"]:
        html = data["presentations"][0]
        # Убираем HTML‑теги для упрощённого отображения
        import re
        text = re.sub(r'<[^>]+>', '', html)
        if len(text) > 1000:
            text = text[:1000] + "..."
    else:
        text = "Информация о праздниках сегодня недоступна."

    await message.answer(f"📅 *{today}*\n\n{text}", parse_mode="Markdown")

@dp.message(lambda m: m.text == "🏛️ Храмы")
async def temples(message: types.Message):
    text = (
        "🏛️ *Храмы, нуждающиеся в поддержке:*\n\n"
        "**Храм Николая Чудотворца**\n"
        "Сбор на реставрацию иконостаса.\n"
        "[Помочь](https://example.com/temple1)\n\n"
        "**Свято-Троицкий монастырь**\n"
        "Сбор на строительство воскресной школы.\n"
        "[Помочь](https://example.com/temple2)\n\n"
        "⚠️ *Важно:* Пожертвования направляются напрямую храмам. "
        "Мы не принимаем и не обрабатываем платежи."
    )
    await message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

@dp.message(lambda m: m.text == "💝 Поддержать")
async def support_developer(message: types.Message):
    text = (
        "💝 *Поддержка разработчика*\n\n"
        "Этот бот создаётся и поддерживается добровольцем. "
        "Если вы хотите помочь проекту развиваться — "
        "вы можете совершить добровольное дарение.\n\n"
        "Ссылка: https://donate.example.com\n\n"
        "Все средства пойдут на развитие бота, хостинг и обновления. "
        "Спасибо за вашу поддержку!"
    )
    await message.answer(text, parse_mode="Markdown")

# ---------- Запуск бота ----------
async def main():
    # Используем polling (проще для Railway)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
