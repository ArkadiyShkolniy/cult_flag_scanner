#!/bin/bash
# Скрипт для запуска всех компонентов через Docker

set -e

echo "🐳 Запуск всех компонентов через Docker..."
echo ""

cd "$(dirname "$0")"

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен!"
    echo ""
    echo "Установите Docker:"
    echo "  sudo apt update"
    echo "  sudo apt install docker.io docker-compose -y"
    echo "  sudo systemctl start docker"
    echo "  sudo systemctl enable docker"
    echo "  sudo usermod -aG docker \$USER"
    echo ""
    echo "После установки перезайдите в систему или выполните:"
    echo "  newgrp docker"
    exit 1
fi

# Проверка наличия docker-compose
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ docker-compose не установлен!"
    echo ""
    echo "Установите docker-compose:"
    echo "  sudo apt install docker-compose -y"
    exit 1
fi

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Файл .env не найден!"
    echo ""
    echo "Создайте файл .env с токеном:"
    echo "  echo 'TINKOFF_INVEST_TOKEN=your_token_here' > .env"
    exit 1
fi

# Создаем директории для данных
mkdir -p trading_bot/data_prod
mkdir -p neural_network/data

echo "📋 Компоненты для запуска:"
echo "   1. 🎨 Инструмент для разметки паттернов (порт 8505)"
echo "   2. 🤖 Торговый робот для отладки"
echo "   3. 📊 Дашборд для отладки (порт 8506)"
echo "   4. 💰 Торговый робот на реальном рынке"
echo "   5. 📊 Дашборд для продакшена (порт 8502)"
echo ""

# Определяем команду docker-compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Собираем образы (если нужно)
echo "🔨 Сборка Docker образов..."
$DOCKER_COMPOSE -f docker-compose.all.yml build

echo ""
echo "🚀 Запуск всех контейнеров..."
$DOCKER_COMPOSE -f docker-compose.all.yml up -d

echo ""
echo "✅ Все компоненты запущены!"
echo ""
echo "📊 Статус контейнеров:"
$DOCKER_COMPOSE -f docker-compose.all.yml ps

echo ""
echo "🌐 Доступ к компонентам:"
echo "   🎨 Разметка:     http://localhost:8505"
echo "   🤖 Отладка:      http://localhost:8506"
echo "   💰 Продакшен:    http://localhost:8502"
echo ""
echo "📋 Полезные команды:"
echo "   Просмотр логов:     $DOCKER_COMPOSE -f docker-compose.all.yml logs -f"
echo "   Остановка:          $DOCKER_COMPOSE -f docker-compose.all.yml stop"
echo "   Перезапуск:         $DOCKER_COMPOSE -f docker-compose.all.yml restart"
echo "   Остановка и удаление: $DOCKER_COMPOSE -f docker-compose.all.yml down"
echo ""
