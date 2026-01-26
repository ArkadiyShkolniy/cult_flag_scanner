#!/bin/bash
# Скрипт для создания архива проекта для переноса на удаленный сервер

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

# Имя архива с датой
ARCHIVE_NAME="invest-python-backup-$(date +%Y%m%d-%H%M%S).tar.gz"
ARCHIVE_PATH="$PROJECT_DIR/../$ARCHIVE_NAME"

echo "📦 Создание архива проекта..."
echo "📁 Директория: $PROJECT_DIR"
echo "💾 Архив: $ARCHIVE_PATH"
echo ""

# Создаем архив, исключая:
# - __pycache__ и .pyc файлы
# - .git директорию (можно включить, но она большая)
# - node_modules (если есть)
# - .env файлы (не переносим секреты)
# - Docker volumes и данные
# - Модели (обучим на сервере)
# - Логи
# - Временные файлы

tar -czf "$ARCHIVE_PATH" \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='*.pyd' \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='.env' \
    --exclude='.env.local' \
    --exclude='*.log' \
    --exclude='*.pth' \
    --exclude='*.pkl' \
    --exclude='neural_network/models/*.pth' \
    --exclude='neural_network/models/*.pkl' \
    --exclude='neural_network/training_log.txt' \
    --exclude='trading_bot/trades_active.json' \
    --exclude='trading_bot/trades_history.json' \
    --exclude='.DS_Store' \
    --exclude='Thumbs.db' \
    --exclude='*.swp' \
    --exclude='*.swo' \
    --exclude='.vscode' \
    --exclude='.idea' \
    --exclude='docker-compose.override.yml' \
    --exclude='*.tar.gz' \
    --exclude='*.zip' \
    -C "$PROJECT_DIR/.." \
    "$(basename "$PROJECT_DIR")"

# Размер архива
ARCHIVE_SIZE=$(du -h "$ARCHIVE_PATH" | cut -f1)

echo "✅ Архив создан: $ARCHIVE_PATH"
echo "📊 Размер: $ARCHIVE_SIZE"
echo ""
echo "📋 Что включено в архив:"
echo "   ✓ Весь исходный код"
echo "   ✓ Конфигурационные файлы"
echo "   ✓ Docker файлы"
echo "   ✓ Документация"
echo "   ✓ Размеченные данные (annotations.csv)"
echo ""
echo "📋 Что НЕ включено (для безопасности/размера):"
echo "   ✗ .git директория (большая)"
echo "   ✗ Модели (*.pth, *.pkl) - будут обучены на сервере"
echo "   ✗ .env файлы (секреты)"
echo "   ✗ Логи и временные файлы"
echo "   ✗ Кэш Python (__pycache__)"
echo ""
echo "🚀 Следующие шаги:"
echo "   1. Перенесите архив на удаленный компьютер (USB, сеть, облако)"
echo "   2. На удаленном компьютере (WSL2):"
echo "      cd ~"
echo "      tar -xzf $ARCHIVE_NAME"
echo "      cd invest-python-main/complex_flag_scanner"
echo "      git init  # Или клонируйте из GitHub"
echo "   3. См. инструкции в TRAINING_MODELS.md для обучения моделей"
