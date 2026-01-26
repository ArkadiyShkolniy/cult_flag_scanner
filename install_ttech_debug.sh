#!/bin/bash
# Установка t-tech-investments в отладочные контейнеры

echo "🔧 Installing t-tech-investments in DEBUG containers..."

# Официальный URL wheel файла
WHEEL_URL="https://files.pythonhosted.org/packages/89/41/ca4f7b8985c74035744313af8af999d82e5793f8f3fc676b7580dadc9653/t_tech_investments-0.3.3-py3-none-any.whl"
WHEEL_FILE="/tmp/t_tech_investments-0.3.3-py3-none-any.whl"

# Функция для установки в контейнер
install_in_container() {
    local container=$1
    local name=$2
    
    if sudo docker ps | grep -q "$container"; then
        echo "📦 Installing in $name ($container)..."
        if sudo docker exec $container bash -c "wget -q $WHEEL_URL -O $WHEEL_FILE && pip install $WHEEL_FILE && rm $WHEEL_FILE" 2>&1 | grep -E "(Successfully|already|ERROR)" || true; then
            echo "   ✅ $name: Installation completed"
        else
            echo "   ⚠️ $name: Installation may have issues"
        fi
    else
        echo "   ⚠️ $name ($container): Container not running"
    fi
}

# Установка во все контейнеры
install_in_container "flag_labeling" "Labeling Dashboard"
install_in_container "trading_dashboard" "Trading Dashboard (DEBUG)"
install_in_container "trading_bot" "Trading Bot (DEBUG)"
install_in_container "flag_scanner" "Flag Scanner"

echo ""
echo "🔄 Restarting containers..."
sudo docker restart flag_labeling trading_dashboard trading_bot flag_scanner 2>/dev/null || true

echo ""
echo "✅ Done! Check status:"
echo "   sudo docker ps | grep -E 'flag_labeling|trading_dashboard|trading_bot|flag_scanner'"
