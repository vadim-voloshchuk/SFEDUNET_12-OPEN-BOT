"""Основной файл бота."""

import logging
import logging.handlers
import os
import sys
import time
from pathlib import Path

# Добавляем текущую директорию в путь поиска модулей
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import TelegramAPI
from config_manager import config_manager
from handlers import (
    set_api_client,
    set_state_store,
    event_loop
)
from state import StateStore
from sync_server import sync_server

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(
            'logs/bot.log',
            maxBytes=1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
    ]
)

logger = logging.getLogger('bot.main')

def main() -> None:
    """Главная функция бота."""
    logger.info('Starting bot with hot reload support...')

    # Инициализация компонентов
    bot_token = config_manager.get('BOT_TOKEN')
    state_file_path = config_manager.get('STATE_FILE_PATH', 'data/state.json')

    api_client = TelegramAPI(bot_token)
    state_store = StateStore(Path(state_file_path))

    # Установка глобальных переменных
    set_api_client(api_client)
    set_state_store(state_store)

    # Запуск сервера синхронизации
    sync_server.start()

    logger.info('Bot initialized successfully with hot reload.')

    # Запуск основного цикла
    try:
        event_loop()
    except KeyboardInterrupt:
        logger.info('Bot interrupted by user.')
    except Exception as exc:
        logger.error('Bot error: %s', str(exc), exc_info=True)
        raise
    finally:
        # Останавливаем сервисы
        sync_server.stop()
        config_manager.stop_monitoring()

if __name__ == '__main__':
    main()
