import sqlite3
from multipledispatch import dispatch


async def init_db(file: str):
    con, c = await connect_db(file)
    c.execute('''
    CREATE TABLE IF NOT EXISTS Users (
    tg_id INTEGER PRIMARY KEY,
    diamonds INTEGER NOT NULL
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS Promocodes (
    tg_id INTEGER PRIMARY KEY,
    PPL9 INTEGER
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS Events (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS EventPredicts (
    id INTEGER PRIMARY KEY,
    event_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    option1 TEXT NOT NULL,
    option2 TEXT NOT NULL,
    users_option1 INTEGER NOT NULL,
    users_option2 INTEGER NOT NULL,
    date TEXT NOT NULL,
    date_end_predicts TEXT NOT NULL
    )
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS PredictBets (
    predict_id INTEGER PRIMARY KEY
    )
    ''')
    con.commit()
    con.close()


async def connect_db(file: str, row_factory=None):
    con = sqlite3.connect(file)
    if row_factory is not None:
        con.row_factory = row_factory
    c = con.cursor()
    return con, c


async def execute(file: str, sql: str, args: tuple = None):
    con, c = await connect_db(file)
    c.execute(sql, args)
    con.commit()
    con.close()


async def add_value(file: str, table: str, values: list):
    con, c = await connect_db(file)
    c.execute(f'INSERT INTO {table} VALUES (' + '?, '*(len(values)-1) + '?)', tuple(values))
    con.commit()
    con.close()


async def add_column(file: str, table: str, column: str):
    con, c = await connect_db(file)
    c.execute(f'ALTER TABLE {table} ADD {column}')
    con.commit()
    con.close()


async def get_value(file: str, table: str, primary_key: str, pkey_value, value: str, row_factory=None):
    con, c = await connect_db(file, row_factory=row_factory)
    c.execute(f'SELECT {value} FROM {table} WHERE {primary_key} = {pkey_value}')
    return c.fetchone()


@dispatch(str, str, str)
async def get_all_values(file: str, table: str, value: str):
    con, c = await connect_db(file, row_factory=sqlite3.Row)
    c.execute(f'SELECT {value} FROM {table}')
    return c.fetchall()


@dispatch(str, str, str, str, str)
async def get_all_values(file: str, table: str, primary_key: str, pkey_value: str, value: str):
    con, c = await connect_db(file, row_factory=sqlite3.Row)
    c.execute(f'SELECT {value} FROM {table} WHERE {primary_key} = {pkey_value}')
    return c.fetchall()


async def register_user(file: str, tg_id: int):
    await add_column(file, 'PredictBets', f'\"{tg_id}\"')
    await add_value(file, 'Users', [tg_id, 0])
