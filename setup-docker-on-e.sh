#!/bin/bash
# Скрипт для настройки Docker для хранения данных на диске E

set -e

echo "🐳 Настройка Docker для хранения данных на диске E..."
echo ""

# Проверка прав root
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Этот скрипт должен запускаться с правами root (sudo)"
    echo "   Запустите: sudo ./setup-docker-on-e.sh"
    exit 1
fi

# Создаем директорию на диске E
DOCKER_DIR="/mnt/e/docker"
echo "📁 Создание директории для Docker на диске E..."
mkdir -p "$DOCKER_DIR"/{containers,images,volumes,network,swarm,overlay2,plugins}
chmod -R 755 "$DOCKER_DIR"

# Останавливаем Docker
echo "🛑 Остановка Docker..."
systemctl stop docker 2>/dev/null || service docker stop 2>/dev/null || true

# Проверяем, есть ли существующие данные Docker
OLD_DOCKER_DIR="/var/lib/docker"
if [ -d "$OLD_DOCKER_DIR" ] && [ "$(ls -A $OLD_DOCKER_DIR 2>/dev/null)" ]; then
    echo "📦 Найдены существующие данные Docker в $OLD_DOCKER_DIR"
    read -p "Переместить существующие данные на диск E? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "📦 Перемещение данных Docker на диск E..."
        # Создаем резервную копию
        if [ -d "$OLD_DOCKER_DIR" ]; then
            mv "$OLD_DOCKER_DIR" "${OLD_DOCKER_DIR}.backup.$(date +%Y%m%d_%H%M%S)"
        fi
        # Копируем данные
        rsync -av "$OLD_DOCKER_DIR.backup."*/* "$DOCKER_DIR/" 2>/dev/null || true
    fi
fi

# Создаем симлинк или настраиваем daemon.json
echo "🔗 Настройка Docker для использования диска E..."

# Вариант 1: Симлинк (проще, но может не работать в WSL2)
if [ ! -L "$OLD_DOCKER_DIR" ] && [ ! -d "$OLD_DOCKER_DIR" ]; then
    echo "   Создание симлинка..."
    mv "$OLD_DOCKER_DIR" "${OLD_DOCKER_DIR}.old" 2>/dev/null || true
    ln -s "$DOCKER_DIR" "$OLD_DOCKER_DIR"
    echo "   ✅ Симлинк создан: $OLD_DOCKER_DIR -> $DOCKER_DIR"
fi

# Вариант 2: Настройка через daemon.json (более надежно)
DAEMON_JSON="/etc/docker/daemon.json"
DAEMON_JSON_DIR="/etc/docker"

mkdir -p "$DAEMON_JSON_DIR"

if [ -f "$DAEMON_JSON" ]; then
    echo "   Обновление существующего daemon.json..."
    # Создаем резервную копию
    cp "$DAEMON_JSON" "${DAEMON_JSON}.backup.$(date +%Y%m%d_%H%M%S)"
else
    echo "   Создание нового daemon.json..."
fi

# Обновляем или создаем daemon.json
cat > "$DAEMON_JSON" << EOF
{
  "data-root": "$DOCKER_DIR",
  "storage-driver": "overlay2"
}
EOF

echo "   ✅ daemon.json настроен"

# Запускаем Docker
echo "🚀 Запуск Docker..."
systemctl start docker 2>/dev/null || service docker start 2>/dev/null || true

# Проверяем статус
sleep 2
if docker info > /dev/null 2>&1; then
    echo ""
    echo "✅ Docker успешно настроен!"
    echo ""
    echo "📊 Информация о Docker:"
    docker info 2>/dev/null | grep -E "Docker Root Dir|Storage Driver" || true
    echo ""
    echo "📁 Данные Docker теперь хранятся в: $DOCKER_DIR"
    echo ""
    df -h "$DOCKER_DIR" | tail -1
else
    echo ""
    echo "⚠️ Docker запущен, но требуется проверка"
    echo "   Выполните: docker info"
fi

echo ""
echo "💡 Примечание: Если Docker Desktop используется в Windows,"
echo "   настройте путь к данным через Settings -> Resources -> Advanced"
