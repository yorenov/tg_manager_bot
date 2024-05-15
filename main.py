import time
import sqlite3 as sq

from aiogram import executor, types
from aiogram.dispatcher.filters import IsReplyFilter
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.dispatcher import FSMContext

from config import ADMINS
import texts as txt
import keyboards as kb
from misc import bot, dp

con = sq.connect("database.db")
cur = con.cursor()


# Send admin message about bot started
async def startbot(*args, **kwargs):
    cur.execute("""CREATE TABLE IF NOT EXISTS admins (
                    id INTEGER NOT NULL
                )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
                    id           INTEGER NOT NULL,
                    username     TEXT,
                    warns_counts INTEGER DEFAULT 0
                )""")
    con.commit()
    for admin_id in ADMINS:
        try:
            await bot.send_message(chat_id=admin_id, text='Bot started!')
        except:
            print(admin_id, "- Не написал боту")


class addadmin(StatesGroup):
    idadmin = State()


class deladmin(StatesGroup):
    idadmin = State()


# info tour
@dp.message_handler(commands=['start'], chat_type=[types.ChatType.PRIVATE, types.ChatType.SENDER])
async def welcome_send_info(message: types.Message):
    user = cur.execute(f"SELECT id FROM users WHERE id = {message.from_user.id}").fetchone()
    if user is None:
        cur.execute(f"INSERT INTO users VALUES ({message.from_user.id}, '{message.from_user.username}', 0)")
        con.commit()
    if message.from_user.id in ADMINS:
        await message.answer(txt.start, reply_markup=kb.startMenu)
    else:
        await message.answer(txt.start)


@dp.message_handler(chat_type=[types.ChatType.PRIVATE, types.ChatType.SENDER])
async def echo(message: types.Message):
    if message.from_user.id in ADMINS:
        if message.text == "Добавить админа":
            await message.answer("Введите id админа")
            await addadmin.idadmin.set()
        elif message.text == "Список админов":
            admins = cur.execute(f"SELECT id FROM admins").fetchall()
            await message.answer('\n'.join(map(str, admins)))
        elif message.text == "Удалить админа":
            await message.answer("Введите id админа")
            await deladmin.idadmin.set()


@dp.message_handler(state=addadmin.idadmin)
async def addadmin_echo(message: types.Message, state: FSMContext):
    newadminid = message.text
    cur.execute(f'INSERT INTO admins VALUES ({newadminid})')
    con.commit()
    await message.answer(f'Админ {newadminid} добавлен')
    await state.finish()


@dp.message_handler(state=deladmin.idadmin)
async def deladmin_echo(message: types.Message, state: FSMContext):
    adminid = message.text
    cur.execute(f'DELETE from admins WHERE id = ?', [adminid])
    con.commit()
    await message.answer(f'Админ {adminid} удалён')
    await state.finish()


# new chat member
@dp.message_handler(content_types=["new_chat_members"])
async def new_chat_member(message: types.Message):
    user = cur.execute(f"SELECT * FROM users WHERE id == {message.new_chat_members[0].id}").fetchall()
    if not user:
        cur.execute(
            f"INSERT INTO users VALUES ({message.new_chat_members[0].id}, '{message.new_chat_members[0].username}', 0)")
        con.commit()
    chat_id = message.chat.id
    await bot.delete_message(chat_id=chat_id, message_id=message.message_id)
    # await bot.send_message(chat_id=chat_id,
    #                        text=f"[{message.new_chat_members[0].full_name}]"
    #                             f"(tg://user?id={message.new_chat_members[0].id}) " + txt.new_chat_member,
    #                        parse_mode=types.ParseMode.MARKDOWN)


# delete message user leave chat
@dp.message_handler(content_types=["left_chat_member"])
async def leave_chat(message: types.Message):
    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


# ban user
@dp.message_handler(commands=['ban'],
                    commands_prefix='!', chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP])
async def ban(message: types.Message):
    admin = cur.execute(f"SELECT id FROM admins WHERE id = {message.from_user.id}").fetchone()
    if message.from_user.id == admin or message.from_user.id in ADMINS:
        if message.reply_to_message:
            replied_user = message.reply_to_message.from_user.id
        else:
            user = message.text.split("@")[1]
            replied_user = cur.execute(f"SELECT id FROM users WHERE username = ?", [user]).fetchone()[0]
        await bot.kick_chat_member(chat_id=message.chat.id, user_id=replied_user)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        if message.reply_to_message:
            await bot.send_message(chat_id=message.chat.id, text=f"[{message.reply_to_message.from_user.full_name}]"
                                                                 f"(tg://user?id={replied_user})"
                                                                 f" был забанен",
                                   parse_mode=types.ParseMode.MARKDOWN)
        else:
            await bot.send_message(chat_id=message.chat.id, text=f"[@{user}]"
                                                                 f"(tg://user?id={replied_user})"
                                                                 f" был забанен",
                                   parse_mode=types.ParseMode.MARKDOWN)


