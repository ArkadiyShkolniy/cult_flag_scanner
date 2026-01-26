#!/bin/bash
# Скрипт для мониторинга обучения и уведомления о завершении

echo "🔍 Запуск мониторинга обучения..."
echo ""

# Находим PID процесса обучения
PID=$(ps aux | grep "train_keypoints.py" | grep -v grep | grep -v monitor | awk '{print $2}')

if [ -z "$PID" ]; then
    echo "⚠️  Процесс обучения не найден!"
    exit 1
fi

echo "✅ Процесс найден: PID $PID"
echo "⏳ Ожидание завершения обучения..."
echo ""

# Функция для проверки завершения
check_completion() {
    if ! ps -p "$PID" > /dev/null 2>&1; then
        return 0  # Процесс завершен
    fi
    return 1  # Процесс еще работает
}

# Мониторинг с уведомлением
while true; do
    if check_completion; then
        echo ""
        echo "═══════════════════════════════════════════════════════════"
        echo "✅ ОБУЧЕНИЕ ЗАВЕРШЕНО!"
        echo "═══════════════════════════════════════════════════════════"
        echo ""
        
        # Информация о модели
        if [ -f "neural_network/models/keypoint_model_best.pth" ]; then
            MODEL_SIZE=$(du -h neural_network/models/keypoint_model_best.pth | cut -f1)
            MODEL_TIME=$(stat -f "%Sm" -t "%Y-%m-%d %H:%M:%S" neural_network/models/keypoint_model_best.pth)
            echo "💾 Финальная модель:"
            echo "   Размер: $MODEL_SIZE"
            echo "   Время: $MODEL_TIME"
            echo ""
        fi
        
        echo "📊 Проверьте результаты:"
        echo "   • neural_network/models/keypoint_model_best.pth"
        echo "   • neural_network/models/keypoint_model_last.pth"
        echo ""
        echo "🔍 Проверьте метрики:"
        echo "   • Order penalty должен быть близок к 0"
        echo "   • Порядок точек должен соблюдаться"
        echo ""
        
        # Попытка уведомления (macOS)
        if command -v osascript > /dev/null 2>&1; then
            osascript -e 'display notification "Обучение нейронной сети завершено!" with title "Training Complete" sound name "Glass"'
        fi
        
        break
    fi
    
    sleep 30  # Проверка каждые 30 секунд
done

