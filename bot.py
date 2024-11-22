import asyncio
import sqlite3
from telebot.asyncio_storage import StateMemoryStorage
import db_manager
import telebot.async_telebot as async_telebot
from telebot import types
from telebot.asyncio_handler_backends import State, StatesGroup
import yaml
import datetime
import random as rd
from telebot import asyncio_helper
# asyncio_helper.proxy = 'http://proxy.server:3128'

TOKEN = 'token_here'
DB_FILE = 'main.db'
DATE_FORMAT = '%d.%m.%Y %H:%M'
COMMISSION = 10
ADMINS = [1282559297, 2032985740]
BETS_INFO = [1282559297, 2032985740]
bot = async_telebot.AsyncTeleBot(token=TOKEN, state_storage=StateMemoryStorage())

current_local = 'ru-RU'
with open(f'./local/{current_local}.yml', encoding='utf-8') as f:
    yml_local = yaml.safe_load(f)


def is_admin(user_id: int) -> bool:
    if user_id not in ADMINS:
        return False
    return True


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

    res = await db_manager.get_value(DB_FILE, 'Users', 'tg_id', user.id, '*')
    if (res is None) and (not user.is_bot):
        await db_manager.register_user(DB_FILE, user.id)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(yml_local['btn_events_for_bet'], callback_data='btn_events_for_bet'))
    markup.add(types.InlineKeyboardButton(yml_local['btn_deposit'], callback_data='btn_deposit'))
    markup.add(types.InlineKeyboardButton(yml_local['btn_my_bets'], callback_data='btn_my_bets'))
    markup.add(types.InlineKeyboardButton(yml_local['btn_support'], callback_data='btn_support'))
    user_balance = await db_manager.get_value(
        DB_FILE,
        'Users',
        'tg_id',
        msg.chat.id,
        'diamonds'
    )
    user_balance = user_balance[0]
    await bot.send_message(
        chat_id=msg.chat.id,
        parse_mode='html',
        text='\n'.join(yml_local['menu']).format(str(user_balance) + ' ' + yml_local['diamond']),
        reply_markup=markup
    )


class DepositMcNick(StatesGroup):
    mc_nick = State()


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
    user_mc_nick = await db_manager.get_value(
        DB_FILE,
        'Users',
        'tg_id',
        user.id,
        'mc_nick'
    )
    user_mc_nick = user_mc_nick[0]
    if user_mc_nick is None:
        mc_nick_status_txt = '\n'.join(yml_local['deposit_menu_need_nickname'])
        markup.add(types.InlineKeyboardButton('Указать никнейм', callback_data='deposit_set_nickname:new'))
    else:
        mc_nick_status_txt = '\n'.join(yml_local['deposit_menu_already_nickname']).format(user_mc_nick, '')
        markup.add(types.InlineKeyboardButton('Изменить никнейм', callback_data='deposit_set_nickname:edit'))

    markup.add(types.InlineKeyboardButton('Назад', callback_data='menu'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text='\n'.join(yml_local['deposit_menu_available']).format(mc_nick_status_txt),
        parse_mode='html',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('deposit_set_nickname:'))
async def deposit_set_nickname(call: types.CallbackQuery):
    await bot.delete_message(call.message.chat.id, call.message.id)
    set_type = call.data.split(':')[1]
    markup = types.InlineKeyboardMarkup()
    txt = 'Error'
    match set_type:
        case 'new':
            txt = '\n'.join(yml_local['deposit_setting_nickname_new'])
        case 'edit':
            txt = '\n'.join(yml_local['deposit_setting_nickname_edit'])
    markup.add(types.InlineKeyboardButton('Отмена', callback_data='btn_deposit'))
    await bot.set_state(call.from_user.id, DepositMcNick.mc_nick, chat_id=call.message.chat.id)
    await bot.send_message(
        chat_id=call.message.chat.id,
        text=txt,
        parse_mode='html',
        reply_markup=markup
    )


@bot.message_handler(state=DepositMcNick.mc_nick)
async def deposit_mc_nick(msg: types.Message):
    await bot.delete_state(msg.from_user.id, msg.chat.id)
    new_mc_nick = msg.text
    await db_manager.execute(
        DB_FILE,
        f'UPDATE Users SET mc_nick = "{new_mc_nick}" WHERE tg_id = ?',
        (msg.from_user.id,)
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Назад', callback_data='btn_deposit'))
    await bot.send_message(chat_id=msg.chat.id,
                           text='\n'.join(yml_local['deposit_setting_nickname_success']),
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
        markup.add(types.InlineKeyboardButton(event['title'], callback_data=f'select_event:{event["id"]}'))
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
        now = datetime.datetime.now()
        date_end = datetime.datetime.strptime(predict['date_end_predicts'], DATE_FORMAT)
        if now < date_end:
            markup.add(types.InlineKeyboardButton(predict['title'], callback_data=f'select_predict:{predict["id"]}'))
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
        callback_data=f'start_making_bet:{predict_info["id"]}:1')
    )
    markup.add(types.InlineKeyboardButton(
        predict_info['option2'],
        callback_data=f'start_making_bet:{predict_info["id"]}:2')
    )
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'select_event:{predict_info["event_id"]}'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text=text,
        parse_mode='html',
        reply_markup=markup
    )


