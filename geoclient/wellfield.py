import logging
from aioalice import Dispatcher, get_new_configured_app, types
from aioalice.dispatcher import MemoryStorage
from aioalice.utils.helper import Helper, HelperMode, Item
from geoclient.http_client import get_app_versions_from_geoclient, get_wellfields_from_geoclient, is_wellfield_exist, \
    create_wellfield
from geoclient.text import *


logging.basicConfig(format=u'%(filename)s [LINE:%(lineno)d] #%(levelname)-8s [%(asctime)s]  %(message)s',
                    level=logging.INFO)

# Создаем экземпляр диспетчера и подключаем хранилище в памяти
dp = Dispatcher(storage=MemoryStorage())


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
    return INIT_VERSIONS


def get_wellfields():
    # return get_wellfields_from_geoclient()
    return INIT_WELLFIELDS


#try to create wellfield
@dp.request_handler(state=CreationState.CREATE_WELLFIELD, contains=YES_NO)
async def create_wellfield_confirm(alice_request):
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

@dp.request_handler(state=CreationState.CREATE_WELLFIELD, contains=HELP_COMMANDS)
async def create_wellfield_help(alice_request):
    return alice_request.response(
        REFERENCE,
        buttons=[CONTINUE_USING]
    )

@dp.request_handler(state=CreationState.CREATE_WELLFIELD)
async def create_wellfield_other(alice_request):
    user_id = alice_request.session.user_id
    data = await dp.storage.get_data(user_id)
    wf_name = f'[ {data["prefix"]} ] {data["wellfield"]}" \nна {data["app_version"]} версии приложения'
    return alice_request.response(
        'Если Вы хотите создать месторождение:\n'
        f' {wf_name},\n'
        ' то ответьте "Да". Для отмены ответьте "Нет".',
        buttons=[YES, NO]
    )

