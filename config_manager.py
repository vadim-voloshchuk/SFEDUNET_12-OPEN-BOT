"""Менеджер конфигурации с горячей перезагрузкой."""

import importlib
import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List

# Загружаем переменные окружения из .env файла
def load_env_file(env_path: str = '.env'):
    """Загружает переменные окружения из .env файла."""
    env_file = Path(env_path)
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Загружаем .env при импорте модуля
load_env_file()

logger = logging.getLogger('bot.config_manager')

class ConfigManager:
    """Менеджер конфигурации с автоматической перезагрузкой."""

    def __init__(self, config_file: str = 'config.py'):
        self.config_file = config_file
        self.config_path = Path(config_file)
        self.last_modified = 0
        self.config_data = {}
        self._lock = threading.Lock()
        self.reload_callbacks = []

        # Загружаем конфигурацию первый раз
        self.reload_config()

        # Запускаем мониторинг изменений
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_config, daemon=True)
        self.monitor_thread.start()

        logger.info('ConfigManager initialized with hot reload')

    def add_reload_callback(self, callback):
        """Добавляет callback, который вызывается при перезагрузке конфигурации."""
        self.reload_callbacks.append(callback)

    def reload_config(self):
        """Перезагружает конфигурацию из файла."""
        try:
            with self._lock:
                # Перезагружаем модуль config
                import config
                if 'config' in sys.modules:
                    config = importlib.reload(sys.modules['config'])

                # Копируем все атрибуты из модуля
                for attr_name in dir(config):
                    if not attr_name.startswith('_'):
                        self.config_data[attr_name] = getattr(config, attr_name)

                # Обновляем время модификации
                self.last_modified = self.config_path.stat().st_mtime

                logger.info('Configuration reloaded successfully')

                # Вызываем callbacks
                for callback in self.reload_callbacks:
                    try:
                        callback()
                    except Exception as e:
                        logger.error(f'Error in reload callback: {e}')

        except Exception as e:
            logger.error(f'Failed to reload config: {e}')

    def _monitor_config(self):
        """Мониторит изменения в файле конфигурации."""
        while self.monitoring:
            try:
                if self.config_path.exists():
                    current_modified = self.config_path.stat().st_mtime
                    if current_modified > self.last_modified:
                        logger.info('Config file changed, reloading...')
                        self.reload_config()

                time.sleep(1)  # Проверяем каждую секунду
            except Exception as e:
                logger.error(f'Error monitoring config: {e}')
                time.sleep(5)

    def get(self, key: str, default=None):
        """Получает значение из конфигурации."""
        with self._lock:
            return self.config_data.get(key, default)

    def __getattr__(self, name: str):
        """Позволяет обращаться к конфигурации как к атрибутам."""
        with self._lock:
            if name in self.config_data:
                return self.config_data[name]
            raise AttributeError(f"'{self.__class__.__name__}' has no attribute '{name}'")

    def stop_monitoring(self):
        """Останавливает мониторинг файла конфигурации."""
        self.monitoring = False
        if self.monitor_thread.is_alive():
            self.monitor_thread.join()

# Глобальный экземпляр менеджера конфигурации
config_manager = ConfigManager()