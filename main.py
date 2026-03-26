import os
import asyncio
import logging
import time
from datetime import datetime

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

async def fetch_readings_from_url(date_str: str) -> str:
    url = f"https://azbyka.ru/biblia/days/{date_str}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return f"Не удалось загрузить страницу. Ссылка: {url}"
                html = await resp.text()
        except Exception:
            return f"Ошибка загрузки. Ссылка: {url}"

    soup = BeautifulSoup(html, 'lxml')

    # Находим все заголовки чтений
    title_divs = soup.find_all('div', class_='days_book-title')
    if not title_divs:
        return f"Не найдены заголовки чтений. Ссылка: {url}"

    result_parts = []
    for title_div in title_divs:
        title_text = title_div.get_text(strip=True)
        if not title_text:
            continue

        # Ищем следующий div с классом tbl-content
        content_div = title_div.find_next_sibling('div', class_='tbl-content')
        if not content_div:
            continue

        # Удаляем лишние элементы
        for tag in content_div.find_all(['div', 'span', 'ul'], class_=[
            'parallel', 'number', 'numbers-header', 'column-header', 'langs', 'add-lang', 'replace-lang__panel'
        ]):
            tag.decompose()

        # Удаляем все элементы с class, содержащим 'number-header'
        for tag in content_div.find_all(class_=re.compile(r'number-header')):
            tag.decompose()

        # Удаляем все элементы с атрибутом data-line (номера стихов)
        for tag in content_div.find_all(attrs={"data-line": True}):
            tag.decompose()

        # Получаем текст, заменяя <br> на переносы
        for br in content_div.find_all('br'):
            br.replace_with('\n')
        content_text = content_div.get_text(separator='\n', strip=True)

        # Убираем множественные переносы
        content_text = re.sub(r'\n\s*\n', '\n\n', content_text)

        if content_text:
            result_parts.append(f"*{title_text}*")
            result_parts.append(content_text)

    if not result_parts:
        return f"Не удалось извлечь тексты чтений. Ссылка: {url}"

    full_text = "\n\n".join(result_parts)
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
    today = datetime.now().strftime("%Y-%m-%d")
    url = f"https://azbyka.ru/biblia/days/{today}"
    text = (
        f"📖 *Чтения дня на {today}*\n\n"
        f"Вы можете прочитать Апостол и Евангелие на сегодня по ссылке:\n"
        f"{url}\n\n"
        f"Также на этой странице доступны ветхозаветные чтения, если они положены по уставу."
    )
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=back_keyboard)

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
