#!/bin/bash
# Скрипт для ручной установки t-tech-investments

echo "🔧 Manual installation of t-tech-investments"

# Вариант 1: Попробовать установить из локального файла (если есть)
if [ -f "/app/t_tech_investments-0.3.3-py3-none-any.whl" ]; then
    echo "📦 Found local wheel file, installing..."
    pip install /app/t_tech_investments-0.3.3-py3-none-any.whl && exit 0
fi

# Вариант 2: Попробовать скачать wheel файл напрямую
echo "📥 Attempting to download wheel file..."
if wget -q https://files.pythonhosted.org/packages/py3/t/t-tech-investments/t_tech_investments-0.3.3-py3-none-any.whl -O /tmp/t_tech_investments.whl 2>/dev/null; then
    echo "✅ Downloaded wheel file, installing..."
    pip install /tmp/t_tech_investments.whl && exit 0
fi

# Вариант 3: Попробовать установить через pip с разными опциями
echo "🔄 Trying alternative installation methods..."

# Попробовать с разными индексами
for index in "https://pypi.org/simple" "https://pypi.python.org/simple"; do
    if pip install --index-url $index t-tech-investments 2>&1 | grep -q "Successfully installed"; then
        echo "✅ Installed from $index"
        exit 0
    fi
done

echo "❌ All installation methods failed"
echo "💡 Please install manually:"
echo "   1. Download wheel file from: https://pypi.org/project/t-tech-investments/#files"
echo "   2. Copy to container: docker cp wheel_file.whl container:/tmp/"
echo "   3. Install: docker exec container pip install /tmp/wheel_file.whl"
exit 1
