"""Обработчики сообщений и коллбэков бота."""

import re
import logging
import time
from typing import Any, Dict, List, Optional

# Конфигурация будет загружаться через менеджер конфигурации
from api import TelegramAPI
from state import StateStore
from menu import (
    build_giveaway_keyboard,
    build_main_menu,
    build_main_reply_keyboard,
    format_stand_status,
    get_motivational_message,
    create_progress_bar,
    main_menu_text,
    get_stand_status,
    get_completed_count,
    set_stand_status,
    get_total_stands_count
)
from user import ensure_main_menu, ensure_giveaway_menu

logger = logging.getLogger('bot.handlers')

# Импорт config_manager напрямую
from config_manager import config_manager

# Глобальные переменные (будут инициализированы в main)
API_CLIENT: Optional[TelegramAPI] = None
state_store: Optional[StateStore] = None

def set_api_client(client: TelegramAPI) -> None:
    global API_CLIENT
    API_CLIENT = client

def set_state_store(store: StateStore) -> None:
    global state_store
    state_store = store

def call_api(method: str, params: Optional[Dict[str, Any]] = None) -> Any:
    if API_CLIENT is None:
        raise RuntimeError('API client is not configured. Call set_api_client first.')
    return API_CLIENT.request(method, params)

def get_updates(offset: Optional[int]) -> List[Dict[str, Any]]:
    params = {'timeout': 30}
    if offset is not None:
        params['offset'] = offset
    try:
        return call_api('getUpdates', params)
    except RuntimeError as exc:
        print(f'[polling] Error: {exc}')
        time.sleep(5)
        return []

def send_message(chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None, parse_mode: Optional[str] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        params['reply_markup'] = reply_markup
    if parse_mode:
        params['parse_mode'] = parse_mode
    return call_api('sendMessage', params)

def edit_message(chat_id: int, message_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None, parse_mode: Optional[str] = None) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        'chat_id': chat_id,
        'message_id': message_id,
        'text': text,
    }
    if reply_markup:
        params['reply_markup'] = reply_markup
    if parse_mode:
        params['parse_mode'] = parse_mode
    return call_api('editMessageText', params)

def edit_message_reply_markup(chat_id: int, message_id: int, reply_markup: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        'chat_id': chat_id,
        'message_id': message_id,
        'reply_markup': reply_markup,
    }
    return call_api('editMessageReplyMarkup', params)

def answer_callback(callback_id: str, text: Optional[str] = None, show_alert: bool = False) -> None:
    params: Dict[str, Any] = {'callback_query_id': callback_id}
    if text:
        params['text'] = text
    if show_alert:
        params['show_alert'] = True
    call_api('answerCallbackQuery', params)

def handle_start(chat_id: int, user: Dict[str, Any]) -> None:
    user['awaiting_name'] = True
    user['pending_question'] = None

    welcome_text = (
        '🎉 *Добро пожаловать на Sfedunet 12!*\n\n'
        '👋 Привет! Я ваш помощник на фестивале.\n\n'
        '📝 *Для начала, давайте знакомиться!*\n'
        'Пожалуйста, введите ваше *имя и фамилию*:'
    )

    send_message(chat_id, welcome_text, parse_mode='Markdown')
    state_store.save()

def normalize_answer(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().lower())

def handle_vk_link(chat_id: int, user: Dict[str, Any], text: str) -> None:
    vk_pattern = config_manager.get('VK_LINK_PATTERN')
    if not vk_pattern.match(text.strip()):
        error_text = (
            '❌ *Ой! Ссылка некорректна*\n\n'
            '📝 *Правильный формат:*\n'
            '• `https://vk.com/username`\n'
            '• `vk.com/username`\n\n'
            '🔄 Попробуйте ещё раз:'
        )
        send_message(chat_id, error_text, parse_mode='Markdown')
        return

    normalized = text.strip()
    if not normalized.startswith('http'):
        normalized = 'https://' + normalized

    user['vk_profile'] = normalized
    user['vk_verified'] = True
    user['awaiting_vk_link'] = False

    success_text = (
        '✅ *Отлично! VK профиль добавлен*\n\n'
        f'🔗 {normalized}\n\n'
        '🎯 *Теперь пройдите все стенды* для участия в розыгрыше!'
    )

    send_message(chat_id, success_text, parse_mode='Markdown')
    ensure_main_menu(chat_id, user, edit_message, send_message)
    state_store.save()

def select_question(stand: Dict[str, Any]) -> Dict[str, Any]:
    import random
    return random.choice(stand['questions'])

