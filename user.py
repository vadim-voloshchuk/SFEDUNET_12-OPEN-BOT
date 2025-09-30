"""Логика работы с пользователем."""

from typing import Any, Dict

from config import ACHIEVEMENTS, STANDS
from menu import (
    build_main_menu,
    build_giveaway_keyboard,
    build_main_reply_keyboard,
    format_stand_status,
    main_menu_text,
    get_completed_count,
    get_total_stands_count
)

def ensure_main_menu(chat_id: int, user: Dict[str, Any], edit_message_func, send_message_func) -> None:
    """Обновляет главное меню пользователя."""
    # Если у пользователя уже есть menu_message_id, обновляем его
    if user.get('menu_message_id'):
        try:
            edit_message_func(
                chat_id,
                user['menu_message_id'],
                main_menu_text(user),
                reply_markup=build_main_menu(user),
                parse_mode='Markdown'
            )
        except Exception:
            # Если не удалось обновить, отправляем новое сообщение
            user['menu_message_id'] = None
            message = send_message_func(
                chat_id,
                main_menu_text(user),
                reply_markup=build_main_menu(user),
                parse_mode='Markdown'
            )
            user['menu_message_id'] = message['message_id']
    else:
        # Отправляем новое сообщение
        message = send_message_func(
            chat_id,
            main_menu_text(user),
            reply_markup=build_main_menu(user),
            parse_mode='Markdown'
        )
        user['menu_message_id'] = message['message_id']

def ensure_giveaway_menu(chat_id: int, user: Dict[str, Any], edit_message_func, send_message_func) -> None:
    """Обновляет меню розыгрыша пользователя."""
    completed = get_completed_count(user)
    vk_verified = user.get('vk_verified', False)

    # Создаем текст с прогрессом
    giveaway_text = f'🎁 *Розыгрыш призов*\n\n'

    if completed == 3 and vk_verified:
        giveaway_text += '🎉 *Поздравляем!* Вы квалифицированы для участия в розыгрыше!\n\n'
        giveaway_text += '✅ Все стенды пройдены\n'
        giveaway_text += '✅ VK профиль добавлен\n\n'
        giveaway_text += '🏆 Ожидайте результатов розыгрыша!'
    else:
        giveaway_text += '📋 *Условия участия:*\n\n'
        total_stands = get_total_stands_count()
        giveaway_text += f'{"✅" if completed == total_stands else "❌"} Пройти все стенды ({completed}/{total_stands})\n'
        giveaway_text += f'{"✅" if vk_verified else "❌"} Добавить VK профиль\n\n'

        if completed < get_total_stands_count():
            giveaway_text += '👇 *Выберите стенд для прохождения:*'
        elif not vk_verified:
            giveaway_text += '👇 *Добавьте VK профиль:*'

    # Если у пользователя уже есть giveaway_message_id, обновляем его
    if user.get('giveaway_message_id'):
        try:
            edit_message_func(
                chat_id,
                user['giveaway_message_id'],
                giveaway_text,
                reply_markup=build_giveaway_keyboard(user),
                parse_mode='Markdown'
            )
        except Exception:
            # Если не удалось обновить, отправляем новое сообщение
            user['giveaway_message_id'] = None
            message = send_message_func(
                chat_id,
                giveaway_text,
                reply_markup=build_giveaway_keyboard(user),
                parse_mode='Markdown'
            )
            user['giveaway_message_id'] = message['message_id']
    else:
        # Отправляем новое сообщение
        message = send_message_func(
            chat_id,
            giveaway_text,
            reply_markup=build_giveaway_keyboard(user),
            parse_mode='Markdown'
        )
        user['giveaway_message_id'] = message['message_id']
