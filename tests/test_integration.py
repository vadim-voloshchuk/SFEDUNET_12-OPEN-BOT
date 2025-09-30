import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path to import bot module
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bot


class TestIntegrationFlow:
    """Integration tests for complete user flows."""

    def setup_method(self):
        """Set up test environment for each test."""
        self.mock_api = Mock()
        bot.set_api_client(self.mock_api)

        # Create temporary state file
        self.tmpdir = tempfile.mkdtemp()
        self.state_path = Path(self.tmpdir) / "test_state.json"
        self.state_store = bot.StateStore(self.state_path)
        bot.set_state_store(self.state_store)

    def teardown_method(self):
        """Clean up after each test."""
        import shutil
        shutil.rmtree(self.tmpdir)

    @patch('bot.send_message')
    @patch('bot.ensure_main_menu')
    def test_complete_registration_flow(self, mock_ensure_main, mock_send):
        """Test complete user registration flow."""
        chat_id = 123

        # Start command
        user = self.state_store.get_user(chat_id)
        bot.handle_start(chat_id, user)

        assert user['awaiting_name'] is True
        # Check that welcome message was sent (exact text may vary)
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert 'Добро пожаловать' in call_args[1]

        # Send name
        mock_send.reset_mock()
        update = {
            'message': {
                'chat': {'id': chat_id, 'type': 'private'},
                'text': 'Иван Иванов'
            }
        }

        bot.process_message(update)

        assert user['full_name'] == 'Иван Иванов'
        assert user['awaiting_name'] is False
        # Check that welcome complete message was sent
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert 'Рады знакомству, Иван Иванов' in call_args[1]
        mock_ensure_main.assert_called_once()

    @patch('bot.send_message')
    @patch('bot.ensure_giveaway_menu')
    @patch('bot.ensure_main_menu')
    def test_complete_giveaway_flow(self, mock_ensure_main, mock_ensure_giveaway, mock_send):
        """Test complete giveaway participation flow."""
        chat_id = 123
        user = self.state_store.get_user(chat_id)
        user['full_name'] = 'Test User'
        user['awaiting_name'] = False

        # Set up for VK link entry
        user['awaiting_vk_link'] = True

        # Enter valid VK link
        bot.handle_vk_link(chat_id, user, 'https://vk.com/testuser')

        assert user['vk_verified'] is True
        assert user['vk_profile'] == 'https://vk.com/testuser'
        assert user['awaiting_vk_link'] is False
        # Check that success message was sent
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert 'VK профиль добавлен' in call_args[1]

        # Complete all stands
        for stand in bot.STANDS:
            stand_id = stand['id']

            # Start question for stand
            bot.handle_stand_question(chat_id, user, stand_id, stand['title'])
            assert user['pending_question']['stand_id'] == stand_id

            # Answer correctly - use the actual answer from pending question
            mock_send.reset_mock()
            correct_answer = user['pending_question']['answers'][0]
            bot.handle_pending_answer(chat_id, user, correct_answer)

            assert user['stand_status'][stand_id]['done'] is True
            assert user['pending_question'] is None
            # Check that success message was sent
            call_args = mock_send.call_args[0]
            assert 'Правильно!' in call_args[1]

        # Verify user is now qualified for giveaway
        assert user['vk_verified'] is True
        assert all(info['done'] for info in user['stand_status'].values())

    @patch('bot.answer_callback')
    @patch('bot.send_message')
    def test_callback_handling(self, mock_send, mock_answer):
        """Test callback query handling."""
        chat_id = 123
        user = self.state_store.get_user(chat_id)

        # Test schedule callback
        update = {
            'callback_query': {
                'id': 'callback_123',
                'data': 'MAIN_SCHEDULE',
                'from': {'id': 123},
                'message': {'chat': {'id': chat_id}}
            }
        }

        bot.process_callback(update)

        mock_answer.assert_called_with('callback_123')
        # Check that schedule was sent with parse_mode
        call_args = mock_send.call_args
        assert call_args[0][0] == chat_id
        assert 'Расписание фестиваля' in call_args[0][1]

    @patch('bot.answer_callback')
    def test_unknown_callback(self, mock_answer):
        """Test handling of unknown callback data."""
        chat_id = 123

        update = {
            'callback_query': {
                'id': 'callback_123',
                'data': 'UNKNOWN_CALLBACK',
                'from': {'id': 123},
                'message': {'chat': {'id': chat_id}}
            }
        }

        bot.process_callback(update)

        mock_answer.assert_called_with('callback_123')

    @patch('bot.send_message')
    def test_stand_question_flow(self, mock_send):
        """Test complete stand question flow."""
        chat_id = 123
        user = self.state_store.get_user(chat_id)

        # Test with first stand (Neuroplay)
        stand = bot.STANDS[0]
        stand_id = stand['id']

        # Handle stand question
        bot.handle_stand_question(chat_id, user, stand_id, stand['title'])

        assert user['pending_question'] is not None
        assert user['pending_question']['stand_id'] == stand_id
        mock_send.assert_called_once()

        # Get the question that was asked
        call_args = mock_send.call_args[0]
        assert stand['title'] in call_args[1]

    def test_state_persistence(self):
        """Test that state is properly saved and loaded."""
        # Create user data
        user_id = 123
        user = self.state_store.get_user(user_id)
        user['full_name'] = 'Test User'
        user['vk_verified'] = True
        user['vk_profile'] = 'https://vk.com/testuser'

        # Save state
        self.state_store.save()

        # Create new state store instance
        new_store = bot.StateStore(self.state_path)

        # Verify data persisted
        loaded_user = new_store.get_user(user_id)
        assert loaded_user['full_name'] == 'Test User'
        assert loaded_user['vk_verified'] is True
        assert loaded_user['vk_profile'] == 'https://vk.com/testuser'

    @patch('bot.send_message')
    def test_error_handling_corrupted_message(self, mock_send):
        """Test handling of corrupted or incomplete messages."""
        # Test with missing message data
        update = {'message': None}
        bot.process_message(update)  # Should not crash

        # Test with missing chat data
        update = {'message': {'text': 'test'}}
        bot.process_message(update)  # Should not crash

        # Test with group chat (should be ignored)
        update = {
            'message': {
                'chat': {'id': 123, 'type': 'group'},
                'text': 'test'
            }
        }
        bot.process_message(update)
        mock_send.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__])