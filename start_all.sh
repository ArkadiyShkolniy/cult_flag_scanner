#!/bin/bash
# Скрипт для запуска всех трех компонентов проекта

set -e

echo "🚀 Запуск всех компонентов торгового бота..."
echo ""

# Проверка наличия .env файла
if [ ! -f .env ]; then
    echo "❌ Ошибка: файл .env не найден!"
    echo "   Создайте файл .env с токеном TINKOFF_INVEST_TOKEN"
    exit 1
fi

# Переходим в директорию проекта
cd "$(dirname "$0")"

echo "📋 Компоненты для запуска:"
echo "   1. 🎨 Инструмент для разметки паттернов (порт 8505)"
echo "   2. 🤖 Торговый робот для отладки (порт 8506)"
echo "   3. 💰 Торговый робот на реальном рынке (порт 8502)"
echo ""

# Создаем директории для данных, если их нет
mkdir -p trading_bot/data_prod
mkdir -p neural_network/data

# Запускаем компоненты в фоновом режиме
echo "🎨 Запуск инструмента для разметки паттернов..."
streamlit run neural_network/labeling_dashboard.py --server.port=8505 --server.address=0.0.0.0 > logs/labeling.log 2>&1 &
LABELING_PID=$!
echo "   ✅ Запущен (PID: $LABELING_PID, порт 8505)"
echo "   📊 Доступ: http://localhost:8505"
echo ""

echo "🤖 Запуск торгового робота для отладки..."
python3 service.py --mode debug --enable-trading --entry-mode parallel_lines > logs/debug_bot.log 2>&1 &
DEBUG_BOT_PID=$!
echo "   ✅ Запущен (PID: $DEBUG_BOT_PID)"
echo ""

echo "📊 Запуск дашборда для отладки..."
streamlit run trading_bot/trading_dashboard.py --server.port=8506 --server.address=0.0.0.0 --server.headless=true > logs/debug_dashboard.log 2>&1 &
DEBUG_DASHBOARD_PID=$!
echo "   ✅ Запущен (PID: $DEBUG_DASHBOARD_PID, порт 8506)"
echo "   📊 Доступ: http://localhost:8506"
echo ""

echo "💰 Запуск торгового робота на реальном рынке..."
python3 service.py --mode prod --enable-trading --entry-mode parallel_lines > logs/prod_bot.log 2>&1 &
PROD_BOT_PID=$!
echo "   ✅ Запущен (PID: $PROD_BOT_PID)"
echo ""

echo "📊 Запуск дашборда для продакшена..."
streamlit run trading_bot/trading_dashboard.py --server.port=8502 --server.address=0.0.0.0 --server.headless=true --server.runOnSave=false > logs/prod_dashboard.log 2>&1 &
PROD_DASHBOARD_PID=$!
echo "   ✅ Запущен (PID: $PROD_DASHBOARD_PID, порт 8502)"
echo "   📊 Доступ: http://localhost:8502"
echo ""

# Создаем файл с PID для остановки
mkdir -p logs
cat > logs/pids.txt << EOF
LABELING=$LABELING_PID
DEBUG_BOT=$DEBUG_BOT_PID
DEBUG_DASHBOARD=$DEBUG_DASHBOARD_PID
PROD_BOT=$PROD_BOT_PID
PROD_DASHBOARD=$PROD_DASHBOARD_PID
EOF

echo "✅ Все компоненты запущены!"
echo ""
echo "📝 PID процессов сохранены в logs/pids.txt"
echo ""
echo "🌐 Доступ к компонентам:"
echo "   🎨 Разметка:     http://localhost:8505"
echo "   🤖 Отладка:      http://localhost:8506"
echo "   💰 Продакшен:    http://localhost:8502"
echo ""
echo "📋 Для остановки всех компонентов выполните:"
echo "   ./stop_all.sh"
echo ""
echo "📋 Для просмотра логов:"
echo "   tail -f logs/labeling.log"
echo "   tail -f logs/debug_bot.log"
echo "   tail -f logs/prod_bot.log"
