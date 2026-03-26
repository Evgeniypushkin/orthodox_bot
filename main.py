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

# ---------- Загружаем локальные данные ----------
def load_lives():
    with open("data/lives.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_prayer(file_name):
    with open(f"data/{file_name}", "r", encoding="utf-8") as f:
        return f.read()

lives_data = load_lives()
morning_prayers = load_prayer("morning_prayers.txt")
evening_prayers = load_prayer("evening_prayers.txt")

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

# ---------- Обработчики ----------
@dp.message(Command("start"))
async def start_command(message: types.Message):
    await message.answer(
        "🛐 Выберите раздел:",
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
        text_parts = []
        for saint in saints:
            name = saint.get("name", "Святой")
            life = saint.get("life", "Описание временно недоступно")
            if len(life) > 1500:
                life = life[:1500] + "..."
            text_parts.append(f"📖 *{name}*\n\n{life}")
        text = "\n\n---\n\n".join(text_parts)
    else:
        text = "На сегодня житий святых в базе нет. Загляните позже."
    
    await callback_query.message.answer(text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "prayers")
async def prayers_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = (
        f"🙏 *Утренние молитвы*\n\n{morning_prayers}\n\n"
        f"🙏 *Вечерние молитвы*\n\n{evening_prayers}"
    )
    if len(text) > 4000:
        await callback_query.message.answer(f"🙏 *Утренние молитвы*\n\n{morning_prayers}", parse_mode="Markdown")
        await callback_query.message.answer(f"🙏 *Вечерние молитвы*\n\n{evening_prayers}", parse_mode="Markdown")
    else:
        await callback_query.message.answer(text, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data == "calendar")
async def calendar_callback(callback_query: types.CallbackQuery):
    await callback_query.answer()
    text = (
        "📅 *Православный календарь*\n\n"
        "Подробный календарь с праздниками и постами будет добавлен позже.\n"
        "Пока вы можете воспользоваться разделом «Чтения дня» для знакомства с житиями святых."
    )
    await callback_query.message.answer(text, parse_mode="Markdown")

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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
