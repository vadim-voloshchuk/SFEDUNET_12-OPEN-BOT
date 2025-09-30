"""HTTP сервер для синхронизации между ботом и админ-панелью."""

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
import json

logger = logging.getLogger('bot.sync_server')

class SyncHandler(BaseHTTPRequestHandler):
    """Обработчик HTTP запросов для синхронизации."""

    def do_POST(self):
        """Обработка POST запросов."""
        try:
            # Парсим URL
            parsed_path = urlparse(self.path)
            path = parsed_path.path

            if path == '/reload-config':
                # Уведомление о необходимости перезагрузки конфигурации
                self._handle_reload_config()
            elif path == '/webhook':
                # Общий webhook для уведомлений
                self._handle_webhook()
            else:
                self.send_error(404, 'Not Found')

        except Exception as e:
            logger.error(f'Error handling request: {e}')
            self.send_error(500, 'Internal Server Error')

    def do_GET(self):
        """Обработка GET запросов."""
        if self.path == '/health':
            self._send_json_response({'status': 'ok', 'message': 'Sync server is running'})
        else:
            self.send_error(404, 'Not Found')

    def _handle_reload_config(self):
        """Обрабатывает запрос на перезагрузку конфигурации."""
        try:
            # Импортируем здесь, чтобы избежать циклических импортов
            from config_manager import config_manager

            # Принудительно перезагружаем конфигурацию
            config_manager.reload_config()

            self._send_json_response({
                'status': 'success',
                'message': 'Configuration reloaded'
            })

            logger.info('Configuration reload triggered via API')

        except Exception as e:
            logger.error(f'Failed to reload config via API: {e}')
            self._send_json_response({
                'status': 'error',
                'message': str(e)
            }, status_code=500)

    def _handle_webhook(self):
        """Обрабатывает общие webhook уведомления."""
        try:
            # Читаем данные запроса
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                post_data = self.rfile.read(content_length)
                data = json.loads(post_data.decode('utf-8'))
            else:
                data = {}

            # Обрабатываем разные типы уведомлений
            event_type = data.get('type', 'unknown')

            if event_type == 'config_changed':
                from config_manager import config_manager
                config_manager.reload_config()

            elif event_type == 'stands_updated':
                # Можно добавить специфичную логику для обновления стендов
                from config_manager import config_manager
                config_manager.reload_config()

            self._send_json_response({
                'status': 'success',
                'message': f'Webhook processed: {event_type}'
            })

            logger.info(f'Webhook processed: {event_type}')

        except Exception as e:
            logger.error(f'Failed to process webhook: {e}')
            self._send_json_response({
                'status': 'error',
                'message': str(e)
            }, status_code=500)

    def _send_json_response(self, data: dict, status_code: int = 200):
        """Отправляет JSON ответ."""
        response = json.dumps(data, ensure_ascii=False)

        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response.encode('utf-8'))))
        self.end_headers()

        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        """Переопределяем логирование для интеграции с основным логгером."""
        logger.info(f'{self.address_string()} - {format % args}')

class SyncServer:
    """HTTP сервер для синхронизации."""

    def __init__(self, host: str = 'localhost', port: int = 8765):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None

    def start(self):
        """Запускает сервер."""
        try:
            self.server = HTTPServer((self.host, self.port), SyncHandler)
            self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.server_thread.start()

            logger.info(f'Sync server started on {self.host}:{self.port}')

        except Exception as e:
            logger.error(f'Failed to start sync server: {e}')

    def stop(self):
        """Останавливает сервер."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join()

        logger.info('Sync server stopped')

# Глобальный экземпляр сервера синхронизации
sync_server = SyncServer()