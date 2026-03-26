import os
import asyncio
import logging
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота из переменной окружения
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Inline-клавиатура (главное меню) ----------
main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📖 Чтения дня", callback_data="reading")],
        [InlineKeyboardButton(text="🙏 Молитвы", callback_data="prayers")],
        [InlineKeyboardButton(text="📅 Календарь", callback_data="calendar")],
        [InlineKeyboardButton(text="🏛️ Храмы", callback_data="temples")],
        [InlineKeyboardButton(text="💝 Поддержать", callback_data="support")],
    ]
)

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    # Приветственное сообщение
    welcome_text = (
        "Добро пожаловать в «Спутник верующего»!\n\n"
        "Я помогаю православным христианам:\n"
        "• Читать жития святых и Священное Писание\n"
        "• Следить за церковным календарём\n"
        "• Находить молитвы\n"
        "• Поддерживать храмы"
    )
    await message.answer(welcome_text)
    
    # Отдельное сообщение с главным меню
    await message.answer(
        "🛐 Спутник верующего\nВыберите раздел:",
        reply_markup=main_menu_keyboard
    )

@dp.callback_query(lambda c: c.data == "reading")
async def reading_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()  # убираем "часики"
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://azbyka.ru/days/api/saints/{today}/group.json"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
        except Exception as e:
            logging.error(f"Ошибка при запросе к API: {e}")
            await callback_query.message.answer("Не удалось загрузить данные. Попробуйте позже.")
            return

    if data and len(data) > 0:
        saint = data[0]
        name = saint.get("name", "Святой")
        life = saint.get("life", "Описание временно недоступно")
        if len(life) > 1500:
            life = life[:1500] + "..."
        text = f"📖 *{name}*\n\n{life}"
    else:
        text = "Данные о святом сегодня недоступны. Загляните позже."
    
    await callback_query.message.answer(text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "prayers")
async def prayers_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    # Пока статические тексты
    text = (
        "🙏 *Утренние молитвы*\n\n"
        "Господи, благослови день сей…\n\n"
        "🙏 *Вечерние молитвы*\n\n"
        "Господи, прости согрешения мои…\n\n"
        "📖 *Полный текст молитв* будет добавлен позже.\n"
        "Вы можете поделиться своими пожеланиями в комментариях к боту."
    )
    await callback_query.message.answer(text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "calendar")
async def calendar_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://azbyka.ru/days/api/presentations/{today}.json"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                data = await resp.json()
        except Exception:
            await callback_query.message.answer("Не удалось загрузить календарь. Попробуйте позже.")
            return

    if data and "presentations" in data and data["presentations"]:
        html = data["presentations"][0]
        import re
        text = re.sub(r'<[^>]+>', '', html)
        if len(text) > 1000:
            text = text[:1000] + "..."
    else:
        text = "Информация о праздниках сегодня недоступна."
    
    await callback_query.message.answer(f"📅 *{today}*\n\n{text}", parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "temples")
async def temples_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
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
    await callback_query.message.answer(text, parse_mode="Markdown", disable_web_page_preview=True)

@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = (
        "💝 *Поддержка разработчика*\n\n"
        "Этот бот создаётся и поддерживается добровольцем. "
        "Если вы хотите помочь проекту развиваться — "
        "вы можете совершить добровольное дарение.\n\n"
        "Ссылка: https://donate.example.com\n\n"
        "Все средства пойдут на развитие бота, хостинг и обновления. "
        "Спасибо за вашу поддержку!"
    )
    await callback_query.message.answer(text, parse_mode="Markdown")

from bs4 import BeautifulSoup

async def fetch_prayers():
    """
    Возвращает словарь с утренними и вечерними молитвами.
    """
    url_morning = "https://azbyka.ru/molitvoslov/utrennie-molitvy.html"
    url_evening = "https://azbyka.ru/molitvoslov/molitvy-na-son-gryadushhim.html"
    
    async with aiohttp.ClientSession() as session:
        # Утренние молитвы
        async with session.get(url_morning) as resp:
            morning_html = await resp.text()
        # Вечерние молитвы
        async with session.get(url_evening) as resp:
            evening_html = await resp.text()
    
    morning_soup = BeautifulSoup(morning_html, 'lxml')
    evening_soup = BeautifulSoup(evening_html, 'lxml')
    
    # Ищем контент внутри тега <div class="content">
    morning_div = morning_soup.find('div', class_='content')
    evening_div = evening_soup.find('div', class_='content')
    
    # Извлекаем текст (можно использовать .get_text() для простоты)
    morning_text = morning_div.get_text(separator='\n', strip=True) if morning_div else "Не удалось загрузить утренние молитвы"
    evening_text = evening_div.get_text(separator='\n', strip=True) if evening_div else "Не удалось загрузить вечерние молитвы"
    
    # Обрезаем слишком длинные тексты (Telegram имеет ограничение 4096 символов)
    if len(morning_text) > 2000:
        morning_text = morning_text[:2000] + "...\n(сокращено)"
    if len(evening_text) > 2000:
        evening_text = evening_text[:2000] + "...\n(сокращено)"
    
    return {
        "morning": morning_text,
        "evening": evening_text
    }

# ---------- Запуск бота ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