def handle_stand_question(chat_id: int, user: Dict[str, Any], stand_id: str, stand_title: str) -> None:
    stands = config_manager.get('STANDS', [])
    stand = next((s for s in stands if s['id'] == stand_id), None)
    if not stand:
        send_message(chat_id, '❌ *Ошибка:* стенд не найден.', parse_mode='Markdown')
        return

    question = select_question(stand)
    user['pending_question'] = {
        'stand_id': stand_id,
        'stand_title': stand_title,
        'answers': question['answers'],
        'hint': question.get('hint', ''),
    }

    question_text = (
        f'{stand["emoji"]} *{stand_title}*\n\n'
        f'📖 _{stand["description"]}_\n\n'
        f'❓ *Вопрос:*\n{question["question"]}\n\n'
        f'✍️ *Напишите ваш ответ:*'
    )

    # Create inline keyboard with hint button
    keyboard = [[
        {'text': '💡 Подсказка', 'callback_data': f'HINT_{stand_id}'}
    ]]

    send_message(chat_id, question_text, reply_markup={'inline_keyboard': keyboard}, parse_mode='Markdown')
    state_store.save()

def handle_pending_answer(chat_id: int, user: Dict[str, Any], text: str) -> None:
    pending = user.get('pending_question')
    if not pending:
        return

    normalized = normalize_answer(text)
    answers = [normalize_answer(ans) for ans in pending['answers']]

    if normalized in answers:
        # Correct answer!
        completed_before = get_completed_count(user)
        set_stand_status(user, pending['stand_id'], True)
        user['pending_question'] = None
        completed_after = completed_before + 1

        # Get achievement message
        achievements = config_manager.get('ACHIEVEMENTS', {})
        achievement_text = ''
        if completed_after == 1:
            achievement_text = achievements.get('first_stand', '')
        elif completed_after == 2:
            achievement_text = achievements.get('half_complete', '')
        elif completed_after == 3:
            achievement_text = achievements.get('all_complete', '')

        success_text = (
            f'🎉 *Правильно!*\n\n'
            f'✅ Стенд *{pending["stand_title"]}* пройден!\n\n'
            f'{achievement_text}\n\n'
            f'📊 *Прогресс:* {completed_after}/{get_total_stands_count()} стендов'
        )

        # Обновляем reply клавиатуру
        reply_markup = build_main_reply_keyboard(user)
        send_message(chat_id, success_text, reply_markup=reply_markup, parse_mode='Markdown')

        # Обновляем inline меню
        ensure_main_menu(chat_id, user, edit_message, send_message)
        state_store.save()
    else:
        # Wrong answer
        wrong_text = (
            f'❌ *Не совсем так...*\n\n'
            f'🤔 Попробуйте ещё раз!\n'
            f'💡 Используйте кнопку "Подсказка" если нужна помощь.'
        )
        send_message(chat_id, wrong_text, parse_mode='Markdown')

