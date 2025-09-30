"""Хранилище состояния бота."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from config_manager import config_manager

logger = logging.getLogger('bot.state')

class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.data: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.path.exists():
            try:
                with self.path.open('r', encoding='utf-8') as f:
                    self.data = json.load(f)
                logger.info('State file loaded successfully from %s', self.path)
            except (json.JSONDecodeError, OSError) as exc:
                logger.error('Failed to load state file %s: %s', self.path, str(exc))
                print('[state] Corrupted state file, starting fresh.')
                self.data = {}
        else:
            logger.info('State file %s does not exist, creating new one', self.path)
            self.data = {}

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self.path.with_suffix('.tmp')
        try:
            with tmp_path.open('w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            tmp_path.replace(self.path)
            logger.debug('State file saved successfully to %s', self.path)
        except Exception as exc:
            logger.error('Failed to save state file %s: %s', self.path, str(exc))
            raise

    def get_user(self, user_id: int) -> Dict[str, Any]:
        key = str(user_id)
        stands = config_manager.get('STANDS', []) if config_manager else []

        if key not in self.data:
            logger.info('Creating new user entry for user %s', user_id)
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
            }
        else:
            # Ensure user has status for all current stands
            user_data = self.data[key]
            if 'stand_status' not in user_data:
                user_data['stand_status'] = {}

            # Add missing stands
            for stand in stands:
                if stand['id'] not in user_data['stand_status']:
                    user_data['stand_status'][stand['id']] = {'done': False}
                    logger.info('Added missing stand %s to user %s', stand['id'], user_id)

            # Remove stands that no longer exist
            current_stand_ids = {stand['id'] for stand in stands}
            stands_to_remove = [
                stand_id for stand_id in user_data['stand_status'].keys()
                if stand_id not in current_stand_ids
            ]
            for stand_id in stands_to_remove:
                del user_data['stand_status'][stand_id]
                logger.info('Removed obsolete stand %s from user %s', stand_id, user_id)

            logger.debug('Returning existing user entry for user %s', user_id)
        return self.data[key]
