#!/usr/bin/env python3
"""
Фильтрация паттернов по геометрическим условиям
Оставляет только валидные паттерны, соответствующие геометрическим требованиям
"""
import os
import sys
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from scanners.hybrid_scanner import HybridFlagScanner
from neural_network.predict_keypoints import predict_with_sliding_window
from config import TIMEFRAMES

load_dotenv()


def is_valid_geometry(pattern, df, pattern_type):
    """
    Проверяет, соответствует ли паттерн геометрическим условиям
    
    Returns:
        True если валиден, False иначе
    """
    if 'points' not in pattern or len(pattern['points']) != 5:
        return False
    
    points = pattern['points']
    t0 = points[0]
    t1 = points[1]
    t2 = points[2]
    t3 = points[3]
    t4 = points[4]
    
    # Высота флагштока
    pole_height = abs(t1['price'] - t0['price'])
    avg_range = df[['high', 'low']].diff().abs().mean().mean()
    if pd.isna(avg_range) or avg_range == 0:
        avg_range = df['high'].max() - df['low'].min()
    min_pole_height = avg_range * 1.5
    
    if pole_height < min_pole_height:
        return False  # Флагшток слишком короткий
    
    if pattern_type == 'bearish' or pattern['class'] == 2:
        # Медвежий флаг
        
        # T3 должен быть <= T1
        if t3['price'] > t1['price'] * 1.05:
            return False
        
        # T4 должна быть выше T0
        if t4['price'] < t0['price']:
            return False
        
        # Второй откат не более 50%
        max_t4 = t0['price'] - pole_height * 0.5
        if t4['price'] < max_t4:
            return False
        
        # T2 между T1 и T3
        if not (t3['price'] <= t2['price'] <= t1['price']):
            return False
    
    else:
        # Бычий флаг
        
        # T3 должен быть >= T1 * 0.95
        if t3['price'] < t1['price'] * 0.95:
            return False
        
        # T4 должна быть выше T0
        if t4['price'] < t0['price']:
            return False
        
        # Второй откат не более 50%
        max_t4 = t0['price'] + pole_height * 0.5
        if t4['price'] > max_t4:
            return False
        
        # T2 между T0 и T1
        if not (t0['price'] <= t2['price'] <= t1['price']):
            return False
    
    # Проверка на пересечение линий со свечами (упрощенная)
    t1_idx = t1['idx']
    t3_idx = t3['idx']
    t2_idx = t2['idx']
    t4_idx = t4['idx']
    
    # Проверяем линию T1-T3
    if abs(t3_idx - t1_idx) > 1:
        start_idx = min(t1_idx, t3_idx)
        end_idx = max(t1_idx, t3_idx)
        for idx in range(start_idx + 1, end_idx):
            if 0 <= idx < len(df):
                candle = df.iloc[idx]
                line_price = t1['price'] + (t3['price'] - t1['price']) * (idx - t1_idx) / (t3_idx - t1_idx)
                body_low = min(candle['open'], candle['close'])
                body_high = max(candle['open'], candle['close'])
                if body_low <= line_price <= body_high:
                    return False  # Линия пересекает тело свечи
    
    # Проверяем линию T2-T4
    if abs(t4_idx - t2_idx) > 1:
        start_idx = min(t2_idx, t4_idx)
        end_idx = max(t2_idx, t4_idx)
        for idx in range(start_idx + 1, end_idx):
            if 0 <= idx < len(df):
                candle = df.iloc[idx]
                line_price = t2['price'] + (t4['price'] - t2['price']) * (idx - t2_idx) / (t4_idx - t2_idx)
                body_low = min(candle['open'], candle['close'])
                body_high = max(candle['open'], candle['close'])
                if body_low <= line_price <= body_high:
                    return False  # Линия пересекает тело свечи
    
    # Проверка параллельности/сходимости линий
    slope_13 = (t3['price'] - t1['price']) / (t3['idx'] - t1['idx']) if (t3['idx'] - t1['idx']) != 0 else 0
    slope_24 = (t4['price'] - t2['price']) / (t4['idx'] - t2['idx']) if (t4['idx'] - t2['idx']) != 0 else 0
    
    if pattern_type == 'bearish' or pattern['class'] == 2:
        if slope_13 < 0 and slope_24 > slope_13 * 1.1:
            return False  # Линии расходятся
    else:
        if slope_13 > 0 and slope_24 < slope_13 * 0.9:
            return False  # Линии расходятся
    
    return True  # Все проверки пройдены


