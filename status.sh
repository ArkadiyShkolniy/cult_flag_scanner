#!/bin/bash
# Скрипт для проверки статуса всех компонентов

cd "$(dirname "$0")"

echo "📊 Статус компонентов торгового бота"
echo "===================================="
echo ""

# Проверяем каждый компонент
check_component() {
    local name=$1
    local pid_file=$2
    local port=$3
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file" 2>/dev/null)
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "✅ $name: Работает (PID: $pid)"
            if [ ! -z "$port" ]; then
                if netstat -tuln 2>/dev/null | grep -q ":$port " || ss -tuln 2>/dev/null | grep -q ":$port "; then
                    echo "   🌐 Порт $port: Открыт"
                else
                    echo "   ⚠️  Порт $port: Не отвечает"
                fi
            fi
        else
            echo "❌ $name: Остановлен (PID файл существует, но процесс не найден)"
        fi
    else
        echo "⚪ $name: Не запущен"
    fi
}

check_component "🎨 Инструмент разметки" "logs/labeling.pid" "8505"
check_component "🤖 Торговый робот (отладка)" "logs/debug_bot.pid" ""
check_component "📊 Дашборд (отладка)" "logs/debug_dashboard.pid" "8506"
check_component "💰 Торговый робот (продакшен)" "logs/prod_bot.pid" ""
check_component "📊 Дашборд (продакшен)" "logs/prod_dashboard.pid" "8502"

echo ""
echo "🌐 Доступ к компонентам:"
echo "   🎨 Разметка:     http://localhost:8505"
echo "   🤖 Отладка:      http://localhost:8506"
echo "   💰 Продакшен:    http://localhost:8502"
echo ""
echo "📋 Для просмотра логов:"
echo "   tail -f logs/labeling.log"
echo "   tail -f logs/debug_bot.log"
echo "   tail -f logs/prod_bot.log"
