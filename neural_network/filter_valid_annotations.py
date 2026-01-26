#!/usr/bin/env python3
"""
Фильтрация размеченных данных - удаление записей, не соответствующих новым геометрическим ограничениям
"""

import pandas as pd
from pathlib import Path
from check_annotations_geometry import check_long_constraints, check_short_constraints, get_tolerance_percent

def main():
    print("=" * 60)
    print("ФИЛЬТРАЦИЯ РАЗМЕЧЕННЫХ ДАННЫХ")
    print("=" * 60)
    print()
    print("📊 Погрешность для проверки:")
    print("   • 5 минут (5m): 0.1% от цены")
    print("   • 1 час (1h): 0.3% от цены")
    print("   • 1 день (1d): 0.5% от цены")
    print("   • Другие таймфреймы: 0.3% от цены")
    print()
    
    annotations_file = Path("neural_network/data/annotations.csv")
    backup_file = Path("neural_network/data/annotations_backup.csv")
    
    if not annotations_file.exists():
        print("❌ Файл аннотаций не найден!")
        return
    
    # Создаем резервную копию
    df = pd.read_csv(annotations_file)
    df.to_csv(backup_file, index=False)
    print(f"✅ Создана резервная копия: {backup_file}")
    print()
    
    # Фильтруем только валидные записи
    df_valid = df.dropna(subset=['t0_price', 't1_price', 't2_price', 't3_price', 't4_price'])
    
    valid_indices = []
    invalid_count = 0
    
    for idx, row in df_valid.iterrows():
        T0 = row['t0_price']
        T1 = row['t1_price']
        T2 = row['t2_price']
        T3 = row['t3_price']
        T4 = row['t4_price']
        label = row['label']
        timeframe = row.get('timeframe', '1h')  # По умолчанию 1h
        
        violations = []
        if label == 1:  # LONG
            violations = check_long_constraints(T0, T1, T2, T3, T4, timeframe)
        elif label == 2:  # SHORT
            violations = check_short_constraints(T0, T1, T2, T3, T4, timeframe)
        
        if not violations:
            valid_indices.append(idx)
        else:
            invalid_count += 1
    
    # Создаем новый DataFrame только с валидными записями
    df_filtered = df.loc[valid_indices].copy()
    
    print(f"📊 Исходное количество: {len(df)}")
    print(f"📊 С координатами: {len(df_valid)}")
    print(f"📊 Валидных (соответствуют ограничениям): {len(df_filtered)}")
    print(f"📊 Удалено невалидных: {invalid_count}")
    print()
    
    # Сохраняем отфильтрованные данные
    df_filtered.to_csv(annotations_file, index=False)
    print(f"✅ Отфильтрованные данные сохранены в: {annotations_file}")
    print()
    
    print("=" * 60)
    print("РЕКОМЕНДАЦИИ:")
    print("=" * 60)
    print()
    print("✅ Невалидные записи удалены из annotations.csv")
    print(f"✅ Осталось {len(df_filtered)} валидных записей для обучения")
    print()
    print("💡 Если нужно восстановить исходные данные:")
    print(f"   cp {backup_file} {annotations_file}")
    print()
    print("📊 Теперь можно обучать модель на валидных данных!")

if __name__ == "__main__":
    main()

