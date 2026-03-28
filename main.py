import re
import os
import asyncio
import logging
import json
import random
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bs4 import BeautifulSoup

def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Удаляем все теги, кроме <a>
    for tag in soup.find_all():
        if tag.name != 'a':
            tag.unwrap()
    return str(soup)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ---------- Загрузка данных ----------
def load_prayers():
    with open("data/prayers.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_confession():
    with open("data/confession.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_quotes():
    with open("data/quotes.json", "r", encoding="utf-8") as f:
        return json.load(f)

quotes = load_quotes()

def get_quote_of_day():
    today = datetime.now().strftime("%Y-%m-%d")
    # Используем дату как seed для воспроизводимости
    random.seed(today)
    index = random.randint(0, len(quotes)-1)
    return quotes[index]

def load_calendar():
    with open("data/church_calendar_2026_2027.json", "r", encoding="utf-8") as f:
        return json.load(f)

prayers_data = load_prayers()
confession_data = load_confession()
quotes = load_quotes()
calendar_data = load_calendar()

# ---------- Клавиатуры ----------
main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🙏 Молитвы", callback_data="prayers")],
        [InlineKeyboardButton(text="📅 Календарь", callback_data="calendar")],
        [InlineKeyboardButton(text="✨ Цитата дня", callback_data="quote")],
        [InlineKeyboardButton(text="📖 Чтения дня", callback_data="reading")],
        [InlineKeyboardButton(text="🙏 Подготовка к исповеди", callback_data="confession_prepare")],
        [InlineKeyboardButton(text="💰 Пожертвовать", callback_data="donate_menu")],
    ]
)

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🛐 МОЛИТВОСЛОВ\nГлавное меню:",
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

# ---------- Молитвы (уже есть, добавим функции, если ещё не) ----------
def get_prayers_menu():
    keyboard = []
    for cat in prayers_data["categories"]:
        keyboard.append([InlineKeyboardButton(text=cat["name"], callback_data=f"prayer_cat_{cat['id']}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_prayer_list(cat_id):
    for cat in prayers_data["categories"]:
        if cat["id"] == cat_id:
            keyboard = []
            for prayer in cat["prayers"]:
                keyboard.append([InlineKeyboardButton(text=prayer["title"], callback_data=f"prayer_{prayer['id']}")])
            keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="prayers")])
            return InlineKeyboardMarkup(inline_keyboard=keyboard)
    return None

def get_prayer_text(prayer_id):
    for cat in prayers_data["categories"]:
        for prayer in cat["prayers"]:
            if prayer["id"] == prayer_id:
                return prayer["text"]
    return "Молитва не найдена."

@dp.callback_query(lambda c: c.data == "prayers")
async def prayers_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    await callback_query.message.edit_text(
        "Выберите категорию молитв:",
        reply_markup=get_prayers_menu()
    )

@dp.callback_query(lambda c: c.data.startswith("prayer_cat_"))
async def prayer_category_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    cat_id = callback_query.data.split("_")[2]
    keyboard = get_prayer_list(cat_id)
    if keyboard:
        await callback_query.message.edit_text(
            "Выберите молитву:",
            reply_markup=keyboard
        )
    else:
        await callback_query.message.edit_text("Категория не найдена.")

@dp.callback_query(lambda c: c.data.startswith("prayer_"))
async def prayer_text_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    prayer_id = callback_query.data.split("_", 1)[1]
    cat_id = None
    prayer_title = ""
    for cat in prayers_data["categories"]:
        for prayer in cat["prayers"]:
            if prayer["id"] == prayer_id:
                cat_id = cat["id"]
                prayer_title = prayer["title"]
                break
        if cat_id:
            break
    text = get_prayer_text(prayer_id)
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data=f"prayer_cat_{cat_id}")]])
    await callback_query.message.edit_text(
        f"*{prayer_title}*\n\n{text}",
        parse_mode="Markdown",
        reply_markup=back_keyboard
    )

# ---------- Исповедь ----------
@dp.callback_query(lambda c: c.data == "confession_prepare")
async def confession_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Перечень грехов", callback_data="confession_sins")],
        [InlineKeyboardButton(text="📖 Как исповедоваться", callback_data="confession_instruction")],
        [InlineKeyboardButton(text="🙏 Молитвы перед исповедью", callback_data="confession_prayers")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    await callback_query.message.edit_text(
        "Подготовка к исповеди\n\n"
        "Выберите раздел, который поможет вам собраться перед таинством покаяния.",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data == "confession_sins")
async def confession_sins(callback_query: types.CallbackQuery):
    await callback_query.answer()
    keyboard = []
    for cat in confession_data["categories"]:
        keyboard.append([InlineKeyboardButton(text=cat["name"], callback_data=f"sins_cat_{cat['id']}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="confession_prepare")])
    await callback_query.message.edit_text(
        "Выберите категорию грехов для самоанализа:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@dp.callback_query(lambda c: c.data.startswith("sins_cat_"))
async def sins_category(callback_query: types.CallbackQuery):
    await callback_query.answer()
    cat_id = callback_query.data.split("_")[2]
    category = next((c for c in confession_data["categories"] if c["id"] == cat_id), None)
    if not category:
        await callback_query.message.edit_text("Категория не найдена.")
        return
    sins_text = "*" + category["name"] + "*\n\n"
    for sin in category["sins"]:
        sins_text += f"• {sin}\n"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="confession_sins")]])
    await callback_query.message.edit_text(sins_text, parse_mode="Markdown", reply_markup=back_keyboard)

@dp.callback_query(lambda c: c.data == "confession_instruction")
async def confession_instruction(callback_query: types.CallbackQuery):
    await callback_query.answer()
    instruction = confession_data["instruction"]
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="confession_prepare")]])
    await callback_query.message.edit_text(instruction, parse_mode="Markdown", reply_markup=back_keyboard)