# mute user in chat
@dp.message_handler(IsReplyFilter(is_reply=True), commands=['mute'],
                    commands_prefix='!', chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP])
async def mute(message: types.Message):
    admin = cur.execute(f"SELECT id FROM admins WHERE id = {message.from_user.id}").fetchone()
    if message.from_user.id == admin or message.from_user.id in ADMINS:
        args = message.text.split()
        if len(args) > 1:
            till_date = message.text.split()[1]
        else:
            till_date = "15m"

        if till_date[-1] == "m":
            ban_for = int(till_date[:-1]) * 60
        elif till_date[-1] == "h":
            ban_for = int(till_date[:-1]) * 3600
        elif till_date[-1] == "d":
            ban_for = int(till_date[:-1]) * 86400
        else:
            ban_for = 15 * 60

        replied_user = message.reply_to_message.from_user.id
        now_time = int(time.time())
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=replied_user,
                                       permissions=types.ChatPermissions(can_send_messages=False,
                                                                         can_send_media_messages=False,
                                                                         can_send_other_messages=False),
                                       until_date=now_time + ban_for)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        await bot.send_message(text=f"[{message.reply_to_message.from_user.full_name}](tg://user?id={replied_user})"
                                    f" muted for {till_date}",
                               chat_id=message.chat.id, parse_mode=types.ParseMode.MARKDOWN)


# un_mute user in chat
@dp.message_handler(commands_prefix='!',
                    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=['unmute'])
async def un_mute_user(message: types.Message):
    admin = cur.execute(f"SELECT id FROM admins WHERE id = {message.from_user.id}").fetchone()
    if message.from_user.id == admin or message.from_user.id in ADMINS:
        if message.reply_to_message:
            replied_user = message.reply_to_message.from_user.id
        else:
            user = message.text.split("@")[1]
            replied_user = cur.execute(f"SELECT id FROM users WHERE username = ?", [user]).fetchone()[0]
        await bot.restrict_chat_member(chat_id=message.chat.id, user_id=replied_user,
                                       permissions=types.ChatPermissions(can_send_messages=True,
                                                                         can_send_media_messages=True,
                                                                         can_send_other_messages=True), )
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        if message.reply_to_message:
            await bot.send_message(text=f"[{message.reply_to_message.from_user.full_name}](tg://user?id={replied_user})"
                                        f" можешь теперь писать в чат )",
                                   chat_id=message.chat.id, parse_mode=types.ParseMode.MARKDOWN)
        else:
            await bot.send_message(text=f"[@{user}](tg://user?id={replied_user})"
                                        f" можешь теперь писать в чат )",
                                   chat_id=message.chat.id, parse_mode=types.ParseMode.MARKDOWN)


# delete user message
@dp.message_handler(IsReplyFilter(is_reply=True), commands_prefix='!',
                    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=['del'])
async def delete_message(message: types.Message):
    admin = cur.execute(f"SELECT id FROM admins WHERE id = {message.from_user.id}").fetchone()
    if message.from_user.id == admin or message.from_user.id in ADMINS:
        msg_id = message.reply_to_message.message_id
        await bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)


# report about spam or something else
@dp.message_handler(commands_prefix='!',
                    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=['warn'])
async def warn_user(message: types.Message):
    admin = cur.execute(f"SELECT id FROM admins WHERE id = {message.from_user.id}").fetchone()
    if message.from_user.id == admin or message.from_user.id in ADMINS:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        if message.reply_to_message:
            replied_user = message.reply_to_message.from_user.id
        else:
            user = message.text.split("@")[1]
            replied_user = cur.execute(f"SELECT id FROM users WHERE username = ?", [user]).fetchone()[0]
        cur.execute(f"UPDATE users SET warns_counts = warns_counts + 1 WHERE id = ?", [replied_user])
        con.commit()
        warns_count = cur.execute(f"SELECT warns_counts FROM users WHERE id == {replied_user}").fetchone()[0]
        if int(warns_count) >= 3:
            await bot.kick_chat_member(chat_id=message.chat.id, user_id=replied_user)
            await bot.unban_chat_member(chat_id=message.chat.id, user_id=replied_user)
            if message.reply_to_message:
                await bot.send_message(
                    text=f"User: [{message.reply_to_message.from_user.full_name}](tg://user?id={replied_user})\n"
                         f"Получил 3/3 предупреждений и был кикнут.", chat_id=message.chat.id,
                    parse_mode=types.ParseMode.MARKDOWN, disable_web_page_preview=True)
            else:
                await bot.send_message(
                    text=f"User: [@{user}](tg://user?id={replied_user})\n"
                         f"Получил 3/3 предупреждений и был кикнут.", chat_id=message.chat.id,
                    parse_mode=types.ParseMode.MARKDOWN, disable_web_page_preview=True)
                cur.execute(f"UPDATE users SET warns_counts = 0 WHERE id = ?", [replied_user])
        else:
            if message.reply_to_message:
                await bot.send_message(
                    text=f"User: [{message.reply_to_message.from_user.full_name}](tg://user?id={replied_user})\n"
                         f"Получил предупреждение: {warns_count}/3",
                    chat_id=message.chat.id, parse_mode=types.ParseMode.MARKDOWN,
                    disable_web_page_preview=True)
            else:
                await bot.send_message(
                    text=f"User: [@{user}](tg://user?id={replied_user})\n"
                         f"Получил предупреждение: {warns_count}/3",
                    chat_id=message.chat.id, parse_mode=types.ParseMode.MARKDOWN,
                    disable_web_page_preview=True)


