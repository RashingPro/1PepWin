import asyncio
import sqlite3

import db_manager
import telebot.async_telebot as async_telebot
from telebot import types
from telebot.asyncio_storage import StateMemoryStorage
from telebot.asyncio_handler_backends import State, StatesGroup
import yaml

TOKEN = '6529609103:AAGsi-5Fjotc0sLmjhuUBlkHXRMZuw8Eii8'
DB_FILE = 'main.db'
bot = async_telebot.AsyncTeleBot(token=TOKEN)

current_local = 'ru-RU'
with open(f'./local/{current_local}.yml', encoding='utf-8') as f:
    yml_local = yaml.safe_load(f)


@bot.message_handler(commands=['start', 'menu'])
@bot.callback_query_handler(func=lambda call: call.data == 'menu')
async def cmd_menu(call: types.Message | types.CallbackQuery):
    if isinstance(call, types.Message):
        msg = call
        user = call.from_user
    else:
        msg = call.message
        user = call.from_user
        await bot.delete_message(msg.chat.id, msg.message_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(yml_local['btn_events_for_bet'], callback_data='btn_events_for_bet'))
    markup.add(types.InlineKeyboardButton(yml_local['btn_deposit'], callback_data='btn_deposit'))
    user_balance = await db_manager.get_value(
        DB_FILE,
        'Users',
        'tg_id',
        user.id,
        'diamonds'
    )
    user_balance = user_balance[0]
    await bot.send_message(
        chat_id=msg.chat.id,
        parse_mode='html',
        text='\n'.join(yml_local['menu']).format(str(user_balance) + ' ' + yml_local['diamond']),
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'btn_deposit')
@bot.message_handler(commands=['deposit'])
async def cmd_deposit(call: types.Message | types.CallbackQuery):
    if isinstance(call, types.Message):
        msg = call
        user = call.from_user
    else:
        msg = call.message
        user = call.from_user
        await bot.delete_message(msg.chat.id, msg.message_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Назад', callback_data='menu'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text='\n'.join(yml_local['to_make_deposit']).format(user.id),
        parse_mode='html',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == 'btn_events_for_bet')
@bot.message_handler(commands=['events'])
async def cmd_events(call: types.Message | types.CallbackQuery):
    if isinstance(call, types.Message):
        msg = call
        user = call.from_user
    else:
        msg = call.message
        user = call.from_user
        await bot.delete_message(msg.chat.id, msg.message_id)
    markup = types.InlineKeyboardMarkup()
    event_list = await db_manager.get_all_values(
        DB_FILE,
        'Events',
        '*'
    )
    event_list = [dict(_e) for _e in event_list]
    for event in event_list:
        markup.add(types.InlineKeyboardButton(event['title'], callback_data=f'select_event:{event['id']}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='menu'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text='\n'.join(yml_local['events_for_bet']),
        parse_mode='html',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_event:'))
async def select_event(call: types.CallbackQuery):
    msg = call.message
    user = call.from_user
    event_id = int(call.data.split(':')[1])
    await bot.delete_message(msg.chat.id, msg.message_id)
    event_predicts = await db_manager.get_all_values(DB_FILE, 'EventPredicts', 'event_id', str(event_id), '*')
    event_predicts = [dict(_p) for _p in event_predicts]
    markup = types.InlineKeyboardMarkup()
    for predict in event_predicts:
        markup.add(types.InlineKeyboardButton(predict['title'], callback_data=f'select_predict:{predict['id']}'))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='btn_events_for_bet'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text='\n'.join(yml_local['predicts_for_bet']),
        parse_mode='html',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('select_predict:'))
async def select_predict(call: types.CallbackQuery):
    msg = call.message
    user = call.from_user
    predict_id = int(call.data.split(':')[1])
    await bot.delete_message(msg.chat.id, msg.message_id)
    predict_info = await db_manager.get_value(
        DB_FILE,
        'EventPredicts',
        'id',
        predict_id,
        '*',
        row_factory=sqlite3.Row
    )
    text = '\n'.join(yml_local['predict_info'])
    text = text.format(
        predict_info['title'],
        predict_info['option1'],
        predict_info['option2'],
        predict_info['sum_option1'],
        predict_info['sum_option2'],
        (predict_info['users_option1'] + predict_info['users_option2']),
        predict_info['date'],
        predict_info['date_end_predicts']
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        predict_info['option1'],
        callback_data=f'start_making_bet:{predict_info['id']}:1')
    )
    markup.add(types.InlineKeyboardButton(
        predict_info['option2'],
        callback_data=f'start_making_bet:{predict_info['id']}:2')
    )
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'select_event:{predict_info['event_id']}'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text=text,
        parse_mode='html',
        reply_markup=markup
    )


class MakingBetInfoState(StatesGroup):
    diamonds = State()


@bot.callback_query_handler(func=lambda call: call.data.startswith('start_making_bet:'))
async def start_making_bet(call: types.CallbackQuery):
    msg = call.message
    user = call.from_user
    predict_id = int(call.data.split(':')[1])
    option = int(call.data.split(':')[2])
    await bot.delete_message(msg.chat.id, msg.message_id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'select_predict:{predict_id}'))
    # TODO: обработка стейтов
    await bot.send_message(
        chat_id=msg.chat.id,
        text=yml_local['diamonds_count_select'],
        parse_mode='html'
    )


async def main():
    task1 = asyncio.create_task(bot.infinity_polling(timeout=None))
    task2 = asyncio.create_task(db_manager.init_db(DB_FILE))
    await task1
    await task2


asyncio.run(main())