class MakingBetInfoState(StatesGroup):
    option = State()
    predict_id = State()
    diamonds = State()


@bot.callback_query_handler(func=lambda call: call.data.startswith('start_making_bet:'))
async def start_making_bet(call: types.CallbackQuery):
    msg = call.message
    user = call.from_user
    predict_id = int(call.data.split(':')[1])
    option = int(call.data.split(':')[2])
    await bot.delete_message(msg.chat.id, msg.message_id)
    date_end_str = await db_manager.get_value(
        DB_FILE,
        'EventPredicts',
        'id',
        predict_id,
        'date_end_predicts'
    )
    date_end_str = date_end_str[0]
    now = datetime.datetime.now()
    date_end = datetime.datetime.strptime(date_end_str, DATE_FORMAT)
    if now >= date_end:
        await bot.send_message(
            chat_id=msg.chat.id,
            text='Приём ставок уже завершён'
        )
        await cmd_menu(msg)
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Назад', callback_data=f'select_predict:{predict_id}'))
    await bot.set_state(user.id, MakingBetInfoState.diamonds, msg.chat.id)
    await bot.current_states.set_data(msg.chat.id, user.id, 'option', option)
    await bot.current_states.set_data(msg.chat.id, user.id, 'predict_id', predict_id)
    await bot.send_message(
        chat_id=msg.chat.id,
        text=yml_local['diamonds_count_select'],
        parse_mode='html',
        reply_markup=markup
    )


