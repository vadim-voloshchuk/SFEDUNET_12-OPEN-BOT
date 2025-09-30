# Настройка продакшн-системы Sfedunet 12 Bot

## Обзор системы

Система состоит из:
1. **Telegram-бот** - основной бот для участников
2. **Веб-админ панель** - управление стендами, участниками и розыгрышем
3. **HTML-стенд розыгрыша** - интерактивный выбор победителя

## Быстрый старт

### 1. Установка зависимостей

```bash
# Установка Python зависимостей
pip install -r requirements.txt

# Или в виртуальном окружении
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Создайте файл `.env`:

```env
BOT_TOKEN=your_telegram_bot_token_here
ADMIN_SECRET_KEY=your_secret_key_for_admin_panel
BOT_STATE_PATH=data/state.json
```

### 3. Создание директорий

```bash
mkdir -p data logs
touch data/state.json
echo "{}" > data/state.json
```

### 4. Запуск системы

**Терминал 1 - Telegram бот:**
```bash
python bot.py
```

**Терминал 2 - Веб-админ панель:**
```bash
python admin_server.py
```

После запуска:
- Бот будет работать через Telegram API
- Админ-панель доступна по адресу: http://localhost:5001

## Компоненты системы

### Telegram Bot (bot.py)

**Основные функции:**
- Регистрация участников
- Прохождение стендов с вопросами
- Проверка VK профилей
- Отслеживание прогресса
- Квалификация для розыгрыша

**Файлы:**
- `bot.py` - точка входа
- `handlers.py` - обработчики сообщений
- `state.py` - управление состоянием
- `api.py` - Telegram API клиент
- `config.py` - конфигурация и контент
- `menu.py` - интерфейс и меню
- `user.py` - работа с пользователями

### Веб-админ панель (admin_server.py)

**Возможности:**
- **Управление стендами:** добавление, редактирование, удаление стендов и вопросов
- **Мониторинг участников:** статистика, прогресс, списки
- **Розыгрыш призов:** интерактивный выбор победителя
- **Реальное время:** данные обновляются автоматически

**Доступные вкладки:**
1. **Управление стендами** - полное редактирование контента
2. **Участники** - статистика и список пользователей
3. **Розыгрыш** - инструмент выбора победителя

### HTML-стенд розыгрыша

**Особенности:**
- Красивая анимация выбора
- Интеграция с реальными данными участников
- Эффекты конфетти при выборе победителя
- Возможность перезапуска розыгрыша

## API Endpoints

### GET /api/stands
Получить все стенды

### POST /api/stands
Сохранить изменения стендов в config.py

### GET /api/users
Получить всех пользователей с прогрессом

### GET /api/qualified
Получить только квалифицированных участников

### GET /api/giveaway_data
Получить данные для розыгрыша в формате HTML

## Структура данных

### Формат участника в state.json:
```json
{
  "user_id": {
    "full_name": "Имя Фамилия",
    "awaiting_name": false,
    "awaiting_vk_link": false,
    "vk_profile": "https://vk.com/username",
    "vk_verified": true,
    "stand_status": {
      "neuroplay": {"done": true},
      "xr": {"done": false},
      "biotech": {"done": false}
    },
    "pending_question": null,
    "menu_message_id": 123,
    "giveaway_message_id": 456
  }
}
```

### Формат стенда в config.py:
```python
{
    'id': 'unique_id',
    'title': '🎮 Название стенда',
    'emoji': '🧠',
    'description': 'Описание стенда',
    'color': '🟦',
    'questions': [
        {
            'question': 'Текст вопроса?',
            'answers': ['ответ1', 'ответ2'],
            'hint': '💡 Подсказка'
        }
    ]
}
```

## Администрирование

### Изменение стендов через веб-панель

1. Откройте http://localhost:5000
2. Перейдите на вкладку "Управление стендами"
3. Редактируйте стенды, добавляйте/удаляйте вопросы
4. Нажмите "Сохранить изменения"
5. Перезапустите бота для применения изменений

### Проведение розыгрыша

1. Откройте вкладку "Розыгрыш"
2. Убедитесь, что список участников актуален
3. Нажмите "Обновить участников" при необходимости
4. Нажмите "Разыграть" для выбора победителя
5. Результат отобразится с анимацией

### Мониторинг участников

На вкладке "Участники" доступна статистика:
- Общее количество участников
- Квалифицированные (прошли все стенды + VK)
- Частично прошедшие
- Новички

## Безопасность

### Рекомендации:
1. Используйте сильные пароли для `ADMIN_SECRET_KEY`
2. Ограничьте доступ к админ-панели (nginx, firewall)
3. Регулярно создавайте бэкапы `data/state.json`
4. Используйте HTTPS в продакшне

### Создание бэкапа:
```bash
# Ежедневный бэкап
cp data/state.json data/state_backup_$(date +%Y%m%d).json

