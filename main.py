import os
import asyncio
import logging
import json
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
def load_prayers():
    with open("data/prayers.json", "r", encoding="utf-8") as f:
        return json.load(f)

prayers_data = load_prayers()

# ---------- Клавиатуры ----------
main_menu_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="📖 Чтения дня", callback_data="reading")],
        [InlineKeyboardButton(text="🙏 Молитвы", callback_data="prayers")],
        [InlineKeyboardButton(text="🏛️ Храмы", callback_data="temples")],
        [InlineKeyboardButton(text="💝 Поддержать", callback_data="support")],
    ]
)

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
                keyboard.append([InlineKeyboardButton(text=prayer["title"], callback_data=f"prayer_{cat_id}_{prayer['title']}")])
            keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="prayers")])
            return InlineKeyboardMarkup(inline_keyboard=keyboard)
    return None

def get_prayer_text(cat_id, prayer_title):
    for cat in prayers_data["categories"]:
        if cat["id"] == cat_id:
            for prayer in cat["prayers"]:
                if prayer["title"] == prayer_title:
                    return prayer["text"]
    return "Молитва не найдена."

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
    parts = callback_query.data.split("_")
    cat_id = parts[1]
    prayer_title = "_".join(parts[2:])  # на случай, если в названии есть подчеркивания
    text = get_prayer_text(cat_id, prayer_title)
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data=f"prayer_cat_{cat_id}")]])
    await callback_query.message.edit_text(
        f"*{prayer_title}*\n\n{text}",
        parse_mode="Markdown",
        reply_markup=back_keyboard
    )

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
