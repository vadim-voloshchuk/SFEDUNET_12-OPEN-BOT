"""Конфигурационный файл с константами и текстами бота."""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

# Пути и настройки
DATA_PATH = Path(os.getenv('BOT_STATE_PATH', 'data/state.json'))
POLL_TIMEOUT = 30

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Путь к файлу состояния
STATE_FILE_PATH = 'data/state.json'

# Тексты
SCHEDULE_TEXT = (
    '📅 *Расписание фестиваля Sfedunet 12*\n\n'
    '🌅 *09:30* – Регистрация и приветственный кофе ☕\n'
    '🎉 *10:00* – Церемония открытия с шоу-кейсом проектов 🚀\n'
    '🔬 *11:00* – Работа стендов и интерактивных зон 🎯\n'
    '🎤 *13:00* – Питч-сессия финалистов 💡\n'
    '👥 *15:00* – Мастер-классы и комьюнити митапы 🛠️\n'
    '🏆 *17:30* – Подведение итогов и афтепати 🎊\n\n'
    '✨ Не забудьте посетить все стенды для участия в розыгрыше!'
)

# Функция для загрузки стендов из JSON
def load_stands():
    """Загрузить стенды из JSON файла."""
    try:
        stands_file = Path('data/stands.json')
        if stands_file.exists():
            with open(stands_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"[Config] Файл стендов не найден: {stands_file}")
            return []
    except Exception as e:
        print(f"[Config] Ошибка загрузки стендов: {e}")
        return []

def save_stands(stands):
    """Сохранить стенды в JSON файл."""
    try:
        stands_file = Path('data/stands.json')
        stands_file.parent.mkdir(parents=True, exist_ok=True)

        with open(stands_file, 'w', encoding='utf-8') as f:
            json.dump(stands, f, ensure_ascii=False, indent=2)
        print(f"[Config] Стенды сохранены в {stands_file}")
        return True
    except Exception as e:
        print(f"[Config] Ошибка сохранения стендов: {e}")
        return False

# Загружаем стенды из JSON
STANDS = load_stands()

# Регулярные выражения
VK_LINK_PATTERN = re.compile(r'^(https?://)?(www\.)?vk\.com/([A-Za-z0-9_.]+)/?$')

# Сообщения достижений
ACHIEVEMENTS = {
    'first_stand': '🎉 *Поздравляем!* Вы прошли свой первый стенд!',
    'half_complete': '⚡ *Отлично!* Вы на полпути к призу!',
    'all_complete': '🏆 *Невероятно!* Все стенды пройдены! Вы участвуете в розыгрыше!',
    'registration_complete': '✅ *Регистрация завершена!* Добро пожаловать на Sfedunet 12!'
}

# Индикаторы прогресса
PROGRESS_BARS = {
    0: '⬜⬜⬜',
    1: '🟦⬜⬜',
    2: '🟦🟦⬜',
    3: '🟦🟦🟦'
}