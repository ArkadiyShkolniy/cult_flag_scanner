# 🖥️ Развертывание на удаленном сервере (Linux)

## Содержание
1. [Варианты серверов](#1-варианты-серверов)
2. [Подготовка сервера](#2-подготовка-сервера)
3. [Вариант A: Docker Compose (рекомендуется)](#3-вариант-a-docker-compose-рекомендуется)
4. [Вариант B: Systemd сервисы](#4-вариант-b-systemd-сервисы)
5. [Вариант C: Screen/Tmux](#5-вариант-c-screentmux)
6. [Мониторинг и логи](#6-мониторинг-и-логи)
7. [Доступ к дашбордам](#7-доступ-к-дашбордам)
8. [Автоматический деплой](#8-автоматический-деплой)

---

## 1. Варианты серверов

### Облачные провайдеры (VPS)
- **DigitalOcean** ($6-12/мес) - простой, хорошая документация
- **Hetzner** (€4-8/мес) - дешево, Европа
- **Linode** ($5-10/мес) - хорошая производительность
- **AWS Lightsail** ($3.50-10/мес) - интеграция с AWS
- **Yandex Cloud** / **Selectel** - российские провайдеры

### Требования к серверу
- **CPU:** 2+ ядра (для обучения нейросети)
- **RAM:** 4GB+ (рекомендуется 8GB)
- **Диск:** 20GB+ SSD
- **ОС:** Ubuntu 20.04/22.04 LTS (рекомендуется)
- **Сеть:** Стабильное подключение (для API запросов)

---

## 2. Подготовка сервера

### Шаг 2.1: Первоначальная настройка
```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка базовых инструментов
sudo apt install -y git curl wget build-essential

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER

# Установка Docker Compose (если не установлен)
sudo apt install docker-compose-plugin -y

# Выйти и войти заново для применения групп
exit
# (войти снова через SSH)
```

### Шаг 2.2: Настройка SSH ключей (опционально, но рекомендуется)
```bash
# На локальной машине сгенерировать ключ (если еще нет)
ssh-keygen -t ed25519 -C "your_email@example.com"

# Скопировать ключ на сервер
ssh-copy-id user@your_server_ip

# Теперь можно подключаться без пароля
ssh user@your_server_ip
```

### Шаг 2.3: Клонирование проекта
```bash
# Создать директорию для проектов
mkdir -p ~/projects
cd ~/projects

# Клонировать репозиторий
git clone <URL_ВАШЕГО_РЕПОЗИТОРИЯ>
cd invest-python-main/complex_flag_scanner

# Создать .env файл
nano .env
```

Добавить в `.env`:
```
TINKOFF_INVEST_TOKEN=your_token_here
```

---

## 3. Вариант A: Docker Compose (рекомендуется)

### Преимущества
- ✅ Изоляция сервисов
- ✅ Автоматический перезапуск
- ✅ Простое управление
- ✅ Легкое масштабирование

### Шаг 3.1: Запуск всех сервисов
```bash
cd ~/projects/invest-python-main/complex_flag_scanner

# Сборка образов (первый раз)
docker compose build

# Запуск всех сервисов в фоне
docker compose up -d

# Проверка статуса
docker compose ps

# Просмотр логов
docker compose logs -f
```

### Шаг 3.2: Настройка автозапуска
Docker Compose автоматически перезапускает контейнеры при перезагрузке сервера (благодаря `restart: unless-stopped` в `docker-compose.yml`).

Но если нужно, можно создать systemd сервис для docker-compose:

```bash
sudo nano /etc/systemd/system/trading-bot.service
```

Содержимое:
```ini
[Unit]
Description=Trading Bot Services
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/your_user/projects/invest-python-main/complex_flag_scanner
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot.service
sudo systemctl start trading-bot.service
```

---

## 4. Вариант B: Systemd сервисы

Если не хотите использовать Docker, можно запустить как systemd сервисы.

### Шаг 4.1: Установка зависимостей
```bash
# Установка Python и зависимостей
sudo apt install -y python3 python3-pip python3-venv

# Создание виртуального окружения
cd ~/projects/invest-python-main/complex_flag_scanner
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Шаг 4.2: Создание systemd сервиса для торгового бота
```bash
sudo nano /etc/systemd/system/trading-bot.service
```

Содержимое:
```ini
[Unit]
Description=Trading Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/home/your_user/projects/invest-python-main/complex_flag_scanner
Environment="PATH=/home/your_user/projects/invest-python-main/complex_flag_scanner/venv/bin"
ExecStart=/home/your_user/projects/invest-python-main/complex_flag_scanner/venv/bin/python3 run_trading_bot.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Активация:
```bash
sudo systemctl daemon-reload
sudo systemctl enable trading-bot.service
sudo systemctl start trading-bot.service

# Проверка статуса
sudo systemctl status trading-bot.service

# Просмотр логов
sudo journalctl -u trading-bot.service -f
```

---

## 5. Вариант C: Screen/Tmux

Для быстрого запуска без systemd.

### Установка Screen
```bash
sudo apt install screen -y
```

### Запуск торгового бота в screen
```bash
# Создать screen сессию
screen -S trading-bot

# Внутри screen:
cd ~/projects/invest-python-main/complex_flag_scanner
docker compose up

# Отключиться: Ctrl+A, затем D
# Подключиться обратно: screen -r trading-bot
```

### Запуск обучения в screen
```bash
screen -S training
cd ~/projects/invest-python-main/complex_flag_scanner
./scripts/start_training.sh 100 16 0.003
```

---

## 6. Мониторинг и логи

### Docker Compose логи
```bash
# Все логи
docker compose logs -f

# Конкретный сервис
docker compose logs -f trading-bot
docker compose logs -f labeling

# Последние 100 строк
docker compose logs --tail=100 trading-bot
```

### Systemd логи
```bash
# Логи сервиса
sudo journalctl -u trading-bot.service -f

# Последние 100 строк
sudo journalctl -u trading-bot.service -n 100
```

### Мониторинг ресурсов
```bash
# Использование ресурсов контейнерами
docker stats

# Использование ресурсов системой
htop  # или top

# Свободное место на диске
df -h
```

### Настройка logrotate (для systemd)
```bash
sudo nano /etc/logrotate.d/trading-bot
```

Содержимое:
```
/var/log/trading-bot/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 your_user your_user
}
```

---

## 7. Доступ к дашбордам

### Вариант 7.1: SSH туннелирование (безопасный, рекомендуется)

**На локальной машине:**
```bash
# Проброс портов через SSH
ssh -L 8505:localhost:8505 -L 8506:localhost:8506 user@your_server_ip

# Теперь в браузере:
# http://localhost:8505 - Дашборд разметки
# http://localhost:8506 - Trading Dashboard
```

### Вариант 7.2: Nginx reverse proxy (для постоянного доступа)

```bash
# Установка Nginx
sudo apt install nginx certbot python3-certbot-nginx -y

# Создание конфигурации
sudo nano /etc/nginx/sites-available/trading-bot
```

Содержимое:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Или IP адрес

    location /labeling {
        proxy_pass http://localhost:8505;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /trading {
        proxy_pass http://localhost:8506;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

Активация:
```bash
sudo ln -s /etc/nginx/sites-available/trading-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Если есть домен, получить SSL сертификат:
sudo certbot --nginx -d your-domain.com
```

### Вариант 7.3: Cloudflare Tunnel (безопасно, бесплатно)

```bash
# Установка cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Аутентификация
cloudflared tunnel login

# Создание туннеля
cloudflared tunnel create trading-bot

# Настройка (после создания туннеля)
cloudflared tunnel route dns trading-bot your-subdomain.yourdomain.com
```

---

## 8. Автоматический деплой

### Вариант 8.1: Git + Webhook

#### На сервере:
```bash
# Установка webhook сервера
sudo apt install webhook -y

# Создание скрипта обновления
nano ~/deploy.sh
```

Содержимое `deploy.sh`:
```bash
#!/bin/bash
cd ~/projects/invest-python-main/complex_flag_scanner
git pull
docker compose build
docker compose up -d
echo "Deployment completed at $(date)"
```

Сделать исполняемым:
```bash
chmod +x ~/deploy.sh
```

Создать webhook конфигурацию:
```bash
sudo nano /etc/webhook.conf
```

Содержимое:
```json
[
  {
    "id": "trading-bot-deploy",
    "execute-command": "/home/your_user/deploy.sh",
    "command-working-directory": "/home/your_user",
    "response-message": "Deployment started"
  }
]
```

Запустить webhook:
```bash
sudo systemctl enable webhook
sudo systemctl start webhook
```

#### На GitHub/GitLab:
Добавить webhook URL: `http://your_server_ip:9000/hooks/trading-bot-deploy`

### Вариант 8.2: GitHub Actions (для CI/CD)

Создать `.github/workflows/deploy.yml`:
```yaml
name: Deploy to Server

on:
  push:
    branches: [ main, master ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.SERVER_HOST }}
          username: ${{ secrets.SERVER_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          script: |
            cd ~/projects/invest-python-main/complex_flag_scanner
            git pull
            docker compose build
            docker compose up -d
```

---

## Быстрый старт (после настройки)

```bash
# 1. Подключиться к серверу
ssh user@your_server_ip

# 2. Перейти в проект
cd ~/projects/invest-python-main/complex_flag_scanner

# 3. Обновить код
git pull

# 4. Перезапустить сервисы
docker compose down
docker compose up -d --build

# 5. Проверить статус
docker compose ps
docker compose logs -f trading-bot
```

---

## Полезные команды

### Управление контейнерами
```bash
# Остановить все
docker compose stop

# Запустить снова
docker compose start

# Перезапустить конкретный сервис
docker compose restart trading-bot

# Посмотреть использование ресурсов
docker stats

# Очистка неиспользуемых ресурсов
docker system prune -a
```

### Мониторинг обучения
```bash
# Если обучение в screen
screen -r training

# Или через Docker
docker compose exec labeling tail -f neural_network/training_log.txt
```

### Резервное копирование
```bash
# Backup аннотаций
tar -czf backup_annotations_$(date +%Y%m%d).tar.gz neural_network/data/annotations.csv

# Backup моделей
tar -czf backup_models_$(date +%Y%m%d).tar.gz neural_network/models/

# Отправить на локальную машину через SCP
scp backup_*.tar.gz user@local_machine:/backup/
```

---

## Troubleshooting

### Контейнеры не запускаются
```bash
# Проверить логи
docker compose logs

# Проверить, не заняты ли порты
sudo netstat -tulpn | grep -E '8504|8505|8506'

# Пересобрать образы
docker compose build --no-cache
docker compose up -d
```

### Нехватка памяти
```bash
# Проверить использование
free -h
docker stats

# Если нехватка, можно ограничить ресурсы в docker-compose.yml:
# deploy:
#   resources:
#     limits:
#       memory: 2G
```

### Проблемы с сетью/API
```bash
# Проверить доступность API
curl -I https://invest-public-api.tinkoff.ru

# Проверить DNS
nslookup invest-public-api.tinkoff.ru
```

---

**Рекомендация:** Используйте **Вариант A (Docker Compose)** - это самый простой и надежный способ развертывания.
