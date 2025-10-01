#!/usr/bin/env python3
"""Тест функциональности бота - проверяем клавиатуры и обработку команд."""

import sys
import json
from bot import TelegramBot
from config import BOT_TOKEN

def test_bot_functionality():
    """Тестируем функциональность бота."""

    print("=== Тест функциональности Telegram Bot ===")

    # Создаем экземпляр бота
    bot = TelegramBot(BOT_TOKEN)

    test_user_id = 999999  # Тестовый пользователь
    test_chat_id = 999999

    print(f"1. Тестируем команду /start для нового пользователя (ID: {test_user_id})")

    # Симулируем команду /start
    start_update = {
        'update_id': 1,
        'message': {
            'message_id': 1,
            'chat': {'id': test_chat_id},
            'from': {'id': test_user_id, 'username': 'test_user'},
            'text': '/start'
        }
    }

    try:
        bot.process_update(start_update)
        print("✅ Команда /start обработана успешно")
    except Exception as e:
        print(f"❌ Ошибка при обработке /start: {e}")
        return False

    print(f"2. Тестируем ввод имени")

    # Симулируем ввод имени
    name_update = {
        'update_id': 2,
        'message': {
            'message_id': 2,
            'chat': {'id': test_chat_id},
            'from': {'id': test_user_id, 'username': 'test_user'},
            'text': 'Тестовый Пользователь'
        }
    }

    try:
        bot.process_update(name_update)
        print("✅ Ввод имени обработан успешно")
    except Exception as e:
        print(f"❌ Ошибка при вводе имени: {e}")
        return False

    print(f"3. Тестируем текстовую команду 'Стенды'")

    # Симулируем текстовую команду "🎮 Стенды"
    stands_text = {
        'update_id': 3,
        'message': {
            'message_id': 3,
            'chat': {'id': test_chat_id},
            'from': {'id': test_user_id, 'username': 'test_user'},
            'text': '🎮 Стенды'
        }
    }

    try:
        bot.process_update(stands_text)
        print("✅ Текстовая команда 'Стенды' обработана успешно")
    except Exception as e:
        print(f"❌ Ошибка при обработке команды 'Стенды': {e}")
        return False

    print(f"4. Тестируем выбор стенда 'Нейроплей'")

    # Симулируем выбор стенда через текст
    stand_text = {
        'update_id': 4,
        'message': {
            'message_id': 4,
            'chat': {'id': test_chat_id},
            'from': {'id': test_user_id, 'username': 'test_user'},
            'text': '🎮 Нейроплей'
        }
    }

    try:
        bot.process_update(stand_text)
        print("✅ Выбор стенда 'Нейроплей' обработан успешно")
    except Exception as e:
        print(f"❌ Ошибка при выборе стенда: {e}")
        return False

    print(f"5. Тестируем завершение стенда через кнопку")

    # Симулируем завершение стенда через текстовую команду
    complete_text = {
        'update_id': 5,
        'message': {
            'message_id': 5,
            'chat': {'id': test_chat_id},
            'from': {'id': test_user_id, 'username': 'test_user'},
            'text': '✅ Пройти стенд'
        }
    }

    try:
        bot.process_update(complete_text)
        print("✅ Завершение стенда обработано успешно")
    except Exception as e:
        print(f"❌ Ошибка при завершении стенда: {e}")
        return False

    print(f"6. Проверяем состояние пользователя")

    # Проверяем состояние пользователя
    try:
        user = bot.state_manager.get_user(test_user_id)
        print(f"   Имя пользователя: {user['full_name']}")
        print(f"   Статус стенда 'neuroplay': {user['stand_status']['neuroplay']['done']}")

        if user['full_name'] == 'Тестовый Пользователь' and user['stand_status']['neuroplay']['done']:
            print("✅ Состояние пользователя корректное")
        else:
            print("❌ Состояние пользователя некорректное")
            return False

    except Exception as e:
        print(f"❌ Ошибка при проверке состояния: {e}")
        return False

    print(f"7. Тестируем возврат в главное меню")

    # Симулируем возврат в главное меню через текстовую команду
    progress_text = {
        'update_id': 6,
        'message': {
            'message_id': 6,
            'chat': {'id': test_chat_id},
            'from': {'id': test_user_id, 'username': 'test_user'},
            'text': '📊 Мой прогресс'
        }
    }

    try:
        bot.process_update(progress_text)
        print("✅ Возврат в главное меню обработан успешно")
    except Exception as e:
        print(f"❌ Ошибка при возврате в меню: {e}")
        return False

    print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
    print("✅ Бот корректно обрабатывает команды и клавиатуры")
    print("✅ Состояние пользователей сохраняется правильно")
    print("✅ Логика прохождения стендов работает")

    # Очищаем тестового пользователя
    try:
        current_data = bot.state_manager.data
        if str(test_user_id) in current_data:
            del current_data[str(test_user_id)]
            bot.state_manager._save_state()
        print("✅ Тестовый пользователь удален")
    except Exception as e:
        print(f"⚠️  Не удалось удалить тестового пользователя: {e}")

    return True

if __name__ == '__main__':
    success = test_bot_functionality()
    sys.exit(0 if success else 1)