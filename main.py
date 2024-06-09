from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from envars_etc import token, crash_report, remove_linebreaks, whitelist, adminlist, sql_password, sql_host, \
    sql_user_name, sql_db_name
from colorama import Fore
import psycopg2
import colorama


db_config = {
    "host": sql_host,
    "user": sql_user_name,
    "password": sql_password,
    "dbname": sql_db_name
}

active_dict = {}

def update_white_list():
    with open(whitelist) as wl:
        workers = remove_linebreaks(wl)
    return workers

def update_admin_list():
    with open(adminlist) as al:
        admins = remove_linebreaks(al)
    return admins

def start():
    colorama.init(autoreset=False)

    class WorkerPost(StatesGroup):
        item_name = State()
        item_count = State()
        take_item = State()
        new_item_name = State()
        new_item_count = State()
        delete_item = State()
        add_id = State()
        delete_id = State()

    bot = Bot(token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text='/id Дізнатися свій ID')],
            [KeyboardButton(text='/edit Редагувати записи')],
            [KeyboardButton(text='/print_all Перегляд кількості всіх предметів')],
            [KeyboardButton(text='/print Перегляд кількості предмету')],
            [KeyboardButton(text='/add_id [A] Додати працівника')],
            [KeyboardButton(text='/delete_id [A] видалити працівника')],
            [KeyboardButton(text='/add [A] Додати запис')],
            [KeyboardButton(text='/delete [A] Видалити запис')]
        ],
        resize_keyboard=True
    )

    @dp.message(Command('start'))
    async def start_cmd(mess: types.Message):
        await mess.answer(
            'Щоб отримати свій id: /id\nЗверніться до адміністратора щоб вас внесли у білий список', reply_markup=kb)

    @dp.message(Command('id'))
    async def id_cmd(mess: types.Message):
        await mess.answer(f'Ваш ID: `{mess.chat.id}`', parse_mode="MARKDOWN")

    @dp.message(Command('print_all'))
    async def print_all_cmd(mess: types.Message):
        if str(mess.chat.id) in update_white_list():
            with psycopg2.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute('SELECT item_name, count FROM items;')
                    all_items = cursor.fetchall()
                    items_str = '\n'.join(f'{item_name}: {count}' for item_name, count in all_items)
            await mess.answer(items_str)
        else:
            await mess.answer('Ваш ID не знаходиться у списку робітників. Звʼяжіться з адміністратором')

    @dp.message(Command('print'))
    async def print_cmd(mess: types.Message):
        if str(mess.chat.id) in update_white_list():
            await mess.answer('Назва товару:')
            await dp.fsm.start_state(WorkerPost.take_item)
        else:
            await mess.answer('Ваш ID не знаходиться у списку робітників. Звʼяжіться з адміністратором')

    @dp.message(F.text, WorkerPost.take_item)
    async def take_item(mess: types.Message, state: FSMContext):
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT item_name, count FROM items WHERE item_name = '{mess.text}';")
                result = cursor.fetchone()
                if result:
                    await mess.answer(f'{result[0]}: {result[1]}')
                else:
                    await mess.answer('Невірне імʼя предмету')
        await state.clear()

    @dp.message(Command('edit'))
    async def edit_cmd(mess: types.Message):
        if str(mess.chat.id) in update_white_list():
            active_dict[mess.chat.id] = []
            await mess.answer('Назва товару:')
            await dp.fsm.start_state(WorkerPost.item_name)
        else:
            await mess.answer('Ваш ID не знаходиться у списку робітників. Звʼяжіться з адміністратором')

    @dp.message(F.text, WorkerPost.item_name)
    async def item_name(mess: types.Message, state: FSMContext):
        active_dict[mess.chat.id].append(mess.text)
        await mess.answer('Кількість моментом на зараз:')
        await dp.fsm.start_state(WorkerPost.item_count)

    @dp.message(F.text, WorkerPost.item_count)
    async def item_count(mess: types.Message, state: FSMContext):
        try:
            count = int(mess.text)
            active_dict[mess.chat.id].append(count)
            with psycopg2.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE items SET count = {count} WHERE item_name = '{active_dict[mess.chat.id][0]}';")
            await mess.answer('Кількість товару успішно відредагована!')
        except Exception as ex:
            await mess.answer('Сталася помилка')
            crash_report(ex)
        finally:
            active_dict.pop(mess.chat.id, None)
            await state.clear()

    @dp.message(Command('add'))
    async def add_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            active_dict[mess.chat.id] = []
            await mess.answer('Назва товару:')
            await dp.fsm.start_state(WorkerPost.new_item_name)
        else:
            await mess.answer('Ви не адміністратор')

    @dp.message(F.text, WorkerPost.new_item_name)
    async def new_item_name(mess: types.Message, state: FSMContext):
        active_dict[mess.chat.id].append(mess.text)
        await mess.answer('Кількість моментом на зараз:')
        await dp.fsm.start_state(WorkerPost.new_item_count)

    @dp.message(F.text, WorkerPost.new_item_count)
    async def new_item_count(mess: types.Message, state: FSMContext):
        try:
            count = int(mess.text)
            active_dict[mess.chat.id].append(count)
            with psycopg2.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO items (item_name, count) VALUES ('{active_dict[mess.chat.id][0]}', {count});")
            await mess.answer('Товар було додано!')
        except Exception as ex:
            await mess.answer('Сталася помилка')
            crash_report(ex)
        finally:
            active_dict.pop(mess.chat.id, None)
            await state.clear()

    @dp.message(Command('delete'))
    async def remove_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            await mess.answer('Назва товару:')
            await dp.fsm.start_state(WorkerPost.delete_item)
        else:
            await mess.answer('Ви не адміністратор')

    @dp.message(F.text, WorkerPost.delete_item)
    async def delete_item(mess: types.Message, state: FSMContext):
        try:
            with psycopg2.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DELETE FROM items WHERE item_name = '{mess.text}';")
                    await mess.answer('Товар було видалено!')
        except Exception as ex:
            await mess.answer('Сталася помилка')
            crash_report(ex)
        finally:
            await state.clear()

    @dp.message(Command('add_id'))
    async def add_id_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            await mess.answer('ID працівника:')
            await dp.fsm.start_state(WorkerPost.add_id)
        else:
            await mess.answer('Ви не адміністратор')

    @dp.message(F.text, WorkerPost.add_id)
    async def add_id(mess: types.Message, state: FSMContext):
        try:
            with open(whitelist, 'a+') as wl:
                wl.write(f'\n{mess.text}')
                await mess.answer('ID працівника додано')
        except Exception as ex:
            await mess.answer('Сталася помилка')
            crash_report(ex)
        finally:
            await state.clear()

    @dp.message(Command('delete_id'))
    async def delete_id_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            await mess.answer('ID працівника:')
            await dp.fsm.start_state(WorkerPost.delete_id)
        else:
            await mess.answer('Ви не адміністратор')

    @dp.message(F.text, WorkerPost.delete_id)
    async def delete_id(mess: types.Message, state: FSMContext):
        try:
            white_list = update_white_list()
            if mess.text in white_list:
                white_list.remove(mess.text)
                with open(whitelist, 'w') as wl:
                    wl.write('\n'.join(white_list))
                await mess.answer('ID працівника видалено')
            else:
                await mess.answer('Цього ID нема в списку')
        except Exception as ex:
            await mess.answer('Сталася помилка')
            crash_report(ex)
        finally:
            await state.clear()

    print(f'{Fore.WHITE}[{Fore.GREEN}OK]{Fore.WHITE} Started')
    dp.run_polling(bot)
    print(f'{Fore.WHITE}[{Fore.GREEN}OK]{Fore.WHITE} Bye!')

if __name__ == '__main__':
    try:
        start()
    except Exception as e:
        crash_report(e)
