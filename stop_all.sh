#!/bin/bash
# Скрипт для остановки всех компонентов

echo "🛑 Остановка всех компонентов..."

if [ -f logs/pids.txt ]; then
    source logs/pids.txt
    
    if [ ! -z "$LABELING" ]; then
        echo "   Остановка инструмента разметки (PID: $LABELING)..."
        kill $LABELING 2>/dev/null || true
    fi
    
    if [ ! -z "$DEBUG_BOT" ]; then
        echo "   Остановка торгового робота для отладки (PID: $DEBUG_BOT)..."
        kill $DEBUG_BOT 2>/dev/null || true
    fi
    
    if [ ! -z "$DEBUG_DASHBOARD" ]; then
        echo "   Остановка дашборда отладки (PID: $DEBUG_DASHBOARD)..."
        kill $DEBUG_DASHBOARD 2>/dev/null || true
    fi
    
    if [ ! -z "$PROD_BOT" ]; then
        echo "   Остановка торгового робота продакшена (PID: $PROD_BOT)..."
        kill $PROD_BOT 2>/dev/null || true
    fi
    
    if [ ! -z "$PROD_DASHBOARD" ]; then
        echo "   Остановка дашборда продакшена (PID: $PROD_DASHBOARD)..."
        kill $PROD_DASHBOARD 2>/dev/null || true
    fi
    
    rm logs/pids.txt
    echo "✅ Все компоненты остановлены"
else
    echo "⚠️ Файл logs/pids.txt не найден"
    echo "   Попытка найти процессы по имени..."
    
    pkill -f "labeling_dashboard.py" 2>/dev/null || true
    pkill -f "service.py --mode debug" 2>/dev/null || true
    pkill -f "service.py --mode prod" 2>/dev/null || true
    pkill -f "trading_dashboard.py" 2>/dev/null || true
    
    echo "✅ Процессы остановлены"
fi