@dp.callback_query(lambda c: c.data == "confession_prayers")
async def confession_prayers(callback_query: types.CallbackQuery):
    await callback_query.answer()
    prayers = confession_data["prayers"]
    if prayers:
        # Для простоты покажем первую молитву, можно сделать меню, если их несколько
        text = f"*{prayers[0]['title']}*\n\n{prayers[0]['text']}"
    else:
        text = "Молитвы не найдены."
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="confession_prepare")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard)

# ---------- Календарь ----------
def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all():
        if tag.name != 'a':
            tag.unwrap()
    text = str(soup)
    # Удаляем множественные переносы строк и лишние пробелы
    text = re.sub(r'\n\s*\n', '\n', text)
    text = text.strip()
    return text

@dp.callback_query(lambda c: c.data == "calendar")
async def calendar_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    today = datetime.now().strftime("%Y-%m-%d")
    try:
        with open("data/church_calendar_2026_2027.json", "r", encoding="utf-8") as f:
            cal = json.load(f)
    except FileNotFoundError:
        text = "📅 *Календарь*\n\nФайл календаря не найден. Пожалуйста, загрузите его в папку data."
        back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back)
        return
    except json.JSONDecodeError as e:
        text = f"📅 *Календарь*\n\nОшибка в файле календаря: {e}"
        back = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
        await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back)
        return

    if today not in cal:
        text = f"📅 *Календарь на {today}*\n\nДанные отсутствуют."
    else:
        data = cal[today]
        parts = [f"📅 *Календарь на {today}*"]
        if data.get("holidays"):
            parts.append("🕊️ *Праздники*")
            for h in data["holidays"]:
                cleaned = clean_html(h)
                if cleaned:
                    parts.append(cleaned)
        if data.get("fasts"):
            parts.append("🍽️ *Пост*")
            for f in data["fasts"]:
                cleaned = clean_html(f)
                if cleaned:
                    parts.append(cleaned)
        if data.get("saints"):
            parts.append("📖 *Святые дня*")
            for s in data["saints"]:
                cleaned = clean_html(s)
                if cleaned:
                    parts.append(cleaned)
        if data.get("services"):
            parts.append("⛪ *Службы*")
            for sv in data["services"]:
                cleaned = clean_html(sv)
                if cleaned:
                    parts.append(cleaned)
        if data.get("canons"):
            parts.append("📜 *Каноны и акафисты*")
            for c in data["canons"]:
                cleaned = clean_html(c)
                if cleaned:
                    parts.append(cleaned)
        if len(parts) == 1:
            text = f"📅 *Календарь на {today}*\n\nНа сегодня нет особых событий."
        else:
            text = "\n\n".join(parts)

    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    # Добавляем disable_web_page_preview=True
    await callback_query.message.edit_text(text, parse_mode="HTML", disable_web_page_preview=True, reply_markup=back_keyboard)

# ---------- Цитата дня ----------
@dp.callback_query(lambda c: c.data == "quote")
async def quote_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    quote = get_quote_of_day()
    text = f"✨ *Цитата дня*\n\n{quote}"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard)

@dp.callback_query(lambda c: c.data == "donate_menu")
async def donate_menu(callback_query: types.CallbackQuery):
    await callback_query.answer()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏛️ Помощь храмам", callback_data="temples")],
        [InlineKeyboardButton(text="💝 Поддержать проект", callback_data="support")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    await callback_query.message.edit_text(
        "Выберите направление пожертвования:",
        reply_markup=keyboard
    )

# ---------- Общие ----------
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
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=back_keyboard)

@dp.callback_query(lambda c: c.data == "support")
async def support_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = (
        "💝 *Поддержка разработчика*\n\n"
        "Этот бот создаётся и поддерживается добровольцем. "
        "Если вы хотите помочь проекту развиваться — "
        "вы можете совершить добровольное пожертвование.\n\n"
        "Ссылка: https://yoomoney.ru/fundraise/1GOHGUKREAL.260326\n\n"
        "Все средства пойдут на развитие бота, хостинг и обновления. "
        "Спасибо за вашу поддержку!"
    )
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", disable_web_page_preview=True, reply_markup=back_keyboard)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
