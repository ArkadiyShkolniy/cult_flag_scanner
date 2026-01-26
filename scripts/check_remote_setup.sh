#!/bin/bash
# Скрипт проверки настройки удаленной среды на Windows/WSL2

echo "=========================================="
echo "🔍 ПРОВЕРКА УДАЛЕННОЙ СРЕДЫ"
echo "=========================================="

# Проверка WSL2
echo ""
echo "1️⃣ Проверка WSL2..."
if command -v wsl &> /dev/null; then
    echo "   ✅ WSL2 доступен"
    wsl --status
else
    echo "   ❌ WSL2 не найден"
fi

# Проверка Docker
echo ""
echo "2️⃣ Проверка Docker..."
if command -v docker &> /dev/null; then
    echo "   ✅ Docker установлен: $(docker --version)"
    if docker ps &> /dev/null; then
        echo "   ✅ Docker работает"
    else
        echo "   ⚠️  Docker установлен, но не запущен (запустите Docker Desktop)"
    fi
else
    echo "   ❌ Docker не установлен"
fi

# Проверка Docker Compose
echo ""
echo "3️⃣ Проверка Docker Compose..."
if command -v docker &> /dev/null && docker compose version &> /dev/null; then
    echo "   ✅ Docker Compose доступен: $(docker compose version)"
else
    echo "   ❌ Docker Compose не найден"
fi

# Проверка SSH
echo ""
echo "4️⃣ Проверка SSH..."
if systemctl is-active --quiet ssh || service ssh status &> /dev/null; then
    echo "   ✅ SSH сервер запущен"
    echo "   ℹ️  IP адрес: $(hostname -I | awk '{print $1}')"
else
    echo "   ⚠️  SSH сервер не запущен"
    echo "   💡 Запустите: sudo service ssh start"
fi

# Проверка проекта
echo ""
echo "5️⃣ Проверка проекта..."
if [ -f "docker-compose.yml" ]; then
    echo "   ✅ docker-compose.yml найден"
    if [ -f ".env" ]; then
        echo "   ✅ .env файл найден"
        if grep -q "TINKOFF_INVEST_TOKEN" .env; then
            echo "   ✅ Токен Tinkoff настроен"
        else
            echo "   ⚠️  Токен Tinkoff не найден в .env"
        fi
    else
        echo "   ⚠️  .env файл не найден"
    fi
else
    echo "   ⚠️  docker-compose.yml не найден (запустите скрипт из корня проекта)"
fi

# Проверка контейнеров
echo ""
echo "6️⃣ Проверка запущенных контейнеров..."
if command -v docker &> /dev/null && docker ps &> /dev/null; then
    containers=$(docker ps --format "{{.Names}}" 2>/dev/null)
    if [ -z "$containers" ]; then
        echo "   ⚠️  Контейнеры не запущены"
        echo "   💡 Запустите: docker compose up -d"
    else
        echo "   ✅ Запущенные контейнеры:"
        echo "$containers" | sed 's/^/      - /'
    fi
fi

# Проверка портов
echo ""
echo "7️⃣ Проверка портов..."
if command -v netstat &> /dev/null; then
    ports=(8504 8505 8506)
    for port in "${ports[@]}"; do
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            echo "   ✅ Порт $port открыт"
        else
            echo "   ⚠️  Порт $port не открыт"
        fi
    done
fi

echo ""
echo "=========================================="
echo "✅ ПРОВЕРКА ЗАВЕРШЕНА"
echo "=========================================="
