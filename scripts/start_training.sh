#!/bin/bash
# Скрипт для запуска обучения нейросети в screen сессии
# Использование: ./scripts/start_training.sh [epochs] [batch_size] [tolerance]

EPOCHS=${1:-100}
BATCH_SIZE=${2:-16}
TOLERANCE=${3:-0.003}
SESSION_NAME="nn_training"

echo "=========================================="
echo "🎓 ЗАПУСК ОБУЧЕНИЯ НЕЙРОСЕТИ"
echo "=========================================="
echo "Эпох: $EPOCHS"
echo "Batch size: $BATCH_SIZE"
echo "Tolerance: $TOLERANCE"
echo "Сессия screen: $SESSION_NAME"
echo ""

# Проверка наличия screen
if ! command -v screen &> /dev/null; then
    echo "⚠️  screen не установлен. Устанавливаю..."
    sudo apt update
    sudo apt install screen -y
fi

# Проверка, не запущена ли уже сессия
if screen -list | grep -q "$SESSION_NAME"; then
    echo "⚠️  Сессия '$SESSION_NAME' уже запущена!"
    echo "Выберите действие:"
    echo "  1) Подключиться к существующей сессии"
    echo "  2) Остановить и перезапустить"
    echo "  3) Отмена"
    read -p "Ваш выбор (1-3): " choice
    
    case $choice in
        1)
            echo "Подключаюсь к существующей сессии..."
            screen -r "$SESSION_NAME"
            exit 0
            ;;
        2)
            echo "Останавливаю существующую сессию..."
            screen -S "$SESSION_NAME" -X quit
            sleep 1
            ;;
        3)
            echo "Отмена."
            exit 0
            ;;
        *)
            echo "Неверный выбор. Отмена."
            exit 1
            ;;
    esac
fi

# Создание директории для логов если нужно
mkdir -p neural_network

# Запуск обучения в screen сессии
echo "🚀 Запускаю обучение в screen сессии..."
echo ""
echo "Инструкции:"
echo "  - Сессия будет работать в фоне даже после отключения SSH"
echo "  - Для просмотра логов: screen -r $SESSION_NAME"
echo "  - Для отключения от сессии: Ctrl+A, затем D"
echo "  - Для завершения обучения: внутри screen нажмите Ctrl+C"
echo ""

screen -dmS "$SESSION_NAME" bash -c "
    cd '$(pwd)' && \
    docker compose exec labeling python3 -u neural_network/train_keypoints.py \
        --epochs $EPOCHS \
        --batch_size $BATCH_SIZE \
        --tolerance_normalized $TOLERANCE \
        > neural_network/training_log.txt 2>&1 && \
    echo '' && \
    echo '✅ Обучение завершено!' && \
    echo 'Лог сохранен в: neural_network/training_log.txt' && \
    sleep 5
"

sleep 2

# Проверка, что сессия запущена
if screen -list | grep -q "$SESSION_NAME"; then
    echo "✅ Обучение запущено в сессии '$SESSION_NAME'"
    echo ""
    echo "Полезные команды:"
    echo "  screen -r $SESSION_NAME          # Подключиться к сессии и смотреть логи"
    echo "  tail -f neural_network/training_log.txt  # Смотреть логи без screen"
    echo "  screen -list                     # Список всех screen сессий"
    echo "  screen -S $SESSION_NAME -X quit  # Остановить обучение"
    echo ""
    echo "Сейчас можно отключиться от SSH - обучение продолжится!"
else
    echo "❌ Ошибка запуска сессии"
    exit 1
fi
