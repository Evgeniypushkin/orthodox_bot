import os
import asyncio
import logging
import json
import re
from datetime import datetime

import aiohttp
from bs4 import BeautifulSoup
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Загрузка данных ----------
def load_readings():
    with open("data/readings_2026_2027.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_calendar():
    with open("data/church_calendar_2026_2027.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_prayer(file_name):
    with open(f"data/{file_name}", "r", encoding="utf-8") as f:
        return f.read()

# readings_data = load_readings()   # можно закомментировать
calendar_data = load_calendar()
morning_prayers = load_prayer("morning_prayers.txt")
evening_prayers = load_prayer("evening_prayers.txt")

# ---------- Клавиатуры ----------
main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📖 Чтения дня", callback_data="reading")],
        [InlineKeyboardButton(text="🙏 Молитвы", callback_data="prayers")],
        [InlineKeyboardButton(text="🏛️ Храмы", callback_data="temples")],
        [InlineKeyboardButton(text="💝 Поддержать", callback_data="support")],
    ]
)

prayers_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🙏 Утренние молитвы", callback_data="morning_prayers")],
        [InlineKeyboardButton(text="🌙 Вечерние молитвы", callback_data="evening_prayers")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ]
)

# ---------- Парсинг страницы azbyka.ru ----------
async def fetch_readings_from_url(url: str) -> str:
    """
    Загружает страницу с azbyka.ru и извлекает тексты
    всех апостольских и евангельских чтений.
    Возвращает отформатированный текст.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status != 200:
                    logging.error(f"Ошибка HTTP {resp.status} для {url}")
                    return "Не удалось загрузить страницу."
                html = await resp.text()
        except Exception as e:
            logging.error(f"Ошибка запроса: {e}")
            return "Не удалось загрузить страницу."

    soup = BeautifulSoup(html, 'lxml')
    # Ищем все блоки с чтениями – они обычно в <div class="reading">
    reading_blocks = soup.find_all('div', class_='reading')
    if not reading_blocks:
        # альтернативный вариант: блоки с классом "bible-reading"
        reading_blocks = soup.find_all('div', class_='bible-reading')

    if not reading_blocks:
        return "Не удалось найти тексты чтений на странице."

    result_parts = []
    for block in reading_blocks:
        # Ищем заголовок (обычно <h3> или <div class="reading-title">)
        title_tag = block.find('h3') or block.find('div', class_='reading-title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            result_parts.append(f"*{title}*")
        else:
            result_parts.append("*Чтение*")
        # Ищем текст чтения (обычно в <p> или в <div class="reading-text">)
        text_block = block.find('div', class_='reading-text') or block
        paragraphs = text_block.find_all('p')
        if paragraphs:
            text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            text = text_block.get_text(strip=True)
        result_parts.append(text)
        result_parts.append("")  # разделитель

    if not result_parts:
        return "Не удалось извлечь тексты."

    # Объединяем всё
    full_text = "\n\n".join(result_parts)
    # Обрезаем, если очень длинное
    if len(full_text) > 4000:
        # Оставляем первые 4000 символов и добавляем предупреждение
        full_text = full_text[:4000] + "\n\n...(текст сокращён, полную версию смотрите по ссылке)"
    return full_text

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🛐 Спутник верующего\nВыберите раздел:",
        reply_markup=main_menu_keyboard
    )

@dp.callback_query(lambda c: c.data == "reading")
async def reading_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    today = datetime.now()
    date_str = today.strftime("%Y-%m-%d")
    # Формируем ссылку самостоятельно
    source_url = f"https://azbyka.ru/biblia/days/{date_str}"
    
    # Показываем "Загрузка..."
    msg = await callback_query.message.edit_text("Загружаю чтения дня...")
    
    text = await fetch_readings_from_url(source_url)
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    
    if len(text) > 4000:
        await msg.delete()
        await callback_query.message.answer(text[:4000], parse_mode="Markdown", reply_markup=back_keyboard)
        await callback_query.message.answer(text[4000:], parse_mode="Markdown")
    else:
        await msg.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard)

@dp.callback_query(lambda c: c.data == "prayers")
async def prayers_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "Выберите молитвы:",
        reply_markup=prayers_menu_keyboard
    )

@dp.callback_query(lambda c: c.data == "morning_prayers")
async def morning_prayers_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = f"🙏 *Утренние молитвы*\n\n{morning_prayers}"
    back_to_prayers = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="prayers")]])
    if len(text) > 4000:
        await callback_query.message.edit_text(text[:4000] + "...", parse_mode="Markdown", reply_markup=back_to_prayers)
        await callback_query.message.answer(text[4000:], parse_mode="Markdown")
    else:
        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_prayers)

@dp.callback_query(lambda c: c.data == "evening_prayers")
async def evening_prayers_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = f"🙏 *Вечерние молитвы*\n\n{evening_prayers}"
    back_to_prayers = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="prayers")]])
    if len(text) > 4000:
        await callback_query.message.edit_text(text[:4000] + "...", parse_mode="Markdown", reply_markup=back_to_prayers)
        await callback_query.message.answer(text[4000:], parse_mode="Markdown")
    else:
        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_prayers)

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "🛐 Спутник верующего\nВыберите раздел:",
        reply_markup=main_menu_keyboard
    )

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
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=back_keyboard)

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
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
