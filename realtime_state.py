#!/usr/bin/env python3
"""Единый источник данных с автоматической синхронизацией в реальном времени."""

import json
import threading
import time
import os
from pathlib import Path
from typing import Any, Dict, Optional, Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class StateChangeHandler(FileSystemEventHandler):
    """Обработчик изменений файла состояния."""

    def __init__(self, callback: Callable):
        self.callback = callback
        self.last_modified = 0

    def on_modified(self, event):
        if event.is_directory:
            return

        if event.src_path.endswith('state.json') or event.src_path.endswith('stands.json'):
            current_time = time.time()
            # Защита от множественных событий
            if current_time - self.last_modified > 0.5:
                self.last_modified = current_time
                self.callback()

class RealtimeStateManager:
    """Менеджер состояния с автоматической синхронизацией в реальном времени."""

    def __init__(self, state_file_path: str = 'data/state.json'):
        self.state_file_path = Path(state_file_path)
        self.data: Dict[str, Any] = {}
        self.subscribers: list[Callable] = []
        self.lock = threading.RLock()
        self._observer = None

        # Создаем директорию если не существует
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Загружаем данные
        self._load()

        # Запускаем мониторинг файла
        self._start_file_monitoring()

    def _load(self):
        """Загружает данные из файла."""
        with self.lock:
            if self.state_file_path.exists():
                try:
                    with open(self.state_file_path, 'r', encoding='utf-8') as f:
                        self.data = json.load(f)
                    print(f"[RealtimeState] Loaded state from {self.state_file_path}")
                except (json.JSONDecodeError, OSError) as e:
                    print(f"[RealtimeState] Error loading state: {e}")
                    self.data = {}
            else:
                print(f"[RealtimeState] Creating new state file at {self.state_file_path}")
                self.data = {}
                self._save()

    def _save(self):
        """Сохраняет данные в файл."""
        try:
            # Создаем временный файл для атомарной записи
            temp_path = self.state_file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)

            # Атомарно заменяем файл
            temp_path.replace(self.state_file_path)

            # Добавляем небольшую задержку чтобы файловая система успела обработать событие
            import time
            time.sleep(0.1)

            print(f"[RealtimeState] Saved state to {self.state_file_path} (users: {len([k for k in self.data.keys() if k != 'meta'])})")

        except Exception as e:
            print(f"[RealtimeState] Error saving state: {e}")
            # Если не можем сохранить в основной файл, попробуем в temp
            try:
                backup_path = Path(f'/tmp/state_backup_{int(time.time())}.json')
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, ensure_ascii=False, indent=2)
                print(f"[RealtimeState] Saved backup to {backup_path}")
            except:
                print("[RealtimeState] Failed to save backup!")

    def _start_file_monitoring(self):
        """Запускает мониторинг изменений файла."""
        try:
            self._observer = Observer()
            handler = StateChangeHandler(self._on_file_changed)
            self._observer.schedule(handler, str(self.state_file_path.parent), recursive=False)
            self._observer.start()
            print(f"[RealtimeState] Started file monitoring for {self.state_file_path.parent}")
        except Exception as e:
            print(f"[RealtimeState] Failed to start file monitoring: {e}")

    def _on_file_changed(self):
        """Обрабатывает изменение файла."""
        print("[RealtimeState] File changed, reloading...")
        old_data = self.data.copy()
        self._load()

        # Если изменились стенды, синхронизируем всех пользователей
        self._sync_all_users_stands()

        # Уведомляем подписчиков об изменениях
        if old_data != self.data:
            self._notify_subscribers()

    def _sync_all_users_stands(self):
        """Синхронизирует стенды для всех пользователей."""
        with self.lock:
            try:
                from config import load_stands
                stands = load_stands()
                current_stand_ids = {stand['id'] for stand in stands}
                updated_users = 0

                for user_id, user_data in self.data.items():
                    if user_id == 'meta' or 'stand_status' not in user_data:
                        continue

                    user_stand_ids = set(user_data['stand_status'].keys())
                    needs_update = False

                    # Добавляем новые стенды
                    for stand in stands:
                        if stand['id'] not in user_data['stand_status']:
                            user_data['stand_status'][stand['id']] = {'done': False}
                            needs_update = True
                            print(f"[RealtimeState] Added stand {stand['id']} to user {user_id}")

                    # Удаляем устаревшие стенды
                    for stand_id in list(user_data['stand_status'].keys()):
                        if stand_id not in current_stand_ids:
                            del user_data['stand_status'][stand_id]
                            needs_update = True
                            print(f"[RealtimeState] Removed obsolete stand {stand_id} from user {user_id}")

                    if needs_update:
                        user_data['updated_at'] = datetime.now().isoformat()
                        updated_users += 1

                if updated_users > 0:
                    print(f"[RealtimeState] Synced stands for {updated_users} users")
                    self._save()

            except Exception as e:
                print(f"[RealtimeState] Error syncing stands: {e}")

    def _notify_subscribers(self):
        """Уведомляет всех подписчиков об изменениях."""
        for callback in self.subscribers:
            try:
                callback(self.data)
            except Exception as e:
                print(f"[RealtimeState] Error notifying subscriber: {e}")

    def subscribe(self, callback: Callable):
        """Подписывается на изменения состояния."""
        self.subscribers.append(callback)
        print(f"[RealtimeState] Added subscriber: {callback.__name__}")

    def unsubscribe(self, callback: Callable):
        """Отписывается от изменений состояния."""
        if callback in self.subscribers:
            self.subscribers.remove(callback)
            print(f"[RealtimeState] Removed subscriber: {callback.__name__}")

    def get_user(self, user_id: int) -> Dict[str, Any]:
        """Получает данные пользователя."""
        with self.lock:
            key = str(user_id)

            # Импортируем актуальную конфигурацию
            try:
                from config import load_stands
                stands = load_stands()
            except:
                stands = []

            if key not in self.data:
                print(f"[RealtimeState] Creating new user: {user_id}")
                self.data[key] = {
                    'full_name': None,
                    'awaiting_name': True,
                    'awaiting_vk_link': False,
                    'vk_profile': None,
                    'vk_verified': False,
                    'stand_status': {stand['id']: {'done': False} for stand in stands},
                    'pending_question': None,
                    'menu_message_id': None,
                    'giveaway_message_id': None,
                    'last_keyboard_state': '',
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                self._save()
                self._notify_subscribers()
            else:
                # Синхронизируем стенды пользователя с актуальной конфигурацией
                user_data = self.data[key]
                if 'stand_status' not in user_data:
                    user_data['stand_status'] = {}

                current_stand_ids = {stand['id'] for stand in stands}
                user_stand_ids = set(user_data['stand_status'].keys())

                # Добавляем новые стенды
                for stand in stands:
                    if stand['id'] not in user_data['stand_status']:
                        user_data['stand_status'][stand['id']] = {'done': False}
                        print(f"[RealtimeState] Added stand {stand['id']} to user {user_id}")

                # Удаляем устаревшие стенды
                for stand_id in list(user_data['stand_status'].keys()):
                    if stand_id not in current_stand_ids:
                        del user_data['stand_status'][stand_id]
                        print(f"[RealtimeState] Removed obsolete stand {stand_id} from user {user_id}")

                # Обновляем timestamp
                user_data['updated_at'] = datetime.now().isoformat()

                if user_stand_ids != current_stand_ids:
                    self._save()
                    self._notify_subscribers()

            return self.data[key]

    def update_user(self, user_id: int, updates: Dict[str, Any]):
        """Обновляет данные пользователя."""
        with self.lock:
            key = str(user_id)
            if key in self.data:
                self.data[key].update(updates)
                self.data[key]['updated_at'] = datetime.now().isoformat()
                self._save()
                self._notify_subscribers()
                print(f"[RealtimeState] Updated user {user_id}: {list(updates.keys())}")
            else:
                print(f"[RealtimeState] Warning: Tried to update non-existent user {user_id}")

    def get_all_users(self) -> Dict[str, Any]:
        """Получает всех пользователей."""
        with self.lock:
            return {k: v for k, v in self.data.items() if k != 'meta'}

    def get_stats(self) -> Dict[str, Any]:
        """Получает актуальную статистику."""
        with self.lock:
            users = self.get_all_users()

            # Импортируем актуальную конфигурацию
            try:
                from config import load_stands
                stands = load_stands()
                total_stands = len(stands)
            except:
                total_stands = 5

            stats = {
                'timestamp': datetime.now().isoformat(),
                'total_users': len(users),
                'total_stands': total_stands,
                'completed_users': 0,
                'qualified_users': 0,
                'vk_verified_users': 0,
                'users_with_pending_questions': 0,
                'average_progress': 0.0
            }

            if users:
                progress_sum = 0
                for user_data in users.values():
                    completed = sum(1 for status in user_data.get('stand_status', {}).values() if status.get('done', False))
                    user_total = len(user_data.get('stand_status', {}))
                    progress = (completed / user_total * 100) if user_total > 0 else 0
                    progress_sum += progress

                    if completed >= total_stands:
                        stats['completed_users'] += 1

                    if user_data.get('vk_verified', False):
                        stats['vk_verified_users'] += 1
                        if completed >= total_stands:
                            stats['qualified_users'] += 1

                    if user_data.get('pending_question'):
                        stats['users_with_pending_questions'] += 1

                stats['average_progress'] = round(progress_sum / len(users), 1)

            return stats

    def clear_all(self):
        """Очищает все данные."""
        with self.lock:
            self.data = {}
            self._save()
            self._notify_subscribers()
            print("[RealtimeState] Cleared all data")

    def stop(self):
        """Останавливает мониторинг."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            print("[RealtimeState] Stopped file monitoring")

# Глобальный экземпляр
_state_manager = None

def get_state_manager() -> RealtimeStateManager:
    """Получает глобальный экземпляр менеджера состояния."""
    global _state_manager
    if _state_manager is None:
        _state_manager = RealtimeStateManager()
    return _state_manager

def stop_state_manager():
    """Останавливает глобальный менеджер состояния."""
    global _state_manager
    if _state_manager:
        _state_manager.stop()
        _state_manager = None

# Для тестирования
if __name__ == '__main__':
    manager = get_state_manager()

    def on_change(data):
        print(f"[Test] State changed! Users: {len(data)}")

    manager.subscribe(on_change)

    # Тест
    user = manager.get_user(12345)
    print(f"User data: {user}")

    stats = manager.get_stats()
    print(f"Stats: {stats}")

    try:
        print("Monitoring changes... Press Ctrl+C to stop")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping...")
        manager.stop()