#!/usr/bin/env python3
"""Тест работы в реальном времени - демонстрация единого источника данных."""

import time
import random
from realtime_state import get_state_manager

def test_realtime_sync():
    """Тестирует синхронизацию в реальном времени."""

    print("🚀 Тест синхронизации в реальном времени")
    print("=" * 50)

    # Получаем менеджер состояния
    state_manager = get_state_manager()

    print(f"📊 Исходное состояние:")
    stats = state_manager.get_stats()
    print(f"   Пользователей: {stats['total_users']}")
    print(f"   Средний прогресс: {stats['average_progress']}%")

    # Создаем тестового пользователя
    test_user_id = random.randint(1000000, 9999999)
    print(f"\n👤 Создаем тестового пользователя: {test_user_id}")

    user = state_manager.get_user(test_user_id)
    print(f"   ✅ Пользователь создан с {len(user['stand_status'])} стендами")

    # Обновляем имя пользователя
    print(f"\n📝 Обновляем имя пользователя...")
    state_manager.update_user(test_user_id, {
        'full_name': f'Test User {test_user_id % 1000}',
        'awaiting_name': False
    })

    # Симулируем прохождение стендов
    stands = list(user['stand_status'].keys())
    for i, stand_id in enumerate(stands[:3]):  # Проходим первые 3 стенда
        print(f"\n🎯 Проходим стенд {i+1}: {stand_id}")

        # Обновляем статус стенда
        user_data = state_manager.get_user(test_user_id)
        user_data['stand_status'][stand_id]['done'] = True

        state_manager.update_user(test_user_id, {
            'stand_status': user_data['stand_status']
        })

        # Показываем новую статистику
        stats = state_manager.get_stats()
        print(f"   📈 Новая статистика: средний прогресс {stats['average_progress']}%")

        time.sleep(1)  # Пауза для демонстрации

    # Добавляем VK верификацию
    print(f"\n✅ Добавляем VK верификацию...")
    state_manager.update_user(test_user_id, {
        'vk_verified': True,
        'vk_profile': 'https://vk.com/test_user'
    })

    # Проходим оставшиеся стенды
    for i, stand_id in enumerate(stands[3:], 4):
        print(f"\n🎯 Проходим стенд {i}: {stand_id}")

        user_data = state_manager.get_user(test_user_id)
        user_data['stand_status'][stand_id]['done'] = True

        state_manager.update_user(test_user_id, {
            'stand_status': user_data['stand_status']
        })

        time.sleep(1)

    # Финальная статистика
    print(f"\n🏆 ФИНАЛЬНАЯ СТАТИСТИКА:")
    stats = state_manager.get_stats()
    print(f"   Всего пользователей: {stats['total_users']}")
    print(f"   Завершивших все стенды: {stats['completed_users']}")
    print(f"   Квалифицированных: {stats['qualified_users']}")
    print(f"   VK верифицированных: {stats['vk_verified_users']}")
    print(f"   Средний прогресс: {stats['average_progress']}%")

    print(f"\n🎉 Тест завершен! Пользователь {test_user_id} прошел все стенды.")
    print(f"💡 Проверьте админ-панель на http://localhost:5000 - данные обновились автоматически!")

    return test_user_id

if __name__ == '__main__':
    test_realtime_sync()