def filter_valid_patterns(predictions, df):
    """Фильтрует паттерны, оставляя только валидные по геометрии"""
    valid_patterns = []
    
    for pred in predictions:
        pattern_type = "bearish" if pred['class'] == 2 else "bullish"
        if is_valid_geometry(pred, df, pattern_type):
            valid_patterns.append(pred)
    
    return valid_patterns


def main():
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        print("❌ Токен не найден!")
        return
    
    print("=" * 60)
    print("🔍 ФИЛЬТРАЦИЯ ПАТТЕРНОВ ПО ГЕОМЕТРИИ")
    print("=" * 60)
    print()
    
    ticker = "MXH6"
    class_code = "SPBFUT"
    timeframe = "1h"
    from_date = datetime(2025, 10, 20, tzinfo=timezone.utc)
    to_date = datetime(2025, 12, 20, tzinfo=timezone.utc)
    
    print(f"📊 Инструмент: {ticker}")
    print(f"📅 Период: {from_date.date()} - {to_date.date()}")
    print()
    
    # Инициализация сканера
    hybrid_scanner = HybridFlagScanner(token, use_nn=True, nn_min_confidence=0.7, device='cpu')
    
    # Загрузка данных
    print("📥 Загрузка данных...")
    tf_config = TIMEFRAMES.get(timeframe, TIMEFRAMES['1h'])
    df = hybrid_scanner.get_candles_df_by_dates(ticker, class_code, from_date, to_date, interval=tf_config['interval'])
    
    if df.empty:
        print("❌ Данные не загружены!")
        return
    
    print(f"✅ Загружено {len(df)} свечей")
    print()
    
    # Получаем предсказания
    print("🔍 Получение предсказаний от нейронной сети...")
    all_predictions = predict_with_sliding_window(
        df, hybrid_scanner.nn_model, window=100, step=10, 
        device=hybrid_scanner.device, min_confidence=0.7
    )
    
    print(f"✅ Найдено паттернов (до фильтрации): {len(all_predictions)}")
    print()
    
    # Фильтрация
    print("🔍 Фильтрация по геометрическим условиям...")
    valid_predictions = filter_valid_patterns(all_predictions, df)
    
    print(f"✅ Осталось валидных паттернов: {len(valid_predictions)}")
    print(f"   Отфильтровано: {len(all_predictions) - len(valid_predictions)} ({100 * (len(all_predictions) - len(valid_predictions)) / len(all_predictions):.1f}%)")
    print()
    
    if valid_predictions:
        # Статистика
        bullish_count = sum(1 for p in valid_predictions if p['class'] == 1)
        bearish_count = sum(1 for p in valid_predictions if p['class'] == 2)
        
        print("📊 Статистика валидных паттернов:")
        print(f"   • Бычьих флагов: {bullish_count}")
        print(f"   • Медвежьих флагов: {bearish_count}")
        print()
        
        # Уверенность
        avg_confidence = sum(p['probability'] for p in valid_predictions) / len(valid_predictions)
        print(f"📈 Средняя уверенность: {avg_confidence:.1%}")
        print()
        
        print("✅ Валидные паттерны соответствуют всем геометрическим условиям!")
        print()
        print("💡 Рекомендуется использовать только валидные паттерны для торговли")
    else:
        print("⚠️  Не найдено валидных паттернов!")
        print("   Попробуйте:")
        print("   • Уменьшить минимальную уверенность")
        print("   • Использовать гибридный подход (математический сканер)")
    
    print()
    print("=" * 60)
    print("✅ ФИЛЬТРАЦИЯ ЗАВЕРШЕНА")
    print("=" * 60)


if __name__ == "__main__":
    main()
