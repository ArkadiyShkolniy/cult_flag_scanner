#!/bin/bash
# Скрипт для очистки проекта от старых и ненужных файлов

echo "=========================================="
echo "🧹 ОЧИСТКА ПРОЕКТА"
echo "=========================================="
echo ""

# Список файлов и директорий для удаления
FILES_TO_DELETE=(
    # Backup файлы
    "neural_network/labeling_dashboard_backup.py"
    "neural_network/labeling_dashboard_enhanced.py"
    "neural_network/data_backup_20260111_130705"
    "neural_network/neural_network"  # Дублирующаяся структура
    
    # Временные/генерируемые файлы
    "neural_network/training_log.txt"
    "neural_network/analysis_MXH6_1h_20260108_122748.html"
    "neural_network/average_pattern_analysis.png"
    "neural_network/VALIDATION_ERRORS_REPORT.txt"
    
    # Старые тестовые скрипты (если не используются)
    "debug_scanner_T.py"
    "test_mxh6_after_training.py"
    "test_scanner_with_rejected.py"
    "test_stock_T.py"
    "verify_t3_fix.py"
    "neural_network/test_1d.py"
    "neural_network/test_mxh6.py"
    "neural_network/test_nn_patterns.py"
    "neural_network/test_with_patterns.py"
    
    # Устаревшие скрипты визуализации (если есть новые версии)
    "show_rejected_patterns_T.py"
    "visualize_rejected_T.py"
    "visualize_all_rules.py"
    "visualize_rules_detailed.py"
    
    # Старые примеры
    "example_hybrid_scanner.py"
    
    # Старые data loaders (если не используются)
    "neural_network/data_loader_1d.py"
    "neural_network/data_loader.py"  # Если используется data_loader_keypoints.py
    
    # Старые модели и тренеры (если не используются)
    "neural_network/model_1d.py"
    "neural_network/model.py"  # Если используется model_keypoints.py
    "neural_network/train_1d.py"
    "neural_network/train.py"  # Если используется train_keypoints.py
    "neural_network/trainer.py"  # Если используется trainer_keypoints.py
    "neural_network/predict.py"  # Если используется predict_keypoints.py
    
    # Старые скрипты анализа (если не используются)
    "analyze_geometry_violations.py"
    "analyze_nn_patterns.py"
    "analyze_pole_stats.py"
    
    # Дублирующиеся модели в корне
    "models/1d_cnn_model_best.pth"
)

echo "Файлы и директории для удаления:"
echo "-----------------------------------"
for file in "${FILES_TO_DELETE[@]}"; do
    if [ -e "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (не найден)"
    fi
done
echo ""

read -p "Продолжить удаление? (y/N): " confirm
if [[ ! $confirm =~ ^[Yy]$ ]]; then
    echo "Отмена."
    exit 0
fi

echo ""
echo "Удаление файлов..."
deleted_count=0
not_found_count=0

for file in "${FILES_TO_DELETE[@]}"; do
    if [ -e "$file" ]; then
        rm -rf "$file"
        echo "  ✅ Удален: $file"
        ((deleted_count++))
    else
        ((not_found_count++))
    fi
done

echo ""
echo "=========================================="
echo "✅ ОЧИСТКА ЗАВЕРШЕНА"
echo "   Удалено: $deleted_count"
echo "   Не найдено: $not_found_count"
echo "=========================================="