@dp.message_handler(commands_prefix='!',
                    chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP], commands=['unwarn'])
async def unwarn_user(message: types.Message):
    admin = cur.execute(f"SELECT id FROM admins WHERE id = {message.from_user.id}").fetchone()
    if message.from_user.id == admin or message.from_user.id in ADMINS:
        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        if message.reply_to_message:
            replied_user = message.reply_to_message.from_user.id
        else:
            user = message.text.split("@")[1]
            replied_user = cur.execute(f"SELECT id FROM users WHERE username = ?", [user]).fetchone()[0]
        warns_count = cur.execute(f"SELECT warns_counts FROM users WHERE id == {replied_user}").fetchone()[0]
        if warns_count > 0:
            cur.execute(f"UPDATE users SET warns_counts = warns_counts - 1 WHERE id = ?", [replied_user])
            con.commit()
            warns_count = cur.execute(f"SELECT warns_counts FROM users WHERE id == {replied_user}").fetchone()[0]
            if message.reply_to_message:
                await bot.send_message(
                    text=f"C пользователя: [{message.reply_to_message.from_user.full_name}](tg://user?id={replied_user})\n"
                         f"Сняли предупреждение - {warns_count}/3.", chat_id=message.chat.id,
                    parse_mode=types.ParseMode.MARKDOWN, disable_web_page_preview=True)
            else:
                await bot.send_message(
                    text=f"C пользователя: [@{user}](tg://user?id={replied_user})\n"
                         f"Сняли предупреждение - {warns_count}/3.", chat_id=message.chat.id,
                    parse_mode=types.ParseMode.MARKDOWN, disable_web_page_preview=True)
        else:
            if message.reply_to_message:
                await bot.send_message(
                    text=f"У пользователя: [{message.reply_to_message.from_user.full_name}](tg://user?id={replied_user})\n"
                         f"0/3 предупреждений.",
                    chat_id=message.chat.id, parse_mode=types.ParseMode.MARKDOWN,
                    disable_web_page_preview=True)
            else:
                await bot.send_message(
                    text=f"У пользователя: [@{user}](tg://user?id={replied_user})\n"
                         f"0/3 предупреждений.",
                    chat_id=message.chat.id, parse_mode=types.ParseMode.MARKDOWN,
                    disable_web_page_preview=True)


@dp.message_handler(commands=['kick'],
                    commands_prefix='!', chat_type=[types.ChatType.SUPERGROUP, types.ChatType.GROUP])
async def kick(message: types.Message):
    admin = cur.execute(f"SELECT id FROM admins WHERE id = {message.from_user.id}").fetchone()
    if message.from_user.id == admin or message.from_user.id in ADMINS:
        if message.reply_to_message:
            replied_user = message.reply_to_message.from_user.id
        else:
            user = message.text.split("@")[1]
            replied_user = cur.execute(f"SELECT id FROM users WHERE username = ?", [user]).fetchone()[0]
        await bot.kick_chat_member(chat_id=message.chat.id, user_id=replied_user)
        await bot.unban_chat_member(chat_id=message.chat.id, user_id=replied_user)
        if message.reply_to_message:
            await bot.send_message(chat_id=message.chat.id, text=f"[{message.reply_to_message.from_user.full_name}]"
                                                                 f"(tg://user?id={replied_user})"
                                                                 f" был кикнут",
                                   parse_mode=types.ParseMode.MARKDOWN)
        else:
            await bot.send_message(chat_id=message.chat.id, text=f"[@{user}]"
                                                                 f"(tg://user?id={replied_user})"
                                                                 f" был кикнут",
                                   parse_mode=types.ParseMode.MARKDOWN)


# Polling
if __name__ == '__main__':
    executor.start_polling(dp, on_startup=startbot, skip_updates=True)
