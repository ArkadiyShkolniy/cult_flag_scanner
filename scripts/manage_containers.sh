#!/bin/bash
# Скрипт для управления Docker контейнерами
# Использование: ./scripts/manage_containers.sh [start|stop|restart|status|logs]

ACTION=${1:-status}
SERVICE=${2:-""}

case $ACTION in
    start)
        echo "🚀 Запуск контейнеров..."
        docker compose up -d
        echo ""
        echo "✅ Контейнеры запущены"
        docker compose ps
        ;;
    
    stop)
        echo "🛑 Остановка контейнеров..."
        docker compose stop
        echo "✅ Контейнеры остановлены"
        ;;
    
    restart)
        echo "🔄 Перезапуск контейнеров..."
        if [ -n "$SERVICE" ]; then
            docker compose restart "$SERVICE"
            echo "✅ Сервис $SERVICE перезапущен"
        else
            docker compose restart
            echo "✅ Все контейнеры перезапущены"
        fi
        ;;
    
    status)
        echo "📊 Статус контейнеров:"
        docker compose ps
        echo ""
        echo "💻 Использование ресурсов:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
        ;;
    
    logs)
        if [ -n "$SERVICE" ]; then
            echo "📜 Логи сервиса: $SERVICE"
            docker compose logs -f "$SERVICE"
        else
            echo "📜 Логи всех сервисов (Ctrl+C для выхода):"
            docker compose logs -f
        fi
        ;;
    
    build)
        echo "🔨 Пересборка образов..."
        docker compose build
        echo "✅ Образы пересобраны"
        ;;
    
    rebuild)
        echo "🔨 Полная пересборка и перезапуск..."
        docker compose up -d --build
        echo "✅ Готово"
        ;;
    
    clean)
        echo "🧹 Очистка неиспользуемых ресурсов Docker..."
        docker system prune -f
        echo "✅ Очистка завершена"
        ;;
    
    *)
        echo "Использование: $0 [start|stop|restart|status|logs|build|rebuild|clean] [service_name]"
        echo ""
        echo "Доступные сервисы:"
        echo "  - scanner (фоновый сканер)"
        echo "  - labeling (дашборд разметки)"
        echo "  - trading-bot (торговый робот)"
        echo "  - trading-dashboard (дашборд робота)"
        echo ""
        echo "Примеры:"
        echo "  $0 start                    # Запустить все"
        echo "  $0 restart trading-bot      # Перезапустить робота"
        echo "  $0 logs labeling            # Логи дашборда"
        exit 1
        ;;
esac
