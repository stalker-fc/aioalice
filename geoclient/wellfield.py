import logging

from aiohttp import web
from aioalice import Dispatcher, get_new_configured_app, types
from aioalice.dispatcher import MemoryStorage
from aioalice.utils.helper import Helper, HelperMode, Item
from geoclient.http_client import get_app_versions_from_geoclient, get_wellfields_from_geoclient, is_wellfield_exist, create_wellfield
WEBHOOK_URL_PATH = '/'  # webhook endpoint

WEBAPP_HOST = 'localhost'
WEBAPP_PORT = 1337


logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO)

# Создаем экземпляр диспетчера и подключаем хранилище в памяти
dp = Dispatcher(storage=MemoryStorage())

YES = 'Да'
NO = 'Нет'
YES_NO = [YES, NO]

HELP = ['Помощь']

# Можно использовать класс Helper для хранения списка состояний
class CreationState(Helper):
    mode = HelperMode.snake_case

    LICENSE_AGREEMENT = Item()
    NEED_WELLFIELD = Item()
    SELECT_APP_VERSION = Item()
    SELECT_WELLFIELD = Item()
    INSERT_PREFIX = Item()
    CONFIRM_WELLFIELD_CREATION = Item()
    CREATE_WELLFIELD = Item()



def get_app_versions():
    # return get_app_versions_from_geoclient()
    return ['developing', 'staging', 'releasing']


def get_wellfields():
    # return get_wellfields_from_geoclient()
    return ['Месторождение 1', 'Месторождение 2', 'Месторождение 3']

