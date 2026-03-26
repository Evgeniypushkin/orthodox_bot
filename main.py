import os
import asyncio
import logging
from datetime import datetime

import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Inline-клавиатура ----------
main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📖 Чтения дня", callback_data="reading")],
        [InlineKeyboardButton(text="🙏 Молитвы", callback_data="prayers")],
        [InlineKeyboardButton(text="📅 Календарь", callback_data="calendar")],
        [InlineKeyboardButton(text="🏛️ Храмы", callback_data="temples")],
        [InlineKeyboardButton(text="💝 Поддержать", callback_data="support")],
    ]
)

# ---------- Парсинг молитв ----------
async def fetch_prayers():
    url_morning = "https://azbyka.ru/molitvoslov/utrennie-molitvy.html"
    url_evening = "https://azbyka.ru/molitvoslov/molitvy-na-son-gryadushhim.html"
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url_morning) as resp:
            morning_html = await resp.text()
        async with session.get(url_evening) as resp:
            evening_html = await resp.text()
    
    morning_soup = BeautifulSoup(morning_html, 'lxml')
    evening_soup = BeautifulSoup(evening_html, 'lxml')
    
    # Пробуем разные возможные селекторы
    morning_div = morning_soup.find('div', class_='text') or morning_soup.find('div', class_='content')
    evening_div = evening_soup.find('div', class_='text') or evening_soup.find('div', class_='content')
    
    if not morning_div:
        # Если не нашли контент — загружаем текст из другого источника
        morning_text = "Не удалось загрузить утренние молитвы. Пожалуйста, зайдите позже."
    else:
        # Удаляем лишние элементы (например, рекламу, ссылки)
        for tag in morning_div.find_all(['script', 'style', 'iframe', 'ins']):
            tag.decompose()
        morning_text = morning_div.get_text(separator='\n', strip=True)
    
    if not evening_div:
        evening_text = "Не удалось загрузить вечерние молитвы. Пожалуйста, зайдите позже."
    else:
        for tag in evening_div.find_all(['script', 'style', 'iframe', 'ins']):
            tag.decompose()
        evening_text = evening_div.get_text(separator='\n', strip=True)
    
    # Обрезаем слишком длинные тексты
    if len(morning_text) > 2000:
        morning_text = morning_text[:2000] + "...\n(сокращено)"
    if len(evening_text) > 2000:
        evening_text = evening_text[:2000] + "...\n(сокращено)"
    
    return {"morning": morning_text, "evening": evening_text}

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    welcome_text = (
        "Добро пожаловать в «Спутник верующего»!\n\n"
        "Я помогаю православным христианам:\n"
        "• Читать жития святых и Священное Писание\n"
        "• Следить за церковным календарём\n"
        "• Находить молитвы\n"
        "• Поддерживать храмы"
    )
    await message.answer(welcome_text)
    await message.answer(
        "🛐 Спутник верующего",
        reply_markup=main_menu_keyboard
    )

@dp.callback_query(lambda c: c.data == "reading")
async def reading_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://azbyka.ru/days/api/saints/{today}/group.json"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logging.error(f"API вернул статус {resp.status}")
                    await callback_query.message.answer("Сервер временно недоступен. Попробуйте позже.")
                    return
                data = await resp.json()
                logging.info(f"Получены данные: {data}")
        except Exception as e:
            logging.error(f"Ошибка при запросе к API: {e}")
            await callback_query.message.answer("Не удалось загрузить данные. Попробуйте позже.")
            return

    if data and isinstance(data, list) and len(data) > 0:
        # Берём первого святого в списке
        saint = data[0]
        name = saint.get("name", "Святой")
        life = saint.get("life", "Описание временно недоступно")
        # Иногда в жизни могут быть HTML-теги — убираем
        import re
        life = re.sub(r'<[^>]+>', '', life)
        if len(life) > 1500:
            life = life[:1500] + "..."
        text = f"📖 *{name}*\n\n{life}"
    else:
        # Если святых нет — пробуем вывести краткую информацию о дне
        text = "Сегодня нет житий святых. Возможно, это праздник. Попробуйте раздел «Календарь»."
    
    await callback_query.message.answer(text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "prayers")
async def prayers_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    msg = await callback_query.message.answer("🙏 Загружаю молитвы, подождите...")
    prayers = await fetch_prayers()
    text = (
        f"🙏 *Утренние молитвы*\n\n{prayers['morning']}\n\n"
        f"🙏 *Вечерние молитвы*\n\n{prayers['evening']}"
    )
    await msg.edit_text(text, parse_mode="Markdown")

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

@dp.callback_query(lambda c: c.data == "https://t.me/evgeniy_pushkin")
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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
