import asyncio
import sqlite3

from aiogram import Bot, Dispatcher
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command

from config import BOT_TOKEN


bot = Bot(BOT_TOKEN)
dp = Dispatcher()

db = sqlite3.connect("users.db")
cur = db.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
chat_id INTEGER,
user_id INTEGER,
username TEXT,
first_name TEXT,
PRIMARY KEY(chat_id, user_id)
)
""")

db.commit()


# ─────────────────────────
# Пользователь написал боту
# ─────────────────────────

@dp.message(Command("start"))
async def start(message: Message):

    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    cur.execute(
        "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
        (message.chat.id, user_id, username, first_name)
    )

    db.commit()

    await message.answer("Вы зарегистрированы")


# ─────────────────────────
# Пользователь вошёл в группу
# ─────────────────────────

@dp.chat_member()
async def user_join(event: ChatMemberUpdated):

    user = event.new_chat_member.user

    chat_id = event.chat.id
    user_id = user.id
    username = user.username
    first_name = user.first_name

    status = event.new_chat_member.status

    if status == "member":

        cur.execute(
            "INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?)",
            (chat_id, user_id, username, first_name)
        )

        db.commit()

        print("Сохранён пользователь:", user_id, username)

    elif status in ["left", "kicked"]:

        cur.execute(
            "DELETE FROM users WHERE chat_id=? AND user_id=?",
            (chat_id, user_id)
        )

        db.commit()

        print("Пользователь удалён из базы:", user_id)


# ─────────────────────────
# Команда удаления
# ─────────────────────────

@dp.message(Command("add"))
async def add_user(message: Message):

    member = await bot.get_chat_member(
        message.chat.id,
        message.from_user.id
    )

    if member.status not in ["administrator", "creator"]:
        await message.answer("Команда доступна только администраторам")
        return

    parts = message.text.split()

    if len(parts) != 3:
        await message.answer("/add @username seconds")
        return

    username = parts[1].replace("@", "")
    seconds = int(parts[2])

    cur.execute(
        "SELECT user_id FROM users WHERE username=? AND chat_id=?",
        (username, message.chat.id)
    )

    row = cur.fetchone()

    if not row:
        await message.answer("Пользователь не найден в базе")
        return

    user_id = row[0]

    await message.answer(
        f"Пользователь @{username} будет удалён через {seconds} сек"
    )

    asyncio.create_task(
        remove_later(message.chat.id, user_id, seconds)
    )


# ─────────────────────────
# Таймер удаления
# ─────────────────────────

async def remove_later(chat_id, user_id, delay):

    await asyncio.sleep(delay)

    try:
        await bot.ban_chat_member(chat_id, user_id)
        await bot.unban_chat_member(chat_id, user_id)

    except Exception as e:
        print("Ошибка удаления:", e)


# ─────────────────────────
# Запуск
# ─────────────────────────

async def main():

    await dp.start_polling(
        bot,
        allowed_updates=["message", "chat_member"]
    )


if __name__ == "__main__":
    asyncio.run(main())