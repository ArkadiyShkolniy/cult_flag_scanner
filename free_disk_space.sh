#!/bin/bash
# Скрипт для освобождения места на диске

echo "🧹 Освобождение места на диске..."
echo ""

# Проверить текущее использование
echo "📊 Текущее использование:"
df -h / | tail -1
echo ""

# Показать, что будет удалено
echo "🗑️  Будет удалено:"
du -sh ~/.local/lib/python3.10/site-packages/nvidia 2>/dev/null && echo "  - nvidia (CUDA библиотеки)"
du -sh ~/.local/lib/python3.10/site-packages/torch 2>/dev/null && echo "  - torch (PyTorch)"
du -sh ~/.local/lib/python3.10/site-packages/triton 2>/dev/null && echo "  - triton (компилятор)"
du -sh ~/.cursor-server 2>/dev/null && echo "  - .cursor-server (кэш)"
echo ""

# Подтверждение
read -p "Продолжить удаление? (y/n): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Отменено."
    exit 1
fi

echo ""
echo "🗑️  Удаление..."

# Удалить CUDA библиотеки
if [ -d ~/.local/lib/python3.10/site-packages/nvidia ]; then
    echo "  Удаление nvidia (CUDA)..."
    rm -rf ~/.local/lib/python3.10/site-packages/nvidia
    echo "  ✅ nvidia удален"
fi

# Удалить PyTorch
if [ -d ~/.local/lib/python3.10/site-packages/torch ]; then
    echo "  Удаление torch..."
    rm -rf ~/.local/lib/python3.10/site-packages/torch
    echo "  ✅ torch удален"
fi

# Удалить Triton
if [ -d ~/.local/lib/python3.10/site-packages/triton ]; then
    echo "  Удаление triton..."
    rm -rf ~/.local/lib/python3.10/site-packages/triton
    echo "  ✅ triton удален"
fi

# Удалить torchvision (если есть)
if [ -d ~/.local/lib/python3.10/site-packages/torchvision ]; then
    echo "  Удаление torchvision..."
    rm -rf ~/.local/lib/python3.10/site-packages/torchvision
    echo "  ✅ torchvision удален"
fi

# Очистить кэш Cursor (опционально)
if [ -d ~/.cursor-server ]; then
    echo "  Удаление .cursor-server..."
    rm -rf ~/.cursor-server
    echo "  ✅ .cursor-server удален"
fi

# Очистить pip кэш
echo "  Очистка pip кэша..."
pip3 cache purge 2>/dev/null || rm -rf ~/.cache/pip
echo "  ✅ pip кэш очищен"

echo ""
echo "📊 Новое использование:"
df -h / | tail -1
echo ""

# Показать освобожденное место
echo "✅ Очистка завершена!"
echo ""
echo "💡 Если нужен PyTorch для разметки, установите CPU версию:"
echo "   pip3 install --user torch torchvision --index-url https://download.pytorch.org/whl/cpu"
echo ""
echo "🔄 Теперь перезапустите WSL2 на Windows:"
echo "   wsl --shutdown"
