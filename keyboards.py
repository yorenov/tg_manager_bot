from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import texts as txt


addadmin = KeyboardButton(txt.addadmin)
listadmin = KeyboardButton(txt.listadmins)
deladmin = KeyboardButton(txt.deladmins)

startMenu = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2).row(addadmin, listadmin, deladmin)
