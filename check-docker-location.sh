#!/bin/bash
# Скрипт для проверки текущего расположения данных Docker

echo "🔍 Проверка расположения данных Docker"
echo "======================================"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен"
    exit 1
fi

# Проверка запуска Docker
if ! docker info > /dev/null 2>&1; then
    echo "⚠️ Docker не запущен"
    echo ""
    echo "Попытка запуска..."
    sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
    sleep 2
fi

# Информация о Docker
echo "📊 Информация о Docker:"
echo ""
docker info 2>/dev/null | grep -E "Docker Root Dir|Storage Driver|Data Space|Metadata Space" || echo "Не удалось получить информацию"

echo ""
echo "📁 Проверка директорий:"
echo ""

# Проверка стандартной директории
if [ -d "/var/lib/docker" ]; then
    SIZE=$(du -sh /var/lib/docker 2>/dev/null | cut -f1)
    echo "   /var/lib/docker: $SIZE"
    if [ -L "/var/lib/docker" ]; then
        LINK=$(readlink -f /var/lib/docker)
        echo "      → Симлинк на: $LINK"
    fi
else
    echo "   /var/lib/docker: не существует"
fi

# Проверка директории на диске E
if [ -d "/mnt/e/docker" ]; then
    SIZE=$(du -sh /mnt/e/docker 2>/dev/null | cut -f1)
    echo "   /mnt/e/docker: $SIZE"
else
    echo "   /mnt/e/docker: не существует"
fi

# Проверка daemon.json
echo ""
echo "⚙️ Конфигурация Docker:"
if [ -f "/etc/docker/daemon.json" ]; then
    echo "   /etc/docker/daemon.json:"
    cat /etc/docker/daemon.json | sed 's/^/      /'
else
    echo "   /etc/docker/daemon.json: не найден (используются настройки по умолчанию)"
fi

# Использование дисков
echo ""
echo "💾 Использование дисков:"
df -h /mnt/e 2>/dev/null | tail -1 | awk '{print "   Диск E: " $3 " / " $2 " (" $5 " заполнено), свободно: " $4}'
df -h /mnt/c 2>/dev/null | tail -1 | awk '{print "   Диск C: " $3 " / " $2 " (" $5 " заполнено), свободно: " $4}'

echo ""
echo "💡 Для настройки Docker на диске E выполните:"
echo "   sudo ./setup-docker-on-e.sh"
