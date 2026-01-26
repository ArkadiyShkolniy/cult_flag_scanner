# 🚀 Быстрый старт через Docker

## Шаг 1: Установка Docker (если не установлен)

```bash
sudo apt update
sudo apt install docker.io docker-compose -y
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
newgrp docker  # или перезайдите в систему
```

## Шаг 2: Проверка .env файла

```bash
cd /home/ark/projects/trading_bot
cat .env
# Должно содержать: TINKOFF_INVEST_TOKEN=your_token_here
```

## Шаг 3: Запуск всех компонентов

```bash
cd /home/ark/projects/trading_bot
./docker-start.sh
```

## Шаг 4: Проверка статуса

```bash
./docker-status.sh
```

## Доступ к компонентам

После запуска откройте в браузере:

- 🎨 **Инструмент разметки:** http://localhost:8505
- 🤖 **Дашборд отладки:** http://localhost:8506  
- 💰 **Дашборд продакшена:** http://localhost:8502

## Остановка

```bash
./docker-stop.sh
```

## Просмотр логов

```bash
docker-compose -f docker-compose.all.yml logs -f
```
