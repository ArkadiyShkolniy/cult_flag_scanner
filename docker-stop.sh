#!/bin/bash
# Скрипт для остановки всех компонентов через Docker

cd "$(dirname "$0")"

# Определяем команду docker-compose
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "🛑 Остановка всех компонентов..."
$DOCKER_COMPOSE -f docker-compose.all.yml stop

echo ""
echo "✅ Все компоненты остановлены"
echo ""
echo "Для полного удаления контейнеров выполните:"
echo "  $DOCKER_COMPOSE -f docker-compose.all.yml down"
