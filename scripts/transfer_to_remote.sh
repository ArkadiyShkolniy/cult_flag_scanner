#!/bin/bash
# Скрипт для переноса проекта на удаленный сервер через rsync/scp
# Использование: ./transfer_to_remote.sh user@remote-host:/path/to/destination

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -z "$1" ]; then
    echo "❌ Ошибка: Укажите назначение"
    echo ""
    echo "Использование:"
    echo "  ./transfer_to_remote.sh user@host:/path/to/destination"
    echo ""
    echo "Примеры:"
    echo "  ./transfer_to_remote.sh user@192.168.1.100:~/projects/"
    echo "  ./transfer_to_remote.sh user@windows-remote:/mnt/c/projects/"
    exit 1
fi

DESTINATION="$1"
PROJECT_NAME="$(basename "$PROJECT_DIR")"

echo "📤 Перенос проекта на удаленный сервер..."
echo "📁 Источник: $PROJECT_DIR"
echo "🎯 Назначение: $DESTINATION"
echo ""

# Проверка наличия rsync
if ! command -v rsync &> /dev/null; then
    echo "❌ rsync не найден. Установите rsync:"
    echo "   macOS: brew install rsync"
    echo "   Linux: sudo apt-get install rsync"
    exit 1
fi

# Используем rsync для эффективной передачи
# --exclude - исключаем ненужные файлы
# -avz - архивный режим, verbose, сжатие
# --progress - показываем прогресс

rsync -avz --progress \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.env' \
    --exclude='*.log' \
    --exclude='*.pth' \
    --exclude='*.pkl' \
    --exclude='neural_network/models/*.pth' \
    --exclude='neural_network/models/*.pkl' \
    --exclude='trading_bot/trades_active.json' \
    --exclude='trading_bot/trades_history.json' \
    --exclude='.DS_Store' \
    --exclude='.vscode' \
    --exclude='.idea' \
    --exclude='*.tar.gz' \
    "$PROJECT_DIR/" "$DESTINATION/$PROJECT_NAME/"

echo ""
echo "✅ Перенос завершен!"
echo ""
echo "🚀 Следующие шаги на удаленном сервере:"
echo "   cd $DESTINATION/$PROJECT_NAME/complex_flag_scanner"
echo "   git init  # Или клонируйте из GitHub"
echo "   # Создайте .env файл с токенами"
echo "   # См. TRAINING_MODELS.md для обучения моделей"
