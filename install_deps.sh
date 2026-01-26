#!/bin/bash
# Скрипт для установки t-tech-investments если его нет

if ! python3 -c "import t_tech" 2>/dev/null; then
    echo "⚠️ t-tech-investments not found, attempting installation..."
    
    # Пробуем разные способы установки
    if pip install --no-cache-dir t-tech-investments==0.3.3 2>&1 | grep -q "Successfully installed"; then
        echo "✅ t-tech-investments installed successfully (version 0.3.3)"
    elif pip install --no-cache-dir t-tech-investments 2>&1 | grep -q "Successfully installed"; then
        echo "✅ t-tech-investments installed successfully (latest)"
    elif pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org t-tech-investments 2>&1 | grep -q "Successfully installed"; then
        echo "✅ t-tech-investments installed successfully (with trusted hosts)"
    elif command -v wget >/dev/null 2>&1; then
        echo "📥 Downloading wheel file from official source (https://developer.tbank.ru/invest/sdk/python_sdk/faq_python)..."
        # Официальный URL из документации T-Bank
        WHEEL_FILE="/tmp/t_tech_investments-0.3.3-py3-none-any.whl"
        if wget -q https://files.pythonhosted.org/packages/89/41/ca4f7b8985c74035744313af8af999d82e5793f8f3fc676b7580dadc9653/t_tech_investments-0.3.3-py3-none-any.whl -O "$WHEEL_FILE" 2>/dev/null && \
           pip install --no-cache-dir "$WHEEL_FILE" 2>&1 | grep -q "Successfully installed"; then
            echo "✅ t-tech-investments installed from official wheel file"
            rm -f "$WHEEL_FILE"
        else
            echo "⚠️ WARNING: t-tech-investments installation failed"
            echo "   Please install manually:"
            echo "   wget https://files.pythonhosted.org/packages/89/41/ca4f7b8985c74035744313af8af999d82e5793f8f3fc676b7580dadc9653/t_tech_investments-0.3.3-py3-none-any.whl"
            echo "   pip install t_tech_investments-0.3.3-py3-none-any.whl"
        fi
    else
        echo "⚠️ WARNING: t-tech-investments installation failed, but continuing..."
        echo "   You may need to install it manually or check network access to PyPI"
        echo "   To install manually, run: docker exec -it <container> pip install t-tech-investments"
    fi
else
    echo "✅ t-tech-investments already installed"
fi

# Запускаем команду даже если установка не удалась
exec "$@"