@dp.request_handler(contains=['отмена'])
async def cancel_operation(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.reset_state(user_id)
    return alice_request.response('Хорошо, прекращаем.')


@dp.request_handler(state=CreationState.SELECT_APP_VERSION, contains=get_app_versions())
async def select_app_version(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.update_data(user_id, app_version=alice_request.request.command)
    text = 'Отлично! Теперь выбери месторождение которое ты хочешь создать.'
    await dp.storage.set_state(user_id, CreationState.SELECT_WELLFIELD)
    return alice_request.response(text, buttons=get_wellfields())


@dp.request_handler(state=CreationState.SELECT_APP_VERSION)
async def select_app_version_not_in_list(alice_request):
    return alice_request.response(
        'Такой версии приложения у нас нет :(\nВыбери одну из списка!',
        buttons=get_app_versions()
    )


@dp.request_handler(state=CreationState.SELECT_WELLFIELD, contains=get_wellfields())
async def select_wellfield(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.update_data(user_id, wellfield=alice_request.request.command)
    text = 'Теперь назови имя того, для кого нужно создать месторождение.'
    await dp.storage.set_state(user_id, CreationState.INSERT_PREFIX)
    return alice_request.response(text)


@dp.request_handler(state=CreationState.SELECT_WELLFIELD)
async def select_wellfield_not_in_list(alice_request):
    return alice_request.response(
        'Такого месторождения не существует :(\nВыбери одно из списка!',
        buttons=get_app_versions()
    )


@dp.request_handler(state=CreationState.INSERT_PREFIX)
async def insert_prefix(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.update_data(user_id, prefix=alice_request.request.command)
    data = await dp.storage.get_data(user_id)
    text = f'Вы точно хотите создать месторождение:\n "[ {data["prefix"]} ] {data["wellfield"]}" \nна {data["app_version"]}-версии приложения?'
    await dp.storage.set_state(user_id, CreationState.CONFIRM_WELLFIELD_CREATION)
    return alice_request.response(text, buttons=['Да', 'Нет'])


@dp.request_handler(state=CreationState.CONFIRM_WELLFIELD_CREATION, contains=YES_NO)
async def insert_prefix(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command
    buttons = []
    if command == 'Да':
        data = await dp.storage.get_data(user_id)
        if is_wellfield_exist(data["app_version"], data["prefix"], data["wellfield"]):
            text = 'Это месторождение уже существует в базе данных. Создать его заново?'
            await dp.storage.set_state(user_id, CreationState.CREATE_WELLFIELD)
            buttons=YES_NO
        else:
            text = 'Начинаем инициализировать месторождение...\n Ожидаемое время инициализации 7-10 минут.'
            await dp.storage.reset_state(user_id)
    else:
        text = 'Не инициализируем месторождение.'
        await dp.storage.reset_state(user_id)

    return alice_request.response(text, buttons=buttons)

@dp.request_handler(state=CreationState.CONFIRM_WELLFIELD_CREATION)
async def insert_prefix(alice_request):
    return alice_request.response(
        'Я тебя не поняла :( \nСкажи да или нет.',
        buttons=YES_NO
    )

@dp.request_handler(state=CreationState.CREATE_WELLFIELD, contains=YES_NO)
async def insert_prefix(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command
    await dp.storage.reset_state(user_id)
    if command == 'Да':
        data = await dp.storage.get_data(user_id)
        create_wellfield(data["app_version"], data["prefix"], data["wellfield"])
        text = 'Начинаем инициализировать месторождение...\n Ожидаемое время инициализации 7-10 минут.'
    else:
        text = 'Не инициализируем месторождение.'

    return alice_request.response(text)

@dp.request_handler(state=CreationState.CREATE_WELLFIELD)
async def insert_prefix(alice_request):
    return alice_request.response(
        'Я тебя не поняла :( \nСкажи да или нет.',
        buttons=YES_NO
    )


@dp.request_handler(state=CreationState.LICENSE_AGREEMENT, contains=YES_NO)
async def handle_any_request(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command
    if command == YES:
        buttons = get_app_versions()
        text = 'Выберите версию приложения, на которой будет создано месторождение.'
        await dp.storage.set_state(user_id, CreationState.SELECT_APP_VERSION)
        await dp.storage.update_data(user_id, license_agreement=True)
    else:
        buttons = []
        text = 'Использование навыка отменено.'
        await dp.storage.reset_state(user_id)
        await dp.storage.update_data(user_id, license_agreement=False)

       # Предлагаем пользователю список игр
    return alice_request.response(text, buttons=buttons)


@dp.request_handler(state=CreationState.LICENSE_AGREEMENT, contains=['Условия использования'])
async def insert_prefix(alice_request):
    return alice_request.response(
        'Данный навык является закрытым. Отвечая положительно,'
        'Вы подтверждаете, что знаете, что такое геоклиент '
        'и для чего используется этот навык. Продолжить использование?',
        buttons=YES_NO
    )


@dp.request_handler(state=CreationState.LICENSE_AGREEMENT)
async def insert_prefix(alice_request):
    return alice_request.response(
        'Пожалуйста, ответьте, согласны ли вы с условиями использования навыка.',
        buttons=[YES, NO, 'Условия использования']
    )


@dp.request_handler()
async def handle_any_request(alice_request):
    user_id = alice_request.session.user_id
    user_data = await dp.storage.get_data(user_id)
    agreement = user_data.get('license_agreement', False)
    # Если сессия новая, приветствуем пользователя
    if not agreement:
        text = 'Я умею создавать месторождения с использованием геоклиента!' \
               ' Данный навык является закрытым. Отвечая положительно, Вы подтверждаете, что знаете, что такое геоклиент ' \
               ' и для чего используется этот навык. Продолжить использование?'
        await dp.storage.set_state(user_id, CreationState.LICENSE_AGREEMENT)
        await dp.storage.update_data(user_id, license_agreement=False)
    else:
        text = 'Я умею создавать месторождения с использованием геоклиента! Создать новое месторождение?'
        await dp.storage.set_state(user_id, CreationState.NEED_WELLFIELD)

    if alice_request.session.new:
        text = 'Привет!' + text

    return alice_request.response(text, buttons=YES_NO)


if __name__ == '__main__':
    app = get_new_configured_app(dispatcher=dp, path=WEBHOOK_URL_PATH)
    web.run_app(app, host=WEBAPP_HOST, port=WEBAPP_PORT)
