#!/usr/bin/env python3
"""Telegram бот для регистрации на розыгрыш через прохождение стендов."""

import logging
import os
import sys
import json
import requests
import time
import random
import re
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Импортируем единый менеджер состояния
from realtime_state import get_state_manager
from config import BOT_TOKEN, VK_LINK_PATTERN, load_stands

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger('telegram_bot')

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.state_manager = get_state_manager()
        self.offset = 0

    def create_keyboard(self, user_id):
        """Создать клавиатуру в зависимости от состояния пользователя."""
        user = self.state_manager.get_user(user_id)

        # Если ожидаем ввод - убираем клавиатуру
        if user['awaiting_name'] or user['awaiting_vk_link'] or user.get('pending_question'):
            return {'remove_keyboard': True}

        # Основная клавиатура
        keyboard = []

        # Проверяем прогресс пользователя
        completed_stands = sum(1 for s in user['stand_status'].values() if s['done'])
        total_stands = len(user['stand_status'])
        has_vk = user.get('vk_verified', False)

        # Если пользователь завершил все стенды и добавил ВК - показываем кнопку розыгрыша
        if completed_stands == total_stands and has_vk:
            keyboard.append(['🎁 Розыгрыш'])
            keyboard.append(['📊 Мой прогресс'])
            return {
                'keyboard': keyboard,
                'resize_keyboard': True,
                'one_time_keyboard': False
            }

        # Если завершил все стенды но нет ВК
        if completed_stands == total_stands and not has_vk:
            keyboard.append(['🔗 Добавить ВК'])
            keyboard.append(['📊 Мой прогресс'])
            return {
                'keyboard': keyboard,
                'resize_keyboard': True,
                'one_time_keyboard': False
            }

        # Первый ряд - основные действия
        row1 = ['📊 Мой прогресс', '🎮 Стенды']
        keyboard.append(row1)

        # Второй ряд - стенды для прохождения
        incomplete_stands = [
            stand_id for stand_id, status in user['stand_status'].items()
            if not status['done']
        ]

        if incomplete_stands:
            stands = load_stands()
            stands_dict = {stand['id']: stand for stand in stands}
            # Показываем первый доступный стенд
            first_incomplete = incomplete_stands[0]
            if first_incomplete in stands_dict:
                stand_info = stands_dict[first_incomplete]
                keyboard.append([f"🎯 Пройти {stand_info['description']}"])

        return {
            'keyboard': keyboard,
            'resize_keyboard': True,
            'one_time_keyboard': False
        }

    def send_message(self, chat_id, text, user_id=None, use_keyboard=True):
        """Отправить сообщение в Telegram."""
        url = f"{self.api_url}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }

        # Добавляем клавиатуру если нужно
        if use_keyboard and user_id:
            keyboard = self.create_keyboard(user_id)
            data['reply_markup'] = json.dumps(keyboard)

        try:
            response = requests.post(url, data=data, timeout=10)
            result = response.json()
            if result.get('ok'):
                logger.info(f"Message sent to {chat_id}: {text[:50]}...")
            else:
                logger.error(f"Failed to send message: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return None

    def get_updates(self):
        """Получить обновления из Telegram."""
        url = f"{self.api_url}/getUpdates"
        params = {
            'offset': self.offset,
            'timeout': 10
        }

        try:
            response = requests.get(url, params=params, timeout=15)
            return response.json()
        except Exception as e:
            logger.error(f"Failed to get updates: {e}")
            return None

    def handle_start(self, chat_id, user_id, username):
        """Обработать команду /start."""
        logger.info(f"User {user_id} started bot")

        # Создаем или получаем пользователя
        user = self.state_manager.get_user(user_id)

        # Если пользователь новый, инициализируем
        if user['full_name'] is None:
            self.state_manager.update_user(user_id, {
                'awaiting_name': True
            })

            self.send_message(
                chat_id,
                "🎉 <b>Добро пожаловать на Sfedunet 12!</b>\n\n"
                "Для участия в розыгрыше вам нужно:\n"
                "1️⃣ Пройти все стенды и ответить на вопросы\n"
                "2️⃣ Добавить ссылку на ваш профиль ВКонтакте\n\n"
                "Для начала введите ваше полное имя:",
                user_id=user_id
            )
        else:
            self.show_main_menu(chat_id, user_id)

    def handle_name_input(self, chat_id, user_id, text):
        """Обработать ввод имени."""
        # Обновляем имя пользователя
        self.state_manager.update_user(user_id, {
            'full_name': text.strip(),
            'awaiting_name': False
        })

        logger.info(f"User {user_id} set name: {text}")

        self.send_message(
            chat_id,
            f"✅ <b>Отлично, {text}!</b>\n\n"
            "Теперь вы можете приступать к прохождению стендов.",
            user_id=user_id
        )

        self.show_main_menu(chat_id, user_id)

    def handle_vk_input(self, chat_id, user_id, text):
        """Обработать ввод ВК ссылки."""
        # Проверяем формат ссылки
        if not VK_LINK_PATTERN.match(text.strip()):
            self.send_message(
                chat_id,
                "❌ <b>Неверный формат ссылки!</b>\n\n"
                "Пожалуйста, введите ссылку в формате:\n"
                "• vk.com/username\n"
                "• https://vk.com/username\n"
                "• www.vk.com/username",
                user_id=user_id
            )
            return

        # Сохраняем ВК профиль
        self.state_manager.update_user(user_id, {
            'vk_profile': text.strip(),
            'vk_verified': True,
            'awaiting_vk_link': False
        })

        logger.info(f"User {user_id} added VK profile: {text}")

        self.send_message(
            chat_id,
            "✅ <b>ВКонтакте профиль добавлен!</b>\n\n"
            "🎉 Поздравляем! Теперь вы участвуете в розыгрыше!",
            user_id=user_id
        )

        self.show_main_menu(chat_id, user_id)

    def start_stand_questions(self, chat_id, user_id, stand_description):
        """Начать прохождение стенда с вопросами."""
        # Находим стенд по описанию
        stands = load_stands()
        stands_dict = {stand['id']: stand for stand in stands}
        found_stand = None

        for stand_id, stand_info in stands_dict.items():
            if stand_info['description'] == stand_description:
                found_stand = (stand_id, stand_info)
                break

        if not found_stand:
            self.send_message(chat_id, "❌ Стенд не найден!", user_id=user_id)
            return

        stand_id, stand_info = found_stand
        user = self.state_manager.get_user(user_id)

        # Проверяем, не пройден ли уже стенд
        if user['stand_status'][stand_id]['done']:
            self.send_message(chat_id, f"✅ Стенд уже пройден!", user_id=user_id)
            return

        # Выбираем случайный вопрос из стенда
        if 'questions' not in stand_info or not stand_info['questions']:
            # Если нет вопросов, просто засчитываем стенд
            self.complete_stand(chat_id, user_id, stand_id, stand_info)
            return

        random_question = random.choice(stand_info['questions'])

        # Сохраняем текущий вопрос в состоянии пользователя
        self.state_manager.update_user(user_id, {
            'pending_question': {
                'stand_id': stand_id,
                'question': random_question['question'],
                'answers': random_question['answers'],
                'hint': random_question.get('hint', 'Нет подсказки')
            }
        })

        text = f"🎯 <b>{stand_info['emoji']} {stand_info['description']}</b>\n\n"
        text += f"❓ <b>Вопрос:</b>\n{random_question['question']}\n\n"
        text += "✍️ Введите ваш ответ:"

        self.send_message(chat_id, text, user_id=user_id)

    def handle_question_answer(self, chat_id, user_id, text):
        """Обработать ответ на вопрос."""
        user = self.state_manager.get_user(user_id)
        pending_question = user.get('pending_question')

        if not pending_question:
            self.send_message(chat_id, "❌ Нет активного вопроса!", user_id=user_id)
            return

        # Проверяем ответ
        user_answer = text.strip().lower()
        correct_answers = [answer.lower() for answer in pending_question['answers']]

        if user_answer in correct_answers:
            # Правильный ответ
            stand_id = pending_question['stand_id']
            stands = load_stands()
            stands_dict = {stand['id']: stand for stand in stands}
            stand_info = stands_dict[stand_id]

            # Завершаем стенд
            self.complete_stand(chat_id, user_id, stand_id, stand_info)
        else:
            # Неправильный ответ - показываем подсказку
            self.send_message(
                chat_id,
                f"❌ <b>Неверный ответ!</b>\n\n"
                f"{pending_question['hint']}\n\n"
                "Попробуйте еще раз:",
                user_id=user_id
            )

    def complete_stand(self, chat_id, user_id, stand_id, stand_info):
        """Завершить стенд."""
        # Обновляем статус стенда и убираем активный вопрос
        user = self.state_manager.get_user(user_id)
        updates = {
            'stand_status': {
                **user['stand_status'],
                stand_id: {'done': True}
            },
            'pending_question': None
        }
        self.state_manager.update_user(user_id, updates)

        logger.info(f"User {user_id} completed stand: {stand_id}")

        text = f"🎉 <b>Поздравляем!</b>\n\n"
        text += f"Вы успешно прошли стенд:\n{stand_info['emoji']} <b>{stand_info['description']}</b>\n\n"

        # Проверяем общий прогресс
        user = self.state_manager.get_user(user_id)  # Перезагружаем данные
        completed_stands = sum(1 for s in user['stand_status'].values() if s['done'])
        total_stands = len(user['stand_status'])

        if completed_stands == total_stands:
            text += f"🏆 <b>Отлично! Вы прошли все стенды!</b>\n"
            text += f"Теперь добавьте ссылку на ваш ВК профиль для участия в розыгрыше!"
        else:
            text += f"📊 Прогресс: {completed_stands}/{total_stands} стендов пройдено"

        self.send_message(chat_id, text, user_id=user_id)

    def show_main_menu(self, chat_id, user_id):
        """Показать главное меню."""
        user = self.state_manager.get_user(user_id)

        text = f"🏆 <b>Привет, {user['full_name']}!</b>\n\n"
        text += "📊 <b>Ваш прогресс по стендам:</b>\n\n"

        # Загружаем актуальные стенды
        stands = load_stands()
        stands_dict = {stand['id']: stand for stand in stands}

        for stand_id, stand_info in stands_dict.items():
            status = "✅" if user['stand_status'][stand_id]['done'] else "❌"
            title = f"{stand_info['emoji']} {stand_info['description']}"
            text += f"{status} {title}\n"

        # Проверяем прогресс
        completed_stands = sum(1 for s in user['stand_status'].values() if s['done'])
        total_stands = len(user['stand_status'])

        text += f"\n📈 <b>Прогресс:</b> {completed_stands}/{total_stands} стендов"

        if completed_stands == total_stands:
            text += "\n\n🎉 <b>Поздравляем! Все стенды пройдены!</b>"
            text += "\n🎁 Вы можете участвовать в розыгрыше призов!"

        self.send_message(chat_id, text, user_id=user_id)

    def request_vk_link(self, chat_id, user_id):
        """Запросить ВК ссылку у пользователя."""
        self.state_manager.update_user(user_id, {
            'awaiting_vk_link': True
        })

        self.send_message(
            chat_id,
            "🔗 <b>Добавление ВКонтакте профиля</b>\n\n"
            "Введите ссылку на ваш профиль ВКонтакте:\n\n"
            "Примеры:\n"
            "• vk.com/ivan_petrov\n"
            "• https://vk.com/ivan_petrov\n"
            "• www.vk.com/ivan_petrov",
            user_id=user_id
        )

    def show_giveaway_info(self, chat_id, user_id):
        """Показать информацию о розыгрыше."""
        self.send_message(
            chat_id,
            "🎁 <b>Розыгрыш призов Sfedunet 12</b>\n\n"
            "🏆 Поздравляем! Вы квалифицированы для участия в розыгрыше!\n\n"
            "📋 <b>Условия участия:</b>\n"
            "✅ Пройти все стенды ✓\n"
            "✅ Добавить ВК профиль ✓\n\n"
            "🎯 Розыгрыш состоится в конце мероприятия.\n"
            "Следите за объявлениями!",
            user_id=user_id
        )

    def show_stands_menu(self, chat_id, user_id):
        """Показать меню стендов."""
        user = self.state_manager.get_user(user_id)

        text = f"🎮 <b>Выберите стенд для прохождения:</b>\n\n"

        # Загружаем актуальные стенды
        stands = load_stands()
        stands_dict = {stand['id']: stand for stand in stands}

        # Показываем все стенды с их статусом
        available_stands = []
        for stand_id, stand_info in stands_dict.items():
            status = "✅" if user['stand_status'][stand_id]['done'] else "🔘"
            title = f"{status} {stand_info['emoji']} {stand_info['description']}"
            text += f"{title}\n"

            if not user['stand_status'][stand_id]['done']:
                available_stands.append(stand_info['description'])

        if available_stands:
            text += f"\n💡 <b>Доступные стенды:</b>\n"
            text += "Нажмите на кнопку стенда снизу для прохождения."
        else:
            text += f"\n🎉 <b>Все стенды пройдены!</b>"

        self.send_message(chat_id, text, user_id=user_id)

    def process_update(self, update):
        """Обработать обновление от Telegram."""
        logger.info(f"Processing update: {update.get('update_id', 'unknown')}")

        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            user_id = message['from']['id']
            username = message['from'].get('username', '')
            logger.info(f"Received message from user {user_id}: {message.get('text', 'no text')}")

            if 'text' in message:
                text = message['text']

                if text == '/start':
                    self.handle_start(chat_id, user_id, username)
                else:
                    # Проверяем состояние пользователя
                    user = self.state_manager.get_user(user_id)

                    if user['awaiting_name']:
                        self.handle_name_input(chat_id, user_id, text)
                    elif user['awaiting_vk_link']:
                        self.handle_vk_input(chat_id, user_id, text)
                    elif user.get('pending_question'):
                        self.handle_question_answer(chat_id, user_id, text)
                    else:
                        # Обрабатываем команды с кнопок
                        if text == '📊 Мой прогресс':
                            logger.info(f"User {user_id} clicked: 'Мой прогресс'")
                            self.show_main_menu(chat_id, user_id)
                        elif text == '🎮 Стенды':
                            logger.info(f"User {user_id} clicked: 'Стенды'")
                            self.show_stands_menu(chat_id, user_id)
                        elif text == '🔗 Добавить ВК':
                            logger.info(f"User {user_id} clicked: 'Добавить ВК'")
                            self.request_vk_link(chat_id, user_id)
                        elif text == '🎁 Розыгрыш':
                            logger.info(f"User {user_id} clicked: 'Розыгрыш'")
                            self.show_giveaway_info(chat_id, user_id)
                        elif text.startswith('🎯 Пройти '):
                            # Извлекаем название стенда из кнопки
                            stand_description = text.replace('🎯 Пройти ', '')
                            logger.info(f"User {user_id} starting stand: '{stand_description}'")
                            self.start_stand_questions(chat_id, user_id, stand_description)
                        else:
                            logger.info(f"User {user_id} sent unknown text: '{text}' - showing main menu")
                            self.show_main_menu(chat_id, user_id)

        else:
            logger.warning(f"Unknown update type: {list(update.keys())}")

    def run(self):
        """Запустить бота."""
        logger.info('Starting Telegram Bot with realtime state...')

        # Подписываемся на изменения состояния
        def on_state_change(data):
            logger.info(f'State changed! Total users: {len(data)}')

        self.state_manager.subscribe(on_state_change)
        logger.info('Bot initialized successfully with realtime state.')

        try:
            logger.info('Starting bot polling loop...')

            while True:
                updates_response = self.get_updates()

                if updates_response and updates_response.get('ok'):
                    updates = updates_response.get('result', [])

                    for update in updates:
                        try:
                            self.process_update(update)
                            self.offset = update['update_id'] + 1
                        except Exception as e:
                            logger.error(f"Error processing update: {e}")
                            continue

                time.sleep(1)

        except KeyboardInterrupt:
            logger.info('Bot interrupted by user.')
        except Exception as exc:
            logger.error('Bot error: %s', str(exc), exc_info=True)
            raise
        finally:
            self.state_manager.stop()
            logger.info('Bot stopped.')

def main():
    """Главная функция."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_TOKEN not found in environment variables")
        return

    bot = TelegramBot(BOT_TOKEN)
    bot.run()

if __name__ == '__main__':
    main()