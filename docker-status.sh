#!/bin/bash
# Скрипт для проверки статуса всех компонентов через Docker

cd "$(dirname "$0")"

# Определяем команду docker-compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "📊 Статус компонентов торгового бота"
echo "===================================="
echo ""

$DOCKER_COMPOSE -f docker-compose.all.yml ps

echo ""
echo "🌐 Доступ к компонентам:"
echo "   🎨 Разметка:     http://localhost:8505"
echo "   🤖 Отладка:      http://localhost:8506"
echo "   💰 Продакшен:    http://localhost:8502"
echo ""
echo "📋 Просмотр логов:"
echo "   Все логи:        $DOCKER_COMPOSE -f docker-compose.all.yml logs -f"
echo "   Разметка:        $DOCKER_COMPOSE -f docker-compose.all.yml logs -f labeling"
echo "   Отладка бот:     $DOCKER_COMPOSE -f docker-compose.all.yml logs -f trading-bot-debug"
echo "   Продакшен бот:   $DOCKER_COMPOSE -f docker-compose.all.yml logs -f trading-bot-prod"