# Или автоматизированно через cron
0 2 * * * cp /path/to/data/state.json /path/to/backups/state_$(date +\%Y\%m\%d).json
```

## Развертывание в продакшне

### С использованием systemd

**1. Создайте сервис для бота:**
```ini
# /etc/systemd/system/sfedu-bot.service
[Unit]
Description=Sfedunet 12 Telegram Bot
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/bot
Environment=BOT_TOKEN=your_token
ExecStart=/path/to/venv/bin/python bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**2. Создайте сервис для админ-панели:**
```ini
# /etc/systemd/system/sfedu-admin.service
[Unit]
Description=Sfedunet 12 Admin Panel
After=network.target

[Service]
Type=simple
User=botuser
WorkingDirectory=/path/to/bot
Environment=BOT_TOKEN=your_token
Environment=ADMIN_SECRET_KEY=your_secret
ExecStart=/path/to/venv/bin/python admin_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**3. Запустите сервисы:**
```bash
sudo systemctl enable sfedu-bot sfedu-admin
sudo systemctl start sfedu-bot sfedu-admin
sudo systemctl status sfedu-bot sfedu-admin
```

### С использованием Docker

```dockerfile
# Dockerfile уже есть в проекте
docker build -t sfedu-bot .
docker run -d --name sfedu-bot -p 5000:5000 --env-file .env sfedu-bot
```

### Nginx конфигурация для админ-панели

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Ограничение доступа к админ-панели
    location /admin {
        allow 192.168.1.0/24;  # Ваша сеть
        deny all;
        proxy_pass http://localhost:5000;
    }
}
```

## Мониторинг и логи

### Логи
- Бот пишет логи в `logs/bot.log`
- Flask пишет в stdout/stderr
- Ротация логов настроена автоматически

### Мониторинг состояния
```bash
# Проверка процессов
ps aux | grep python
systemctl status sfedu-bot sfedu-admin

# Проверка логов
tail -f logs/bot.log
journalctl -u sfedu-bot -f
```

## Решение проблем

### Бот не отвечает
1. Проверьте `BOT_TOKEN` в .env
2. Убедитесь, что бот добавлен в группу и имеет права
3. Проверьте логи: `tail -f logs/bot.log`

### Админ-панель не работает
1. Проверьте, запущен ли Flask сервер
2. Убедитесь, что порт 5000 свободен
3. Проверьте права доступа к файлам

### Данные участников не сохраняются
1. Проверьте права на запись в директорию `data/`
2. Убедитесь, что `data/state.json` существует
3. Проверьте место на диске

### Стенды не обновляются
1. Убедитесь, что изменения сохранены через админ-панель
2. Перезапустите бота после изменения config.py
3. Проверьте синтаксис в config.py

## Контакты и поддержка

При возникновении проблем:
1. Проверьте логи
2. Убедитесь, что все зависимости установлены
3. Проверьте конфигурацию

Система готова к продакшн-использованию! 🚀