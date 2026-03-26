import os
import asyncio
import logging
import time
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

# ---------- Загрузка молитв ----------
def load_prayer(file_name):
    with open(f"data/{file_name}", "r", encoding="utf-8") as f:
        return f.read()

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

# ---------- Кэш для чтений дня (на 1 час) ----------
readings_cache = {}
CACHE_TTL = 3600

async def fetch_readings_from_url(url: str) -> str:
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    logging.error(f"Ошибка HTTP {resp.status} для {url}")
                    return "Не удалось загрузить страницу."
                html = await resp.text()
        except asyncio.TimeoutError:
            logging.error(f"Таймаут при запросе к {url}")
            return "Сервер не отвечает. Попробуйте позже."
        except Exception as e:
            logging.error(f"Ошибка запроса: {e}")
            return "Не удалось загрузить страницу."

    soup = BeautifulSoup(html, 'lxml')
    reading_blocks = soup.find_all('div', class_='reading')
    if not reading_blocks:
        reading_blocks = soup.find_all('div', class_='bible-reading')
    if not reading_blocks:
        logging.warning(f"Не найдены блоки чтений на странице {url}")
        return "Не удалось найти тексты чтений на странице."

    result_parts = []
    for block in reading_blocks:
        title_tag = block.find('h3') or block.find('div', class_='reading-title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            result_parts.append(f"*{title}*")
        else:
            result_parts.append("*Чтение*")
        text_block = block.find('div', class_='reading-text') or block
        paragraphs = text_block.find_all('p')
        if paragraphs:
            text = "\n\n".join(p.get_text(strip=True) for p in paragraphs)
        else:
            text = text_block.get_text(strip=True)
        result_parts.append(text)
        result_parts.append("")

    full_text = "\n\n".join(result_parts).strip()
    if not full_text:
        return "Не удалось извлечь тексты чтений."

    if len(full_text) > 4000:
        full_text = full_text[:4000] + "\n\n...(текст сокращён, полную версию смотрите по ссылке)"
    return full_text

async def get_reading_text(date_str: str) -> str:
    if date_str in readings_cache:
        cached_text, timestamp = readings_cache[date_str]
        if time.time() - timestamp < CACHE_TTL:
            return cached_text
    url = f"https://azbyka.ru/biblia/days/{date_str}"
    text = await fetch_readings_from_url(url)
    readings_cache[date_str] = (text, time.time())
    return text

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🛐 МОЛИТВОСЛОВ\nВыберите раздел:",
        reply_markup=main_menu_keyboard
    )

@dp.callback_query(lambda c: c.data == "reading")
async def reading_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    date_str = datetime.now().strftime("%Y-%m-%d")
    msg = await callback_query.message.edit_text("Загружаю чтения дня...")
    try:
        text = await get_reading_text(date_str)
    except Exception:
        logging.exception("Ошибка при загрузке чтений")
        text = "Произошла ошибка при загрузке. Попробуйте позже."
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
    back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="prayers")]])
    if len(text) > 4000:
        await callback_query.message.edit_text(text[:4000] + "...", parse_mode="Markdown", reply_markup=back)
        await callback_query.message.answer(text[4000:], parse_mode="Markdown")
    else:
        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back)

@dp.callback_query(lambda c: c.data == "evening_prayers")
async def evening_prayers_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = f"🙏 *Вечерние молитвы*\n\n{evening_prayers}"
    back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="prayers")]])
    if len(text) > 4000:
        await callback_query.message.edit_text(text[:4000] + "...", parse_mode="Markdown", reply_markup=back)
        await callback_query.message.answer(text[4000:], parse_mode="Markdown")
    else:
        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back)

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "🛐 МОЛИТВОСЛОВ\nВыберите раздел:",
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
        "⚠️ *Важно:* Пожертвования направляются напрямую храмам. Мы не принимаем и не обрабатываем платежи."
    )
    back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=back)

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
    back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
