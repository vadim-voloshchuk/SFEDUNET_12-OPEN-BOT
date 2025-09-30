"""API клиент для Telegram Bot."""

import json
import logging
import logging.handlers
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

logger = logging.getLogger('bot.api')

class TelegramAPI:
    """Minimal Telegram Bot API client using urllib to avoid extra deps."""

    def __init__(self, token: str) -> None:
        if not token:
            raise RuntimeError('Please set BOT_TOKEN environment variable with your Telegram bot token.')
        self.api_root = f'https://api.telegram.org/bot{token}/'

    def request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        url = f'{self.api_root}{method}'
        data_bytes = None
        if params is not None:
            encoded_params: Dict[str, Any] = {}
            for key, value in params.items():
                if value is None:
                    continue
                if isinstance(value, (dict, list)):
                    encoded_params[key] = json.dumps(value, ensure_ascii=False)
                else:
                    encoded_params[key] = value
            data_bytes = urlencode(encoded_params).encode('utf-8')
        request = Request(url, data=data_bytes)
        logger.debug('Making API call to %s with params: %s', method, params)
        try:
            with urlopen(request, timeout=60) as response:
                payload = response.read()
        except HTTPError as exc:  # pragma: no cover - network errors tested separately
            logger.error('HTTPError calling %s: %s', method, exc.read().decode())
            raise RuntimeError(f'HTTPError calling {method}: {exc.read().decode()}') from exc
        except URLError as exc:  # pragma: no cover - network errors tested separately
            logger.error('URLError calling %s: %s', method, exc)
            raise RuntimeError(f'URLError calling {method}: {exc}') from exc
        result = json.loads(payload.decode('utf-8'))
        if not result.get('ok'):
            logger.error('API error on %s: %s', method, result)
            raise RuntimeError(f'API error on {method}: {result}')
        logger.debug('API call to %s successful', method)
        return result['result']
