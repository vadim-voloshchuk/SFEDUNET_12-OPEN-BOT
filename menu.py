"""Функции для работы с меню и интерфейсом бота."""

import logging
from typing import Any, Dict

# Конфигурация будет получаться через глобальную переменную
from config_manager import config_manager

logger = logging.getLogger('bot.menu')

def get_stand_status(user: Dict[str, Any], stand_id: str) -> Dict[str, Any]:
    """Safely gets stand status for a user, returning default if missing."""
    if 'stand_status' not in user:
        return {'done': False}
    return user['stand_status'].get(stand_id, {'done': False})

def get_completed_count(user: Dict[str, Any]) -> int:
    """Safely calculates completed stands count."""
    if 'stand_status' not in user:
        return 0
    return sum(1 for info in user['stand_status'].values() if info.get('done', False))

def set_stand_status(user: Dict[str, Any], stand_id: str, done: bool = True) -> None:
    """Safely sets stand status for a user."""
    if 'stand_status' not in user:
        user['stand_status'] = {}
    if stand_id not in user['stand_status']:
        user['stand_status'][stand_id] = {}
    user['stand_status'][stand_id]['done'] = done

def get_total_stands_count() -> int:
    """Gets total number of stands from current configuration."""
    stands = config_manager.get('STANDS', []) if config_manager else []
    return len(stands)

def build_main_menu(user: Dict[str, Any]) -> Dict[str, Any]:
    """Создает главное меню."""
    completed = get_completed_count(user)
    progress = create_progress_bar(completed)

    menu_items = []
    # Добавляем кнопки стендов
    stands = config_manager.get('STANDS', []) if config_manager else []
    for stand in stands:
        stand_status = get_stand_status(user, stand['id'])
        if stand_status['done']:
            menu_items.append({'text': f'{stand["emoji"]} {stand["title"]} ✅', 'callback_data': f'STAND_INFO_{stand["id"]}'})
        else:
            menu_items.append({'text': f'{stand["emoji"]} {stand["title"]}', 'callback_data': f'STAND_{stand["id"]}'})
    
    # Добавляем остальные кнопки меню
    menu_items.extend([
        {'text': '📅 Расписание', 'callback_data': 'MAIN_SCHEDULE'},
        {'text': f'🎁 Розыгрыш (⏳ {completed}/{get_total_stands_count()})', 'callback_data': 'MAIN_GIVEAWAY'},
        {'text': '📊 Мой прогресс', 'callback_data': 'MAIN_STATS'},
        {'text': '❓ Помощь', 'callback_data': 'MAIN_HELP'},
    ])
    
    # Разбиваем на строки по 2 кнопки в каждой строке
    keyboard = []
    for i in range(0, len(menu_items), 2):
        keyboard.append(menu_items[i:i+2])
    
    return {'inline_keyboard': keyboard}

def build_giveaway_keyboard(user: Dict[str, Any]) -> Dict[str, Any]:
    """Создает клавиатуру розыгрыша."""
    completed = get_completed_count(user)

    keyboard = []

    # Добавляем кнопки стендов
    stands = config_manager.get('STANDS', []) if config_manager else []
    for stand in stands:
        stand_status = get_stand_status(user, stand['id'])
        if stand_status['done']:
            keyboard.append([{'text': f'{stand["emoji"]} {stand["title"]} ✅', 'callback_data': f'STAND_INFO_{stand["id"]}'},])
        else:
            keyboard.append([{'text': f'{stand["emoji"]} {stand["title"]}', 'callback_data': f'STAND_{stand["id"]}'},])
    
    # VK link button
    if user.get('vk_verified', False):
        keyboard.append([
            {'text': '🔗 VK профиль добавлен', 'callback_data': 'GIVEAWAY_VK_LINK'}
        ])
    else:
        keyboard.append([
            {'text': '🔗 Добавить VK профиль', 'callback_data': 'GIVEAWAY_VK_LINK'}
        ])
    
    # Progress button
    keyboard.append([
        {'text': '📊 Прогресс', 'callback_data': 'GIVEAWAY_PROGRESS'}
    ])
    
    # Back button
    keyboard.append([
        {'text': '⬅️ Назад в меню', 'callback_data': 'GIVEAWAY_BACK'}
    ])
    
    return {'inline_keyboard': keyboard}

def build_main_reply_keyboard(user: Dict[str, Any]) -> Dict[str, Any]:
    """Создает reply клавиатуру для основных команд."""
    completed = get_completed_count(user)
    vk_verified = user.get('vk_verified', False)

    # Проверяем, квалифицирован ли пользователь
    if completed == get_total_stands_count() and vk_verified:
        return {
            'keyboard': [
                ['📅 Расписание', '📊 Мой прогресс'],
                ['🎁 Розыгрыш (✅ {}/{})'.format(completed, get_total_stands_count()), '❓ Помощь'],
                ['🏆 Я УЧАСТВУЮ В РОЗЫГРЫШЕ! 🎉']
            ],
            'resize_keyboard': True
        }
    elif completed < 3:
        return {
            'keyboard': [
                ['📅 Расписание', '📊 Мой прогресс'],
                ['🎁 Розыгрыш (⏳ {}/{})'.format(completed, get_total_stands_count()), '❓ Помощь']
            ],
            'resize_keyboard': True
        }
    else:
        return {
            'keyboard': [
                ['📅 Расписание', '📊 Мой прогресс'],
                ['🎁 Розыгрыш (✅ {}/{})'.format(completed, get_total_stands_count()), '❓ Помощь']
            ],
            'resize_keyboard': True
        }

def format_stand_status(user: Dict[str, Any]) -> str:
    """Форматирует статус прохождения стендов."""
    completed = get_completed_count(user)
    progress = create_progress_bar(completed)

    status_text = f'📊 *Ваш прогресс:*\n\n{progress}\n\n'

    stands = config_manager.get('STANDS', []) if config_manager else []
    for stand in stands:
        status = get_stand_status(user, stand['id'])
        if status['done']:
            status_text += f'✅ {stand["emoji"]} {stand["title"]}\n'
        else:
            status_text += f'⏳ {stand["emoji"]} {stand["title"]}\n'
    
    status_text += f'\n🎯 *Пройдено:* {completed}/{get_total_stands_count()} стенда'
    
    return status_text

def get_motivational_message(user: Dict[str, Any]) -> str:
    """Получает мотивационное сообщение."""
    completed = get_completed_count(user)
    total = get_total_stands_count()

    if completed == 0:
        return '🚀 *Начните с первого стенда!*'
    elif completed == 1:
        return '🔥 *Уже один стенд пройден!*'
    elif completed == total - 1 and total > 1:
        return '🌟 *Почти завершено!*'
    elif completed == total:
        return '🎉 *Поздравляем!* Вы прошли все стенды!'
    else:
        return '💡 *Продолжайте в том же духе!*'

def create_progress_bar(completed: int, total: int = None) -> str:
    """Создает прогресс-бар."""
    if total is None:
        total = get_total_stands_count()
    if completed < 0:
        completed = 0
    if completed > total:
        completed = total
    
    filled = '█' * completed
    empty = '░' * (total - completed)
    
    return f'[{filled}{empty}] {completed}/{total}'

def main_menu_text(user: Dict[str, Any]) -> str:
    """Текст главного меню."""
    completed = get_completed_count(user)
    motivation = get_motivational_message(user)
    
    return (
        f'🎯 *Главное меню*\n\n'
        f'{motivation}\n\n'
        f'📊 *Ваш прогресс:*\n'
        f'{create_progress_bar(completed)}\n\n'
        f'Выберите действие:'
    )
