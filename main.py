from aiogram import Bot, Dispatcher, executor, types
from envars_etc import token, crash_report, remove_linebreaks, whitelist, adminlist, sql_password, sql_host, \
    sql_user_name, sql_db_name
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup

import psycopg2

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
    disp = Dispatcher(bot=bot, storage=MemoryStorage())
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add('/id Дізнатися свій ID').add('/edit Редагувати записи').add('/print_all Перегляд кількості всіх предметів').add('/print Перегляд кількості предмету').add('/add_id [A] Додати працівника').add('/delete_id [A] видалити працівника').add('/add [A] Додати запис').add('/delete [A] Видалити запис')

    @disp.message_handler(commands=['start'])
    async def start_cmd(mess: types.Message):
        await mess.answer(
            'Щоб отримати свій id: /id\nЗверніться до адміністратора щоб вас внесли у білий список', reply_markup=kb)

    @disp.message_handler(commands=['id'])
    async def id_cmd(mess: types.Message):
        await mess.answer(f'Ваш ID: `{mess.chat.id}`', parse_mode="MARKDOWN")

    @disp.message_handler(commands=['print_all'])
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

    @disp.message_handler(commands=['print'])
    async def print_cmd(mess: types.Message):
        if str(mess.chat.id) in update_white_list():
            await mess.answer('Назва товару:')
            await WorkerPost.take_item.set()
        else:
            await mess.answer('Ваш ID не знаходиться у списку робітників. Звʼяжіться з адміністратором')

    @disp.message_handler(state=WorkerPost.take_item, content_types=types.ContentType.TEXT)
    async def take_item(mess: types.Message, state: FSMContext):
        with psycopg2.connect(**db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(f"SELECT item_name, count FROM items WHERE item_name = '{mess.text}';")
                result = cursor.fetchone()

                if result:
                    await mess.answer(f'{result[0]}: {result[1]}')

                else:
                    await mess.answer('Невірне імʼя предмету')

        await state.finish()

    @disp.message_handler(commands=['edit'])
    async def edit_cmd(mess: types.Message):
        if str(mess.chat.id) in update_white_list():
            active_dict[mess.chat.id] = []
            await mess.answer('Назва товару:')
            await WorkerPost.item_name.set()
        else:
            await mess.answer('Ваш ID не знаходиться у списку робітників. Звʼяжіться з адміністратором')

    @disp.message_handler(state=WorkerPost.item_name, content_types=types.ContentType.TEXT)
    async def item_name(mess: types.Message, state: FSMContext):
        active_dict[mess.chat.id].append(mess.text)
        await mess.answer('Кількість моментом на зараз:')
        await WorkerPost.item_count.set()

    @disp.message_handler(state=WorkerPost.item_count, content_types=types.ContentType.TEXT)
    async def item_count(mess: types.Message, state: FSMContext):
        try:
            count = int(mess.text)
            active_dict[mess.chat.id].append(count)
            with psycopg2.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE items SET count = {count} WHERE item_name = '{active_dict[mess.chat.id][0]}';")
            await mess.answer('Кількість товару успішно відредагована!')

        except Exception as e:
            await mess.answer('Сталася помилка')
            crash_report(e)

        finally:
            active_dict.pop(mess.chat.id, None)
            await state.finish()

    @disp.message_handler(commands=['add'])
    async def add_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            active_dict[mess.chat.id] = []
            await mess.answer('Назва товару:')
            await WorkerPost.new_item_name.set()
        else:
            await mess.answer('Ви не адміністратор')

    @disp.message_handler(state=WorkerPost.new_item_name, content_types=types.ContentType.TEXT)
    async def new_item_name(mess: types.Message, state: FSMContext):
        active_dict[mess.chat.id].append(mess.text)
        await mess.answer('Кількість моментом на зараз:')
        await WorkerPost.new_item_count.set()

    @disp.message_handler(state=WorkerPost.new_item_count, content_types=types.ContentType.TEXT)
    async def new_item_count(mess: types.Message, state: FSMContext):
        try:
            count = int(mess.text)
            active_dict[mess.chat.id].append(count)
            with psycopg2.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"INSERT INTO items (item_name, count) VALUES ('{active_dict[mess.chat.id][0]}', {count});")
            await mess.answer('Товар було додано!')

        except Exception as e:
            await mess.answer('Сталася помилка')
            crash_report(e)

        finally:
            active_dict.pop(mess.chat.id, None)
            await state.finish()

    @disp.message_handler(commands=['delete'])
    async def remove_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            await mess.answer('Назва товару:')
            await WorkerPost.delete_item.set()
        else:
            await mess.answer('Ви не адміністратор')

    @disp.message_handler(state=WorkerPost.delete_item, content_types=types.ContentType.TEXT)
    async def delete_item(mess: types.Message, state: FSMContext):
        try:
            with psycopg2.connect(**db_config) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"DELETE FROM items WHERE item_name = '{mess.text}';")
                    await mess.answer('Товар було видалено!')

        except Exception as e:
            await mess.answer('Сталася помилка')
            crash_report(e)

        finally:
            await state.finish()

    @disp.message_handler(commands=['add_id'])
    async def add_id_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            await mess.answer('ID працівника:')
            await WorkerPost.add_id.set()
        else:
            await mess.answer('Ви не адміністратор')

    @disp.message_handler(state=WorkerPost.add_id, content_types=types.ContentType.TEXT)
    async def add_id(mess: types.Message, state: FSMContext):
        try:
            with open(whitelist, 'a+') as wl:
                wl.write(f'\n{mess.text}')
                await mess.answer('ID працівника додано')

        except Exception as e:
            await mess.answer('Сталася помилка')
            crash_report(e)

        finally:
            await state.finish()

    @disp.message_handler(commands=['delete_id'])
    async def delete_id_cmd(mess: types.Message):
        if str(mess.chat.id) in update_admin_list():
            await mess.answer('ID працівника:')
            await WorkerPost.delete_id.set()
        else:
            await mess.answer('Ви не адміністратор')

    @disp.message_handler(state=WorkerPost.delete_id, content_types=types.ContentType.TEXT)
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

        except Exception as e:
            await mess.answer('Сталася помилка')
            crash_report(e)

        finally:
            await state.finish()

    print('[OK] Started')
    executor.start_polling(dispatcher=disp)
    print('[OK] Bye!')


if __name__ == '__main__':
    try:
        start()
    
    except Exception as e:
        crash_report(e)
