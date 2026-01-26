#!/bin/bash
# Скрипт для автоматического развертывания на удаленном сервере
# Использование: ./scripts/deploy_to_server.sh user@server_ip

if [ -z "$1" ]; then
    echo "Использование: $0 user@server_ip"
    echo "Пример: $0 root@192.168.1.100"
    exit 1
fi

SERVER=$1
REMOTE_DIR="~/projects/invest-python-main/complex_flag_scanner"

echo "=========================================="
echo "🚀 РАЗВЕРТЫВАНИЕ НА СЕРВЕР"
echo "=========================================="
echo "Сервер: $SERVER"
echo "Директория: $REMOTE_DIR"
echo ""

# Проверка подключения
echo "1️⃣ Проверка подключения к серверу..."
if ! ssh -o ConnectTimeout=5 "$SERVER" "echo 'Connected'" > /dev/null 2>&1; then
    echo "❌ Не удалось подключиться к серверу"
    echo "Проверьте:"
    echo "  - Правильность IP адреса"
    echo "  - Настройки SSH ключей"
    echo "  - Доступность сервера"
    exit 1
fi
echo "✅ Подключение установлено"
echo ""

# Проверка Docker
echo "2️⃣ Проверка Docker на сервере..."
if ! ssh "$SERVER" "command -v docker > /dev/null 2>&1"; then
    echo "⚠️  Docker не установлен на сервере"
    echo "Установите Docker перед продолжением:"
    echo "  curl -fsSL https://get.docker.com -o get-docker.sh"
    echo "  sudo sh get-docker.sh"
    exit 1
fi
echo "✅ Docker установлен"
echo ""

# Создание директории если нужно
echo "3️⃣ Подготовка директории на сервере..."
ssh "$SERVER" "mkdir -p $(dirname $REMOTE_DIR)" 2>/dev/null
echo "✅ Директория готова"
echo ""

# Копирование файлов (если нужно)
read -p "Скопировать файлы проекта на сервер? (y/N): " copy_files
if [[ $copy_files =~ ^[Yy]$ ]]; then
    echo "4️⃣ Копирование файлов..."
    rsync -avz --exclude '__pycache__' --exclude '*.pyc' --exclude '.git' \
        -e ssh ./ "$SERVER:$REMOTE_DIR/"
    echo "✅ Файлы скопированы"
else
    echo "4️⃣ Пропуск копирования (предполагается, что код уже на сервере)"
fi
echo ""

# Запуск на сервере
echo "5️⃣ Запуск на сервере..."
ssh "$SERVER" "cd $REMOTE_DIR && \
    docker compose down && \
    docker compose build && \
    docker compose up -d && \
    echo '✅ Сервисы запущены' && \
    docker compose ps"

echo ""
echo "=========================================="
echo "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО"
echo "=========================================="
echo ""
echo "Полезные команды:"
echo "  ssh $SERVER 'cd $REMOTE_DIR && docker compose logs -f'"
echo "  ssh $SERVER 'cd $REMOTE_DIR && docker compose ps'"
echo "  ssh $SERVER 'cd $REMOTE_DIR && docker compose restart trading-bot'"
