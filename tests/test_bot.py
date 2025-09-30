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


class TestTelegramAPI:
    """Tests for TelegramAPI class."""

    def test_init_without_token(self):
        """Test TelegramAPI initialization without token."""
        with pytest.raises(RuntimeError, match="Please set BOT_TOKEN"):
            bot.TelegramAPI("")

    def test_init_with_token(self):
        """Test TelegramAPI initialization with token."""
        api = bot.TelegramAPI("test_token")
        assert api.api_root == "https://api.telegram.org/bottest_token/"

    @patch('bot.urlopen')
    def test_request_success(self, mock_urlopen):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"ok": True, "result": {"test": "data"}}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        api = bot.TelegramAPI("test_token")
        result = api.request("getMe")

        assert result == {"test": "data"}

    @patch('bot.urlopen')
    def test_request_api_error(self, mock_urlopen):
        """Test API request with API error."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({"ok": False, "error": "test error"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        api = bot.TelegramAPI("test_token")

        with pytest.raises(RuntimeError, match="API error"):
            api.request("getMe")


class TestStateStore:
    """Tests for StateStore class."""

    def test_init_with_nonexistent_file(self):
        """Test StateStore initialization with non-existent file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"
            store = bot.StateStore(path)
            assert store.data == {}

    def test_init_with_existing_file(self):
        """Test StateStore initialization with existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"
            test_data = {"123": {"full_name": "Test User"}}

            with path.open('w', encoding='utf-8') as f:
                json.dump(test_data, f)

            store = bot.StateStore(path)
            assert store.data == test_data

    def test_init_with_corrupted_file(self):
        """Test StateStore initialization with corrupted file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"

            with path.open('w', encoding='utf-8') as f:
                f.write("invalid json")

            store = bot.StateStore(path)
            assert store.data == {}

    def test_save(self):
        """Test StateStore save method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"
            store = bot.StateStore(path)
            store.data = {"123": {"full_name": "Test User"}}

            store.save()

            assert path.exists()
            with path.open('r', encoding='utf-8') as f:
                saved_data = json.load(f)
            assert saved_data == {"123": {"full_name": "Test User"}}

    def test_get_user_new(self):
        """Test getting new user data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"
            store = bot.StateStore(path)

            user_data = store.get_user(123)

            assert user_data['full_name'] is None
            assert user_data['awaiting_name'] is True
            assert user_data['vk_verified'] is False
            assert 'stand_status' in user_data
            assert len(user_data['stand_status']) == 3  # Three stands

    def test_get_user_existing(self):
        """Test getting existing user data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"
            store = bot.StateStore(path)

            # Create user first
            user_data = store.get_user(123)
            user_data['full_name'] = "Test User"

            # Get same user again
            user_data_2 = store.get_user(123)

            assert user_data_2['full_name'] == "Test User"
            assert user_data is user_data_2  # Same object


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_normalize_answer(self):
        """Test answer normalization."""
        assert bot.normalize_answer("  Hello   World  ") == "hello world"
        assert bot.normalize_answer("TEST") == "test"
        assert bot.normalize_answer("arcade-12") == "arcade-12"

    def test_vk_link_pattern(self):
        """Test VK link pattern matching."""
        valid_links = [
            "https://vk.com/username",
            "http://vk.com/username",
            "www.vk.com/username",
            "vk.com/username",
            "https://vk.com/test.user_123",
        ]

        invalid_links = [
            "https://facebook.com/username",
            "vk.com",
            "not a link",
            "https://vk.com/",
        ]

        for link in valid_links:
            assert bot.VK_LINK_PATTERN.match(link), f"Should match: {link}"

        for link in invalid_links:
            assert not bot.VK_LINK_PATTERN.match(link), f"Should not match: {link}"

    def test_select_question(self):
        """Test question selection from stand."""
        stand = bot.STANDS[0]  # Neuroplay stand
        question = bot.select_question(stand)

        assert 'question' in question
        assert 'answers' in question
        assert question in stand['questions']


class TestMessageHandling:
    """Tests for message handling functions."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_api = Mock()
        bot.set_api_client(self.mock_api)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "test_state.json"
            self.state_store = bot.StateStore(path)
            bot.set_state_store(self.state_store)

    def test_handle_vk_link_valid(self):
        """Test handling valid VK link."""
        self.setUp()
        user = self.state_store.get_user(123)
        user['awaiting_vk_link'] = True

        with patch('bot.send_message') as mock_send, \
             patch('bot.ensure_giveaway_menu'), \
             patch('bot.ensure_main_menu'):

            bot.handle_vk_link(123, user, "https://vk.com/testuser")

            assert user['vk_profile'] == "https://vk.com/testuser"
            assert user['vk_verified'] is True
            assert user['awaiting_vk_link'] is False
            mock_send.assert_called_once()

    def test_handle_vk_link_invalid(self):
        """Test handling invalid VK link."""
        self.setUp()
        user = self.state_store.get_user(123)
        user['awaiting_vk_link'] = True

        with patch('bot.send_message') as mock_send:
            bot.handle_vk_link(123, user, "invalid_link")

            assert user['vk_profile'] is None
            assert user['vk_verified'] is False
            assert user['awaiting_vk_link'] is True
            mock_send.assert_called_once()

    def test_handle_pending_answer_correct(self):
        """Test handling correct answer to stand question."""
        self.setUp()
        user = self.state_store.get_user(123)
        user['pending_question'] = {
            'stand_id': 'neuroplay',
            'stand_title': 'Стенд Нейроплей',
            'answers': ['arcade-12', 'arcade12']
        }

        with patch('bot.send_message') as mock_send, \
             patch('bot.ensure_giveaway_menu'), \
             patch('bot.ensure_main_menu'):

            bot.handle_pending_answer(123, user, "arcade-12")

            assert user['stand_status']['neuroplay']['done'] is True
            assert user['pending_question'] is None
            mock_send.assert_called_once()

    def test_handle_pending_answer_incorrect(self):
        """Test handling incorrect answer to stand question."""
        self.setUp()
        user = self.state_store.get_user(123)
        user['pending_question'] = {
            'stand_id': 'neuroplay',
            'stand_title': 'Стенд Нейроплей',
            'answers': ['arcade-12', 'arcade12']
        }

        with patch('bot.send_message') as mock_send:
            bot.handle_pending_answer(123, user, "wrong_answer")

            assert user['stand_status']['neuroplay']['done'] is False
            assert user['pending_question'] is not None
            mock_send.assert_called_once()