#try to confirm wellfield creation
@dp.request_handler(state=CreationState.CONFIRM_WELLFIELD_CREATION, contains=YES_NO)
async def confirm_wellfield_creation_confirm(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command
    buttons = []
    if command.lower() == YES.lower():
        data = await dp.storage.get_data(user_id)
        if is_wellfield_exist(data["app_version"], data["prefix"], data["wellfield"]):
            text = 'Это месторождение уже существует в базе данных. Создать его заново?'
            await dp.storage.set_state(user_id, CreationState.CREATE_WELLFIELD)
            buttons = YES_NO
        else:
            text = 'Начинаем инициализировать месторождение...\n Ожидаемое время инициализации 7-10 минут.'
            await dp.storage.reset_state(user_id)
    else:
        text = 'Использование навыка отменено.'
        await dp.storage.reset_state(user_id)

    return alice_request.response(text, buttons=buttons)


@dp.request_handler(state=CreationState.CONFIRM_WELLFIELD_CREATION, contains='Назвать имя заново')
async def confirm_wellfield_creation_repeat_name(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.set_state(user_id, CreationState.INSERT_PREFIX)
    return alice_request.response(
        'Пожалуйста назовите имя того, для кого требуется проинициализировать месторождение.')


@dp.request_handler(state=CreationState.CONFIRM_WELLFIELD_CREATION, contains=HELP_COMMANDS)
async def confirm_wellfield_creation_help(alice_request):
    return alice_request.response(
        REFERENCE,
        buttons=[CONTINUE_USING]
    )


@dp.request_handler(state=CreationState.CONFIRM_WELLFIELD_CREATION)
async def confirm_wellfield_creation_other(alice_request):
    user_id = alice_request.session.user_id
    data = await dp.storage.get_data(user_id)
    wf_name = f'[ {data["prefix"]} ] {data["wellfield"]}" \nна {data["app_version"]} версии приложения'
    return alice_request.response(
        'Если Вы хотите создать месторождение:\n'
        f' {wf_name},\n'
        ' то ответьте "Да". Для отмены ответьте "Нет".',
        buttons=[YES, NO]
    )


#try to choose prefix
@dp.request_handler(state=CreationState.INSERT_PREFIX, contains=HELP_COMMANDS)
async def insert_prefix_help(alice_request):
    return alice_request.response(
        REFERENCE,
        buttons=[CONTINUE_USING]
    )

@dp.request_handler(state=CreationState.INSERT_PREFIX)
async def insert_prefix_name(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.update_data(user_id, prefix=alice_request.request.command)
    data = await dp.storage.get_data(user_id)
    text = f'Вы точно хотите создать месторождение:\n "[ {data["prefix"]} ] ' \
        f'{data["wellfield"]}" \nна {data["app_version"]} версии приложения?'
    await dp.storage.set_state(user_id, CreationState.CONFIRM_WELLFIELD_CREATION)
    return alice_request.response(text, buttons=[YES, NO, 'Назвать имя заново'])



#try to choose wellfield
@dp.request_handler(state=CreationState.SELECT_WELLFIELD, contains=get_wellfields())
async def select_wellfield_version(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.update_data(user_id, wellfield=alice_request.request.command)
    text = 'Пожалуйста, назовите имя того, для кого нужно создать месторождение.'
    await dp.storage.set_state(user_id, CreationState.INSERT_PREFIX)
    return alice_request.response(text)


@dp.request_handler(state=CreationState.SELECT_WELLFIELD, contains=HELP_COMMANDS)
async def select_wellfield_help(alice_request):
    return alice_request.response(
        REFERENCE,
        buttons=[CONTINUE_USING]
    )

@dp.request_handler(state=CreationState.SELECT_WELLFIELD, contains=CONTINUE)
async def select_wellfield_continue(alice_request):
    text = 'Какое месторождение будем создавать?'
    buttons = get_wellfields()
    return alice_request.response(text, buttons=buttons)


@dp.request_handler(state=CreationState.SELECT_WELLFIELD, contains=CANCEL)
async def select_wellfield_cancel(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.reset_state(user_id)
    return alice_request.response('Использование навыка отменено.')


@dp.request_handler(state=CreationState.SELECT_WELLFIELD)
async def select_wellfield_other(alice_request):
    return alice_request.response(
        'Если Вы хотите создать месторождение, '
        'то Вам нужно выбрать одно из доступных к инициализации месторождений. ',
        buttons=[CONTINUE, CANCEL]
    )

#try to choose application version
@dp.request_handler(state=CreationState.SELECT_APP_VERSION, contains=get_app_versions())
async def select_app_version(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.update_data(user_id, app_version=alice_request.request.command)
    text = 'Отлично! Теперь выберите месторождение, которое Вы хотите создать.'
    await dp.storage.set_state(user_id, CreationState.SELECT_WELLFIELD)
    return alice_request.response(text, buttons=get_wellfields())


@dp.request_handler(state=CreationState.SELECT_APP_VERSION, contains=HELP_COMMANDS)
async def select_app_help(alice_request):
    return alice_request.response(
        REFERENCE,
        buttons=[CONTINUE_USING]
    )


@dp.request_handler(state=CreationState.SELECT_APP_VERSION, contains=CONTINUE)
async def select_app_continue(alice_request):
    text = 'На какой версии приложения будем создавать месторождение?'
    buttons = get_app_versions()
    return alice_request.response(text, buttons=buttons)


@dp.request_handler(state=CreationState.SELECT_APP_VERSION, contains=CANCEL)
async def select_app_cancel(alice_request):
    user_id = alice_request.session.user_id
    await dp.storage.reset_state(user_id)
    return alice_request.response(
        'Использование навыка отменено.')


@dp.request_handler(state=CreationState.SELECT_APP_VERSION)
async def select_app_other(alice_request):
    return alice_request.response(
        'Если Вы хотите создать месторождение, '
        'то Вам нужно выбрать одну из доступных версий приложения. ',
        buttons=[CONTINUE, CANCEL]
    )


# try to create wellfield
@dp.request_handler(state=CreationState.NEED_WELLFIELD, contains=YES_NO_CANCEL)
async def need_wellfield(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command
    if command.lower() == YES.lower():
        text = 'На какой версии приложения будем создавать месторождение?'
        buttons = get_app_versions()
        await dp.storage.set_state(user_id, CreationState.SELECT_APP_VERSION)
    else:
        buttons = []
        text = 'Использование навыка отменено.'
        await dp.storage.reset_state(user_id)

    return alice_request.response(text, buttons=buttons)


@dp.request_handler(state=CreationState.NEED_WELLFIELD, contains=HELP_COMMANDS)
async def need_wellfield_help(alice_request):
    return alice_request.response(
        REFERENCE,
        buttons=[CONTINUE_USING]
    )

@dp.request_handler(state=CreationState.NEED_WELLFIELD)
async def need_wellfield_other(alice_request):
    return alice_request.response(
        'Если Вы хотите создать месторождение, то ответьте "Да", '
        'а если нет, то это всегда можно сделать в любое другое время. '
        'Создать новое месторождение?',
        buttons=[YES, NO]
    )


# license agreeement
@dp.request_handler(state=CreationState.LICENSE_AGREEMENT, contains=YES_NO)
async def license_confirm(alice_request):
    user_id = alice_request.session.user_id
    command = alice_request.request.command
    if command.lower() == YES.lower():
        text = 'Создать новое месторождение?'
        await dp.storage.set_state(user_id, CreationState.NEED_WELLFIELD)
        await dp.storage.update_data(user_id, license_agreement=True)
        buttons = YES_NO
    else:
        buttons = []
        text = 'Использование навыка отменено.'
        await dp.storage.reset_state(user_id)
        await dp.storage.update_data(user_id, license_agreement=False)

    # Предлагаем пользователю список игр
    return alice_request.response(text, buttons=buttons)


@dp.request_handler(state=CreationState.LICENSE_AGREEMENT, contains=['Условия использования'])
async def license_message(alice_request):
    return alice_request.response(
        LICENSE_MESSAGE,
        buttons=YES_NO
    )


@dp.request_handler(state=CreationState.LICENSE_AGREEMENT)
async def license_other(alice_request):
    return alice_request.response(
        'Для дальнейшего использования, пожалуйста, ответьте, согласны ли Вы с условиями использования навыка.',
        buttons=[YES, NO, 'Условия использования']
    )


# start message
@dp.request_handler()
async def handle_any_request(alice_request):
    user_id = alice_request.session.user_id
    user_data = await dp.storage.get_data(user_id)
    agreement = user_data.get('license_agreement', False)
    # Если сессия новая, приветствуем пользователя
    print(user_data)
    if not agreement:
        text = 'Я умею создавать месторождения с использованием геоклиента! ' + LICENSE_MESSAGE

        await dp.storage.set_state(user_id, CreationState.LICENSE_AGREEMENT)
        await dp.storage.update_data(user_id, license_agreement=False)
    else:
        text = 'Я умею создавать месторождения с использованием геоклиента! Создать новое месторождение?'
        await dp.storage.set_state(user_id, CreationState.NEED_WELLFIELD)

    if alice_request.session.new:
        text = HELLO + ' ' + text

    return alice_request.response(text, buttons=YES_NO)
