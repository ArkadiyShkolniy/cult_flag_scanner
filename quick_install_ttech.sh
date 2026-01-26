#!/bin/bash
# Быстрая установка t-tech-investments в контейнерах
# Использует официальный wheel файл из https://developer.tbank.ru/invest/sdk/python_sdk/faq_python

echo "🔧 Installing t-tech-investments in containers..."

# Официальный URL wheel файла
WHEEL_URL="https://files.pythonhosted.org/packages/89/41/ca4f7b8985c74035744313af8af999d82e5793f8f3fc676b7580dadc9653/t_tech_investments-0.3.3-py3-none-any.whl"
WHEEL_FILE="/tmp/t_tech_investments-0.3.3-py3-none-any.whl"

# Функция для ожидания готовности контейнера
wait_for_container() {
    local container=$1
    local max_attempts=10
    local attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if sudo docker exec $container echo "ready" >/dev/null 2>&1; then
            return 0
        fi
        echo "   Waiting for container $container to be ready... ($attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done
    return 1
}

# Установка в дашборде
echo "📦 Installing in dashboard_prod..."
if wait_for_container dashboard_prod; then
    sudo docker exec dashboard_prod bash -c "wget -q $WHEEL_URL -O $WHEEL_FILE && pip install $WHEEL_FILE && rm $WHEEL_FILE" 2>&1 | grep -E "(Successfully|ERROR|already)" || echo "   Installation completed"
else
    echo "   ❌ Container dashboard_prod is not ready"
fi

# Установка в сканере
echo "📦 Installing in cult_bot_prod..."
if wait_for_container cult_bot_prod; then
    sudo docker exec cult_bot_prod bash -c "wget -q $WHEEL_URL -O $WHEEL_FILE && pip install $WHEEL_FILE && rm $WHEEL_FILE" 2>&1 | grep -E "(Successfully|ERROR|already)" || echo "   Installation completed"
else
    echo "   ❌ Container cult_bot_prod is not ready"
fi

# Проверка
echo ""
echo "✅ Checking installation..."
sudo docker exec dashboard_prod python3 -c "import t_tech; print('✅ dashboard_prod: OK')" 2>/dev/null || echo "❌ dashboard_prod: FAILED"
sudo docker exec cult_bot_prod python3 -c "import t_tech; print('✅ cult_bot_prod: OK')" 2>/dev/null || echo "❌ cult_bot_prod: FAILED"

echo ""
echo "🔄 Restarting containers..."
sudo docker restart dashboard_prod cult_bot_prod

echo "✅ Done! Check logs: docker logs dashboard_prod"