class TestMenuGeneration:
    """Tests for menu generation functions."""

    def test_build_main_menu(self):
        """Test main menu generation."""
        user = {'stand_status': {'neuroplay': {'done': False}, 'xr': {'done': False}, 'biotech': {'done': False}}}
        menu = bot.build_main_menu(user)

        assert 'inline_keyboard' in menu
        assert len(menu['inline_keyboard']) >= 3  # Schedule, Giveaway, and Help buttons

    def test_main_menu_text_not_qualified(self):
        """Test main menu text for non-qualified user."""
        user = {'full_name': 'Test User', 'vk_verified': False, 'stand_status': {'neuroplay': {'done': False}, 'xr': {'done': False}, 'biotech': {'done': False}}}
        text = bot.main_menu_text(user)

        assert 'Добро пожаловать на Sfedunet 12!' in text
        assert 'ВЫ УЧАСТВУЕТЕ В РОЗЫГРЫШЕ!' not in text

    def test_main_menu_text_qualified(self):
        """Test main menu text for qualified user."""
        user = {
            'full_name': 'Test User',
            'vk_verified': True,
            'stand_status': {
                'neuroplay': {'done': True},
                'xr': {'done': True},
                'biotech': {'done': True}
            }
        }
        text = bot.main_menu_text(user)

        assert 'ВЫ УЧАСТВУЕТЕ В РОЗЫГРЫШЕ!' in text

    def test_build_giveaway_keyboard_incomplete(self):
        """Test giveaway keyboard for incomplete user."""
        user = {
            'vk_verified': False,
            'stand_status': {
                'neuroplay': {'done': False},
                'xr': {'done': False},
                'biotech': {'done': True}
            }
        }

        keyboard = bot.build_giveaway_keyboard(user)

        assert 'inline_keyboard' in keyboard
        # Should have VK link button, progress button, stand buttons, and back button
        assert len(keyboard['inline_keyboard']) >= 5

    def test_build_main_reply_keyboard(self):
        """Test main reply keyboard generation."""
        user = {
            'vk_verified': False,
            'stand_status': {
                'neuroplay': {'done': False},
                'xr': {'done': False},
                'biotech': {'done': False}
            }
        }

        keyboard = bot.build_main_reply_keyboard(user)

        assert 'keyboard' in keyboard
        assert keyboard['resize_keyboard'] is True
        assert len(keyboard['keyboard']) >= 2  # At least basic buttons

    def test_build_main_reply_keyboard_qualified(self):
        """Test main reply keyboard for qualified user."""
        user = {
            'vk_verified': True,
            'stand_status': {
                'neuroplay': {'done': True},
                'xr': {'done': True},
                'biotech': {'done': True}
            }
        }

        keyboard = bot.build_main_reply_keyboard(user)

        assert 'keyboard' in keyboard
        # Should have special qualified button
        keyboard_text = str(keyboard)
        assert 'УЧАСТВУЮ В РОЗЫГРЫШЕ' in keyboard_text


if __name__ == '__main__':
    pytest.main([__file__])