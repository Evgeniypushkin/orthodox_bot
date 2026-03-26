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

# ---------- Загрузка данных ----------
def load_lives():
    with open("data/lives.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_prayer(file_name):
    with open(f"data/{file_name}", "r", encoding="utf-8") as f:
        return f.read()

lives_data = load_lives()
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
    day = today.day
    month = today.month
    key = f"{day:02d}-{month:02d}"
    
    if key in lives_data:
        saints = lives_data[key]
        parts = []
        for saint in saints:
            name = saint.get("name", "Святой")
            life = saint.get("life", "Житие не найдено")
            if len(life) > 1500:
                life = life[:1500] + "..."
            parts.append(f"📖 *{name}*\n\n{life}")
        text = "\n\n---\n\n".join(parts)
    else:
        text = "На сегодня житий святых в базе нет."
    
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]])
    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_keyboard)

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
    await callback_query.message.edit_text(text, parse_mode="Markdown", reply_markup=back_to_prayers)

@dp.callback_query(lambda c: c.data == "evening_prayers")
async def evening_prayers_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = f"🙏 *Вечерние молитвы*\n\n{evening_prayers}"
    back_to_prayers = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data="prayers")]])
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