@bot.message_handler(state=MakingBetInfoState.diamonds)
async def making_bet_diamonds(msg: types.Message):
    try:
        int(msg.text)
    except ValueError:
        return
    diamonds_count = int(msg.text)
    user_balance = await db_manager.get_value(
        DB_FILE,
        'Users',
        'tg_id',
        msg.from_user.id,
        'diamonds'
    )
    user_balance = user_balance[0]
    if user_balance < diamonds_count:
        await bot.send_message(
            chat_id=msg.chat.id,
            text=yml_local['not_enough_diamonds']
        )
        await cmd_menu(msg)
        await bot.delete_state(msg.from_user.id, msg.chat.id)
        return
    async with bot.retrieve_data(msg.from_user.id, msg.chat.id) as data:
        option = data['option']
        predict_id = data['predict_id']
    await bot.delete_state(msg.from_user.id, msg.chat.id)

    option_title = await db_manager.get_value(
        DB_FILE,
        'EventPredicts',
        'id',
        predict_id,
        f'option{option}'
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Подтвердить',
                                          callback_data=f'confirm_bet:{predict_id}:{option}:{diamonds_count}')
               )
    markup.add(types.InlineKeyboardButton('Отмена', callback_data=f'select_predict:{predict_id}'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text='\n'.join(yml_local['confirm_bet']).format(option_title[0], f'{diamonds_count}', COMMISSION),
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_bet:'))
async def confirm_bet(call: types.CallbackQuery):
    data = call.data.split(':')
    predict_id = int(data[1])
    option = int(data[2])
    diamonds_count = int(data[3])
    await bot.delete_message(
        chat_id=call.message.chat.id,
        message_id=call.message.id
    )
    try:
        user_old = await db_manager.get_value(
            DB_FILE,
            'PredictBets',
            'predict_id',
            predict_id,
            '*',
            sqlite3.Row
        )
        user_old = dict(user_old)[str(call.from_user.id)]
        if user_old is not None:  # отмена предыдущей ставки если она есть

            user_old_option = user_old.split(':')[0]
            user_old_bet = int(user_old.split(':')[1])
            current_for_old_option = await db_manager.get_value(
                DB_FILE,
                'EventPredicts',
                'id',
                predict_id,
                f'sum_option{user_old_option}'
            )
            current_for_old_option = current_for_old_option[0]
            await db_manager.execute(
                DB_FILE,
                f'UPDATE EventPredicts SET "sum_option{user_old_option}" = ? WHERE id = ?',
                (current_for_old_option - user_old_bet, predict_id)
            )
            current_users_for_old_option = await db_manager.get_value(
                DB_FILE,
                'EventPredicts',
                'id',
                predict_id,
                f'users_option{user_old_option}'
            )
            current_users_for_old_option = current_users_for_old_option[0]
            await db_manager.execute(
                DB_FILE,
                f'UPDATE EventPredicts SET users_option{user_old_option} = ? WHERE id = ?',
                (current_users_for_old_option - 1, predict_id)
            )
            user_balance = await db_manager.get_value(
                DB_FILE,
                'Users',
                'tg_id',
                call.from_user.id,
                'diamonds'
            )
            user_balance = user_balance[0]
            await db_manager.execute(
                DB_FILE,
                f'UPDATE Users SET diamonds = ? WHERE tg_id = ?',
                (user_balance + user_old_bet, call.from_user.id)
            )

        current_for_new_option = await db_manager.get_value(
            DB_FILE,
            'EventPredicts',
            'id',
            predict_id,
            f'sum_option{option}'
        )
        current_for_new_option = current_for_new_option[0]
        await db_manager.execute(
            DB_FILE,
            f'UPDATE EventPredicts SET sum_option{option} = ? WHERE id = ?',
            (current_for_new_option + diamonds_count, predict_id)
        )
        current_users_for_new_option = await db_manager.get_value(
            DB_FILE,
            'EventPredicts',
            'id',
            predict_id,
            f'users_option{option}'
        )
        current_users_for_new_option = current_users_for_new_option[0]
        await db_manager.execute(
            DB_FILE,
            f'UPDATE EventPredicts SET users_option{option} = ? WHERE id = ?',
            (current_users_for_new_option + (1 if diamonds_count > 0 else 0), predict_id)
        )
        user_balance = await db_manager.get_value(
            DB_FILE,
            'Users',
            'tg_id',
            call.from_user.id,
            'diamonds'
        )
        user_balance = user_balance[0]
        await db_manager.execute(
            DB_FILE,
            f'UPDATE Users SET diamonds = ? WHERE tg_id = ?',
            (user_balance - diamonds_count, call.from_user.id)
        )

        await db_manager.execute(
            DB_FILE,
            f'UPDATE PredictBets SET "{call.from_user.id}" = ? WHERE predict_id = ?',
            (f"{option}:{diamonds_count}" if diamonds_count > 0 else None, predict_id)
        )
    except Exception as e:
        print(e)
        await bot.send_message(chat_id=call.message.chat.id, text='Не удалось сделать ставку. Попробуйте позже')
    else:
        await bot.send_message(
            chat_id=call.message.chat.id,
            text='Успешно. Новая ставка на это событие заменит предыдущую. Если хотите отменить ставку - поставьте 0 алмазов'
        )
        mc_nick = await db_manager.get_value(
            DB_FILE,
            'Users',
            'tg_id',
            call.from_user.id,
            'mc_nick'
        )
        predict = await db_manager.get_all_values(
            DB_FILE,
            'EventPredicts',
            'id',
            str(predict_id),
            '*'
        )
        predict = dict(predict[0])
        event = await db_manager.get_value(
            DB_FILE,
            'Events',
            'id',
            predict['event_id'],
            'title'
        )
        event = event[0]
        for bet_info_user in BETS_INFO:
            if call.from_user.id == 1282559297:
                continue
            await bot.send_message(
                chat_id=bet_info_user,
                text='\n'.join(yml_local['new_bet_admin_info']).format(
                    't.me/' + call.from_user.username,
                    mc_nick[0],
                    diamonds_count,
                    f'{event} / {predict["title"]}',
                    predict[f'option{option}']
                ),
                parse_mode='html'
            )
        await cmd_menu(call.message)


@bot.callback_query_handler(func=lambda call: call.data == 'btn_my_bets')
@bot.message_handler(commands=['my_bets'])
async def my_bets(call: types.Message | types.CallbackQuery):
    if isinstance(call, types.Message):
        msg = call
        user = call.from_user
    else:
        msg = call.message
        user = call.from_user
        await bot.delete_message(msg.chat.id, msg.message_id)
    bets = await db_manager.get_all_values(
        DB_FILE,
        'PredictBets',
        '*'
    )
    bets = [dict(x) for x in bets]
    bets_txt = ''
    for i in range(len(bets)):
        if bets[i][str(user.id)] is None:
            continue
        predict = await db_manager.get_value(
            DB_FILE,
            'EventPredicts',
            'id',
            bets[i]['predict_id'],
            '*',
            sqlite3.Row
        )
        event_title = await db_manager.get_value(
            DB_FILE,
            'Events',
            'id',
            predict['event_id'],
            'title'
        )
        event_title = event_title[0]
        option = bets[i][str(user.id)].split(':')[0]
        option_title = predict[f'option{option}']
        bets_txt += yml_local['your_bet_format'].format(
            i + 1,
            event_title,
            predict['title'],
            option_title,
            bets[i][str(user.id)].split(':')[1]
        )
    if bets_txt == '':
        bets_txt = yml_local['no_bets']
    txt = '\n'.join(yml_local['list_of_your_bets']).format(bets_txt)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='Назад', callback_data='menu'))
    await bot.send_message(chat_id=msg.chat.id, text=txt, reply_markup=markup, parse_mode='html')


