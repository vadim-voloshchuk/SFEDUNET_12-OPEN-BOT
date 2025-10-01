# 🚀 VDS Deployment Guide для SFEDUNET12 Bot

## Краткий обзор

Этот проект готов к деплою на VDS с несколькими вариантами развертывания:
- 🐳 **Docker** (рекомендуется) - полностью контейнеризованное решение
- 🔧 **Systemd** - нативное развертывание с systemd сервисами
- ⚡ **Manual** - ручная настройка для разработки

## 🔧 Исправленные проблемы

✅ **Добавлены зависимости:**
- `python-telegram-bot>=20.0` - основная библиотека для бота
- `python-dotenv>=1.0.0` - загрузка переменных окружения
- `gunicorn>=21.2.0` - WSGI сервер для продакшена
- `watchdog>=3.0.0` - мониторинг файлов

✅ **Исправлен Dockerfile:**
- Копирование всех необходимых Python файлов
- Правильные права доступа для пользователя
- Улучшенные проверки здоровья

✅ **Обновлен docker-compose.yml:**
- Добавлены переменные окружения для админ панели
- Проброшен порт 5001 для веб-интерфейса
- Добавлен Nginx для reverse proxy
- Настроены health checks

✅ **Созданы скрипты деплоя:**
- `deploy.sh` - полный деплой с systemd
- `docker-deploy.sh` - быстрый Docker деплой

## 🚀 Способы деплоя

### Вариант 1: Docker (Рекомендуется)

```bash
# 1. Настройте переменные окружения
cp .env.example .env
nano .env  # Укажите BOT_TOKEN и другие настройки

# 2. Запустите Docker деплой
./docker-deploy.sh

# 3. Проверьте статус
docker-compose ps
docker-compose logs -f
```

**Преимущества:**
- ✅ Быстрое развертывание
- ✅ Изолированная среда
- ✅ Легкое обновление
- ✅ Автоматические перезапуски

### Вариант 2: Systemd сервисы

```bash
# 1. Настройте продакшн конфигурацию
cp .env.production .env
nano .env  # Укажите реальные токены

# 2. Запустите полный деплой
./deploy.sh

# 3. Проверьте сервисы
sudo systemctl status sfedunet-bot
sudo systemctl status sfedunet-admin
```

**Преимущества:**
- ✅ Нативная интеграция с системой
- ✅ Системные логи через journald
- ✅ Автозапуск при загрузке системы
- ✅ Безопасные настройки

### Вариант 3: Ручной запуск

```bash
# 1. Установите зависимости
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Настройте окружение
cp .env.example .env
nano .env

# 3. Создайте директории
mkdir -p data logs
echo "{}" > data/state.json

# 4. Запустите в двух терминалах
python bot.py
python admin_server.py
```

## 🌐 Доступ к сервисам

После успешного деплоя:

- **Telegram Bot**: Работает через Telegram API
- **Админ панель**: http://your-server:5001
- **Health check**: http://your-server:5001/health

## 📋 Настройка переменных окружения

Создайте файл `.env` со следующими параметрами:

```env
# Обязательные параметры
BOT_TOKEN=ваш_telegram_bot_token
ADMIN_SECRET_KEY=секретный_ключ_админки

# Опциональные параметры
BOT_STATE_PATH=data/state.json
FLASK_ENV=production
ADMIN_HOST=0.0.0.0
ADMIN_PORT=5001
LOG_LEVEL=INFO
```

## 🔒 Настройка безопасности

### Firewall настройки

```bash
# Разрешить только необходимые порты
sudo ufw allow ssh
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw allow 5001/tcp # Admin panel (ограничить по IP)
sudo ufw enable
```

### Nginx reverse proxy

Если используете Nginx, настройте SSL и ограничьте доступ к админке:

```nginx
# В nginx.conf уже настроено:
# - Ограничение по IP для админ панели
# - SSL конфигурация
# - Rate limiting
# - Security headers
```

## 📊 Мониторинг и логи

### Docker

```bash
# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f sfedunet-bot

# Статус контейнеров
docker-compose ps

# Перезапуск
docker-compose restart
```

### Systemd

```bash
# Статус сервисов
sudo systemctl status sfedunet-bot sfedunet-admin

# Логи в реальном времени
sudo journalctl -u sfedunet-bot -f
sudo journalctl -u sfedunet-admin -f

# Перезапуск сервисов
sudo systemctl restart sfedunet-bot
sudo systemctl restart sfedunet-admin
```

## 🔄 Обновление системы

### Docker обновление

```bash
# Остановить сервисы
docker-compose down

# Обновить код
git pull

# Пересобрать и запустить
docker-compose up -d --build
```

### Systemd обновление

```bash
# Остановить сервисы
sudo systemctl stop sfedunet-bot sfedunet-admin

# Обновить код
git pull

# Обновить зависимости
source venv/bin/activate
pip install -r requirements.txt

# Запустить сервисы
sudo systemctl start sfedunet-bot sfedunet-admin
```

## 💾 Резервное копирование

Автоматическое резервное копирование настроено в `deploy.sh`:

```bash
# Ручное создание бэкапа
./backup.sh

# Проверка бэкапов
ls -la /opt/sfedunet-bot-backups/

# Восстановление из бэкапа
cp /opt/sfedunet-bot-backups/state_YYYYMMDD_HHMMSS.json data/state.json
```

## 🆘 Решение проблем

### Бот не запускается

```bash
# Проверьте токен
grep BOT_TOKEN .env

# Проверьте логи
docker-compose logs sfedunet-bot
# или
sudo journalctl -u sfedunet-bot -n 50
```

### Админ панель недоступна

```bash
# Проверьте порт
netstat -tulpn | grep 5001

# Проверьте firewall
sudo ufw status

# Проверьте права на файлы
ls -la data/
```

### Ошибки зависимостей

```bash
# Переустановите зависимости
pip install --upgrade -r requirements.txt

# Очистите кэш Python
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete
```

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи сервисов
2. Убедитесь в правильности настроек `.env`
3. Проверьте доступность портов
4. Проверьте права доступа к файлам

---

**Система готова к продакшн использованию! 🎉**

Выберите подходящий вариант деплоя и следуйте инструкциям выше.