def process_message(update: Dict[str, Any]) -> None:
    message = update.get('message') or update.get('edited_message')
    if not message:
        return
    chat = message.get('chat')
    if not chat or chat.get('type') != 'private':
        return
    chat_id = chat.get('id')
    if not chat_id:
        return
    user = state_store.get_user(chat_id)
    text = message.get('text', '')

    # Log incoming message
    logger.debug('Processing message from user %s: %s', chat_id, text)

    if text.startswith('/'):
        logger.info('Handling command from user %s: %s', chat_id, text)
        handle_start(chat_id, user)
        return

    if user['awaiting_name']:
        user['full_name'] = text.strip()
        user['awaiting_name'] = False
        logger.info('User %s registered with name: %s', chat_id, user['full_name'])

        achievements = config_manager.get('ACHIEVEMENTS', {})
        welcome_complete_text = (
            f'🎉 *Рады знакомству, {user["full_name"]}!*\n\n'
            f'{achievements.get("registration_complete", "")}\n\n'
            f'🎯 *Что вас ждет:*\n'
            f'• 📅 Расписание мероприятий\n'
            f'• 🔬 Интерактивные стенды\n'
            f'• 🎁 Розыгрыш крутых призов\n\n'
            f'🚀 *Готовы начать?*'
        )

        # Send welcome message with reply keyboard
        reply_markup = build_main_reply_keyboard(user)
        send_message(chat_id, welcome_complete_text, reply_markup=reply_markup, parse_mode='Markdown')
        ensure_main_menu(chat_id, user, edit_message, send_message)
        state_store.save()
        return

    if user['awaiting_vk_link']:
        logger.info('Handling VK link from user %s', chat_id)
        handle_vk_link(chat_id, user, text)
        return

    if user.get('pending_question'):
        logger.info('Handling answer from user %s for question %s', chat_id, user['pending_question']['stand_id'])
        handle_pending_answer(chat_id, user, text)
        return

    # Handle reply keyboard commands
    if text in ['📅 Расписание']:
        logger.info('User %s requested schedule', chat_id)
        schedule_text = config_manager.get('SCHEDULE_TEXT', 'Расписание недоступно')
        send_message(chat_id, schedule_text, parse_mode='Markdown')
        return
    elif text.startswith('🎁 Розыгрыш'):
        logger.info('User %s requested giveaway menu', chat_id)
        ensure_giveaway_menu(chat_id, user, edit_message, send_message)
        return
    elif text in ['🏆 Я УЧАСТВУЮ В РОЗЫГРЫШЕ! 🎉']:
        # This button should only appear when user is qualified
        completed_stands = get_completed_count(user)

        if user.get('vk_verified', False) and completed_stands == get_total_stands_count():
            logger.info('User %s completed all stands and qualified for giveaway', chat_id)
            celebration_text = (
                '🎉 *ПОЗДРАВЛЯЕМ!* 🎊\n\n'
                '🏆 *Вы успешно прошли все стенды и участвуете в розыгрыше!*\n\n'
                '🎁 *Призы ждут своих победителей:*\n'
                '• 🎧 Наушники премиум-класса\n'
                '• 📱 Гаджеты и аксессуары\n'
                '• 🎁 Мерч фестиваля\n'
                '• 🛍️ И многое другое!\n\n'
                '⏰ *Результаты розыгрыша* будут объявлены в конце мероприятия.\n\n'
                '🎪 А пока наслаждайтесь фестивалем!'
            )
        else:
            # Fallback message (shouldn't normally happen)
            logger.warning('User %s tried to access giveaway without completing requirements', chat_id)
            celebration_text = (
                '🤔 *Кажется, вы ещё не завершили все условия...*\n\n'
                '📋 *Для участия в розыгрыше нужно:*\n'
                '1️⃣ Добавить VK профиль\n'
                '2️⃣ Пройти все 3 стенда\n\n'
                '🎯 Используйте кнопку *"🎁 Розыгрыш"* для проверки прогресса!'
            )

        send_message(chat_id, celebration_text, parse_mode='Markdown')
        return
    elif text in ['📊 Мой прогресс']:
        logger.info('User %s requested progress', chat_id)
        stats_text = format_stand_status(user)
        send_message(chat_id, stats_text, parse_mode='Markdown')
        return
    elif text in ['❓ Помощь']:
        logger.info('User %s requested help', chat_id)
        help_text = (
            '❓ *Помощь по боту*\n\n'
            '🎯 *Как участвовать в розыгрыше:*\n'
            '1️⃣ Добавьте ссылку на VK профиль\n'
            '2️⃣ Пройдите все 3 стенда\n'
            '3️⃣ Ответьте правильно на вопросы\n\n'
            '💡 *Подсказки:*\n'
            '• Используйте кнопку "Подсказка" в вопросах\n'
            '• Следите за прогрессом в главном меню\n'
            '• Посещайте стенды в любом порядке\n\n'
            '🎮 *Навигация:*\n'
            '• Используйте кнопки внизу экрана\n'
            '• Или нажимайте на inline-кнопки в сообщениях\n\n'
            '🆘 *Нужна помощь?* Обратитесь к организаторам!'
        )
        send_message(chat_id, help_text, parse_mode='Markdown')
        return

    # Unknown message
    logger.warning('User %s sent unknown message: %s', chat_id, text)
    help_message = (
        '🤔 *Не понимаю что вы хотите...*\n\n'
        '💡 *Используйте кнопки меню* для навигации по боту.\n\n'
        '❓ Нажмите *"Помощь"* для получения инструкций.'
    )
    reply_markup = build_main_reply_keyboard(user)
    send_message(chat_id, help_message, reply_markup=reply_markup, parse_mode='Markdown')