@bot.message_handler(func=lambda msg: msg.text.startswith('!admin'))
async def wcmd_admin(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    await bot.send_message(int(msg.text.split()[1]), text='Я тебя вижу:)')


@bot.message_handler(func=lambda msg: msg.text.startswith('!get_date'))
async def wcmd_get_date(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    await bot.send_message(msg.chat.id, text=datetime.datetime.now().strftime(DATE_FORMAT))


@bot.message_handler(func=lambda msg: msg.text.startswith('!add_money'))
async def wcmd_add_money(msg: types.Message):
    try:
        money = int(msg.text.split()[1])
    except:
        return
    user_balance = await db_manager.get_value(
        DB_FILE,
        'Users',
        'tg_id',
        msg.chat.id,
        'diamonds'
    )
    user_balance = user_balance[0] + money
    await db_manager.execute(
            DB_FILE,
            f'UPDATE Users SET diamonds = ? WHERE tg_id = ?',
            (user_balance, msg.from_user.id)
    )


@bot.message_handler(func=lambda msg: msg.text.startswith('!my_tg_id'))
async def wcmd_my_tg_id(msg: types.Message):
    await bot.send_message(chat_id=msg.chat.id, text=str(msg.from_user.id))


@bot.message_handler(func=lambda msg: msg.text.startswith('!add_event'))
async def wcmd_add_event(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    args = msg.text.split()
    if len(args) - 1 < 2:
        await bot.send_message(
            chat_id=msg.chat.id,
            text=yml_local['wrong_args']
        )
    event_id = args[1]
    title = ' '.join(args[2:])
    try:
        await db_manager.add_value(
            DB_FILE,
            'Events',
            [event_id, title]
        )
    except Exception as e:
        code = rd.randint(1, 1000)
        print(f'Exception: {e}. Values: {event_id};{title}. Error ID: {code}')
        await bot.send_message(
            chat_id=msg.chat.id,
            text=f'Произошла ошибка. Обратитесь к разработчику с ID ошибки: {code}'
        )
    else:
        await bot.send_message(
            chat_id=msg.chat.id,
            text=f'Успешно добавлен ивент {title} с ID {event_id}'
        )


@bot.message_handler(func=lambda msg: msg.text.startswith('!add_prediction')) #
async def wcmd_add_prediction(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return


@bot.message_handler(func=lambda msg: msg.text.startswith('!set_bot_state'))
async def wcmd_set_bot_state(msg: types.Message):
    if not is_admin(msg.from_user.id):
        return
    state = msg.text.split()[1]
    match state:
        case 'enabled':
            ...
        case 'disabled':
            ...
        case _:
            await bot.send_message(chat_id=msg.chat.id, text=yml_local['wrong_args'])


@bot.callback_query_handler(func=lambda call: call.data == 'btn_support')
@bot.message_handler(commands=['support'])
async def support(call: types.Message | types.CallbackQuery):
    if isinstance(call, types.Message):
        msg = call
        user = call.from_user
    else:
        msg = call.message
        user = call.from_user
        await bot.delete_message(chat_id=msg.chat.id, message_id=msg.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text='➕Создать обращение', callback_data='support_ticket_create'))
    user_tickets = await db_manager.get_all_values(
        DB_FILE,
        'SupportTickets',
        'sender_id',
        str(user.id),
        '*'
    )
    user_tickets = [dict(x) for x in user_tickets]
    print(user_tickets)
    for ticket in user_tickets:
        markup.add(types.InlineKeyboardButton(
            text=f'{ticket["title"]} ({ticket["status"]} | {ticket["send_date"]})',
            callback_data=f'support_edit_ticket:{ticket["id"]}'
        ))
    markup.add(types.InlineKeyboardButton('Назад', callback_data='menu'))
    await bot.send_message(
        chat_id=msg.chat.id,
        text='\n'.join(yml_local['support_menu']),
        reply_markup=markup,
        parse_mode='html'
    )


async def make_result_predicts(predict: dict):
    win_option = predict['win_option']
    all_users_bets = await db_manager.get_all_values(
        DB_FILE,
        'PredictBets',
        'predict_id',
        str(predict['id']),
        '*'
    )
    all_users_bets = [dict(x) for x in all_users_bets][0]
    all_users_bets.pop('predict_id')
    user_ids = list(all_users_bets.keys())
    for user_id in user_ids:
        user_bet = all_users_bets[user_id].split(':')
        user_bet_option = int(user_bet[0])
        user_bet_diamonds = int(user_bet[1])
        user_balance = await db_manager.get_value(
            DB_FILE,
            'Users',
            'tg_id',
            user_id,
            'diamonds'
        )
        user_balance = user_balance[0]
        diamonds_user_option = predict[f'sum_option{user_bet_option}']
        diamonds_total = predict[f'sum_option1'] + predict[f'sum_option2']
        percentage = diamonds_user_option / diamonds_total * 100
        multiplier = 100 / percentage
        multiplier = round(multiplier, 2)
        print(f'Процентов за эту опцию {percentage}')
        print(f'Коэфициент X{multiplier}')
        if user_bet_option == win_option:  # win
            print(f'Комиссия {COMMISSION}%')
            print(f'Выигрыш {(user_bet_diamonds * multiplier) * (100 - COMMISSION) * 0.01}')
            user_balance += user_bet_diamonds * multiplier
        else:  # lose
            print(f'Проигрыш {user_bet_diamonds}')
        user_ids.remove(user_id)
        if len(user_ids) < 1:
            print(f'Полностью удалено')
            await db_manager.execute(
                DB_FILE,
                f'DELETE FROM PredictBets WHERE predict_id = ?',
                (predict['id'],)
            )
            await db_manager.execute(
                DB_FILE,
                f'DELETE FROM EventPredicts WHERE id = ?',
                (predict['id'],)
            )


async def update_cycle():
    while True:
        await asyncio.sleep(2)
        events_list = await db_manager.get_all_values(DB_FILE, 'Events', '*')
        events_list = [dict(_e) for _e in events_list]
        for event in events_list:
            predicts_list = await db_manager.get_all_values(DB_FILE, 'EventPredicts', 'event_id', str(event['id']), '*')
            predicts_list = [dict(_p) for _p in predicts_list]
            for predict in predicts_list:
                end_date = datetime.datetime.strptime(predict['date_end_predicts'], DATE_FORMAT)
                now = datetime.datetime.now()
                if now >= end_date:
                    print(f'Found predict with date after end: {predict["title"]} with id {predict["id"]}')
                    print('Making result...')
                    try:
                        task1 = asyncio.create_task(make_result_predicts(predict))
                        await task1
                    except Exception as e:
                        print(type(e), e)


async def main():
    bot.add_custom_filter(async_telebot.asyncio_filters.StateFilter(bot))
    task1 = asyncio.create_task(bot.infinity_polling(timeout=None))
    task2 = asyncio.create_task(db_manager.init_db(DB_FILE))
    task3 = asyncio.create_task(update_cycle())
    await task1
    await task2
    await task3


asyncio.run(main())
