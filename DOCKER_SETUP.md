# 🐳 Запуск всех компонентов через Docker

## Предварительные требования

### 1. Установка Docker

```bash
# Обновление пакетов
sudo apt update

# Установка Docker
sudo apt install docker.io docker-compose -y

# Запуск Docker
sudo systemctl start docker
sudo systemctl enable docker

# Добавление пользователя в группу docker (чтобы не использовать sudo)
sudo usermod -aG docker $USER

# Перезайдите в систему или выполните:
newgrp docker
```

### 2. Проверка установки

```bash
docker --version
docker-compose --version
# или
docker compose version
```

### 3. Настройка .env файла

Убедитесь, что файл `.env` существует и содержит:

```bash
TINKOFF_INVEST_TOKEN=your_token_here
TELEGRAM_BOT_TOKEN=your_telegram_token  # Опционально
TELEGRAM_CHAT_ID=your_chat_id            # Опционально
```

## Быстрый запуск

### Вариант 1: Использование скрипта (рекомендуется)

```bash
cd /home/ark/projects/trading_bot
chmod +x docker-start.sh docker-stop.sh docker-status.sh
./docker-start.sh
```

### Вариант 2: Ручной запуск

```bash
cd /home/ark/projects/trading_bot

# Сборка образов
docker-compose -f docker-compose.all.yml build

# Запуск всех компонентов
docker-compose -f docker-compose.all.yml up -d

# Или с просмотром логов
docker-compose -f docker-compose.all.yml up
```

## Компоненты

После запуска будут доступны следующие сервисы:

| Компонент | Контейнер | Порт | URL |
|-----------|-----------|------|-----|
| 🎨 Инструмент разметки | `cult_labeling` | 8505 | http://localhost:8505 |
| 🤖 Торговый робот (отладка) | `cult_trading_bot_debug` | - | Фоновый процесс |
| 📊 Дашборд (отладка) | `cult_dashboard_debug` | 8506 | http://localhost:8506 |
| 💰 Торговый робот (продакшен) | `cult_trading_bot_prod` | - | Фоновый процесс |
| 📊 Дашборд (продакшен) | `cult_dashboard_prod` | 8502 | http://localhost:8502 |

## Управление

### Проверка статуса

```bash
./docker-status.sh
# или
docker-compose -f docker-compose.all.yml ps
```

### Просмотр логов

```bash
# Все логи
docker-compose -f docker-compose.all.yml logs -f

# Логи конкретного сервиса
docker-compose -f docker-compose.all.yml logs -f labeling
docker-compose -f docker-compose.all.yml logs -f trading-bot-debug
docker-compose -f docker-compose.all.yml logs -f trading-bot-prod
```

### Остановка

```bash
./docker-stop.sh
# или
docker-compose -f docker-compose.all.yml stop
```

### Перезапуск

```bash
docker-compose -f docker-compose.all.yml restart
```

### Полное удаление

```bash
docker-compose -f docker-compose.all.yml down
```

### Пересборка образов

```bash
docker-compose -f docker-compose.all.yml build --no-cache
docker-compose -f docker-compose.all.yml up -d
```

## Структура файлов

- `docker-compose.all.yml` - конфигурация для всех компонентов
- `docker-start.sh` - скрипт запуска
- `docker-stop.sh` - скрипт остановки
- `docker-status.sh` - скрипт проверки статуса
- `Dockerfile` - образ для всех контейнеров

## Важные замечания

⚠️ **ВНИМАНИЕ:** Торговый робот продакшена (`trading-bot-prod`) работает с **реальными деньгами**!

- Убедитесь, что все параметры настроены правильно
- Проверьте логи перед запуском продакшена
- Начните с минимальных объемов
- Мониторьте работу через дашборд

## Решение проблем

### Ошибка: "Cannot connect to the Docker daemon"
**Решение:** Убедитесь, что Docker запущен:
```bash
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker
```

### Ошибка: "Permission denied"
**Решение:** Добавьте пользователя в группу docker:
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### Ошибка: "Port already in use"
**Решение:** Остановите контейнеры или измените порты в `docker-compose.all.yml`

### Ошибка: "TINKOFF_INVEST_TOKEN не найден"
**Решение:** Создайте файл `.env` с токеном:
```bash
echo "TINKOFF_INVEST_TOKEN=your_token_here" > .env
```

## Отдельный запуск компонентов

Если нужно запустить только определенные компоненты:

```bash
# Только инструмент разметки
docker-compose -f docker-compose.all.yml up -d labeling

# Только торговый робот отладки
docker-compose -f docker-compose.all.yml up -d trading-bot-debug trading-dashboard-debug

# Только торговый робот продакшена
docker-compose -f docker-compose.all.yml up -d trading-bot-prod trading-dashboard-prod
```