def process_callback(update: Dict[str, Any]) -> None:
    callback = update.get('callback_query')
    if not callback:
        return
    data = callback.get('data', '')
    from_user = callback.get('from')
    if not from_user:
        return
    message = callback.get('message')
    if not message or not message.get('chat'):
        return
    chat_id = message['chat'].get('id')
    if not chat_id:
        return
    user = state_store.get_user(from_user['id'])

    # Log incoming callback
    logger.debug('Processing callback from user %s with data: %s', from_user['id'], data)

    if data == 'MAIN_SCHEDULE':
        logger.info('User %s requested main schedule', from_user['id'])
        answer_callback(callback.get('id', ''))
        schedule_text = config_manager.get('SCHEDULE_TEXT', 'Расписание недоступно')
        send_message(chat_id, schedule_text, parse_mode='Markdown')

    elif data == 'MAIN_GIVEAWAY':
        logger.info('User %s requested main giveaway menu', from_user['id'])
        answer_callback(callback.get('id', ''))
        ensure_giveaway_menu(chat_id, user, edit_message, send_message)

    elif data == 'MAIN_STATS':
        logger.info('User %s requested main stats', from_user['id'])
        answer_callback(callback.get('id', ''))
        stats_text = format_stand_status(user)
        send_message(chat_id, stats_text, parse_mode='Markdown')

    elif data == 'MAIN_HELP':
        logger.info('User %s requested main help', from_user['id'])
        answer_callback(callback.get('id', ''))
        help_text = (
            '❓ *Помощь по боту*\n\n'
            '🎯 *Как участвовать в розыгрыше:*\n'
            '1️⃣ Добавьте ссылку на VK профиль\n'
            '2️⃣ Пройдите все 3 стенда\n'
            '3️⃣ Ответьте правильно на вопросы\n\n'
            '💡 *Подсказки:*\n'
            '• Используйте кнопку "Подсказка" в вопросах\n'
            '• Следите за прогрессом в главном меню\n'
            '• Посещайте стенды в любом порядке\n\n'
            '🆘 *Нужна помощь?* Обратитесь к организаторам!'
        )
        send_message(chat_id, help_text, parse_mode='Markdown')

    elif data == 'GIVEAWAY_BACK':
        logger.info('User %s returned to main menu from giveaway', from_user['id'])
        answer_callback(callback.get('id', ''))
        ensure_main_menu(chat_id, user, edit_message, send_message)

    elif data == 'GIVEAWAY_PROGRESS':
        logger.info('User %s requested giveaway progress', from_user['id'])
        answer_callback(callback.get('id', ''))
        progress_text = format_stand_status(user)
        send_message(chat_id, progress_text, parse_mode='Markdown')

    elif data == 'GIVEAWAY_VK_LINK':
        logger.info('User %s requested VK link input', from_user['id'])
        answer_callback(callback.get('id', ''))
        if user['vk_verified']:
            send_message(chat_id, f'✅ *VK профиль уже добавлен:*\n{user["vk_profile"]}', parse_mode='Markdown')
        else:
            user['awaiting_vk_link'] = True
            state_store.save()
            vk_instruction = (
                '🔗 *Добавление VK профиля*\n\n'
                '📝 Отправьте ссылку на ваш профиль ВКонтакте.\n\n'
                '✅ *Примеры правильных ссылок:*\n'
                '• `https://vk.com/username`\n'
                '• `vk.com/username`\n\n'
                '✍️ *Напишите ссылку сообщением:*'
            )
            send_message(chat_id, vk_instruction, parse_mode='Markdown')

    elif data.startswith('HINT_'):
        logger.info('User %s requested hint for stand %s', from_user['id'], data.replace('HINT_', ''))
        answer_callback(callback.get('id', ''))
        stand_id = data.replace('HINT_', '')
        pending = user.get('pending_question')
        if pending and pending.get('stand_id') == stand_id and pending.get('hint'):
            send_message(chat_id, pending['hint'], parse_mode='Markdown')
        else:
            send_message(chat_id, '💡 Подсказка недоступна для этого вопроса.')

    elif data.startswith('STAND_INFO_'):
        logger.info('User %s requested info for stand %s', from_user['id'], data.replace('STAND_INFO_', ''))
        answer_callback(callback.get('id', ''))
        stand_id = data.replace('STAND_INFO_', '')
        stand = next((s for s in STANDS if s['id'] == stand_id), None)
        if stand:
            info_text = (
                f'{stand["emoji"]} *{stand["title"]} - ПРОЙДЕН!* ✅\n\n'
                f'📖 _{stand["description"]}_\n\n'
                f'🎉 *Поздравляем!* Вы успешно ответили на вопрос этого стенда.\n\n'
                f'📊 Посетите остальные стенды для завершения квеста!'
            )
            send_message(chat_id, info_text, parse_mode='Markdown')

    elif data.startswith('STAND_'):
        stand_id = data.replace('STAND_', '')
        stands = config_manager.get('STANDS', [])
        stand = next((s for s in stands if s['id'] == stand_id), None)
        if not stand:
            logger.warning('User %s tried to access non-existent stand %s', from_user['id'], stand_id)
            answer_callback(callback.get('id', ''), 'Стенд не найден.', show_alert=True)
            return
        if get_stand_status(user, stand_id)['done']:
            logger.info('User %s tried to access already completed stand %s', from_user['id'], stand_id)
            answer_callback(callback.get('id', ''), 'Этот стенд уже пройден!')
            return
        logger.info('User %s started stand %s', from_user['id'], stand_id)
        answer_callback(callback.get('id', ''))
        handle_stand_question(chat_id, user, stand_id, stand['title'])
    else:
        logger.warning('User %s sent unknown callback data: %s', from_user['id'], data)
        answer_callback(callback.get('id', ''))

def event_loop() -> None:
    offset = None
    print('[bot] Starting long polling loop.')
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update['update_id'] + 1
            if 'callback_query' in update:
                process_callback(update)
            else:
                process_message(update)
