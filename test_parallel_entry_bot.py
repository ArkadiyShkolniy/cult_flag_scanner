"""
Тестирование логики входа по параллельности в торговом боте.
"""
import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from trading_bot.trade_strategy import TradeStrategy
from trading_bot.parallel_entry_strategy import check_parallel_entry, ParallelEntryStrategy

load_dotenv()

def test_parallel_entry_with_real_data():
    """
    Тестирует логику входа по параллельности на реальных данных.
    Требует Docker окружения с установленными зависимостями.
    """
    print("=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ ЛОГИКИ ВХОДА ПО ПАРАЛЛЕЛЬНОСТИ (РЕАЛЬНЫЕ ДАННЫЕ)")
    print("=" * 70)
    print()
    print("⚠️  Для тестирования на реальных данных используйте Docker окружение:")
    print("   docker-compose exec app python test_parallel_entry_bot.py --mode real")
    print()
    print("   Или запустите в контейнере с установленными зависимостями.")
    print()


def test_parallel_entry_with_synthetic_data():
    """
    Тестирует логику входа по параллельности на синтетических данных.
    """
    print("=" * 70)
    print("🧪 ТЕСТИРОВАНИЕ НА СИНТЕТИЧЕСКИХ ДАННЫХ")
    print("=" * 70)
    print()
    
    # Создаем синтетические данные для LONG паттерна
    np.random.seed(42)
    n_candles = 100
    base_price = 100
    
    # Генерируем паттерн
    prices = []
    for i in range(n_candles):
        if i < 30:
            # Тренд вверх (T0 -> T1)
            price = base_price + (i / 30) * 20
        elif i < 45:
            # Коррекция вниз (T1 -> T2)
            price = base_price + 20 - ((i - 30) / 15) * 10
        elif i < 65:
            # Отскок вверх (T2 -> T3)
            price = base_price + 10 + ((i - 45) / 20) * 8
        else:
            # Финальная коррекция (T3 -> T4)
            price = base_price + 18 - ((i - 65) / 15) * 6
        
        prices.append(price + np.random.normal(0, 0.5))
    
    # Создаем DataFrame
    df = pd.DataFrame({
        'open': prices,
        'high': [p + abs(np.random.normal(0, 1)) for p in prices],
        'low': [p - abs(np.random.normal(0, 1)) for p in prices],
        'close': [p + np.random.normal(0, 0.5) for p in prices],
        'volume': np.random.randint(1000, 10000, n_candles)
    })
    
    # Добавляем EMA
    df['ema_7'] = df['close'].ewm(span=7).mean()
    df['ema_14'] = df['close'].ewm(span=14).mean()
    
    # Определяем точки паттерна
    t0_idx = 0
    t1_idx = 29
    t2_idx = 44
    t3_idx = 64
    t4_idx = 79
    
    pattern = {
        'pattern': 'BULLISH_FLAG',
        't0': {'idx': t0_idx, 'price': df.iloc[t0_idx]['close']},
        't1': {'idx': t1_idx, 'price': df.iloc[t1_idx]['close']},
        't2': {'idx': t2_idx, 'price': df.iloc[t2_idx]['close']},
        't3': {'idx': t3_idx, 'price': df.iloc[t3_idx]['close']},
        't4': {'idx': t4_idx, 'price': df.iloc[t4_idx]['close']},
    }
    
    print("📊 Синтетический паттерн:")
    print(f"   T0: {pattern['t0']['price']:.2f} (idx={t0_idx})")
    print(f"   T1: {pattern['t1']['price']:.2f} (idx={t1_idx})")
    print(f"   T2: {pattern['t2']['price']:.2f} (idx={t2_idx})")
    print(f"   T3: {pattern['t3']['price']:.2f} (idx={t3_idx})")
    print(f"   T4: {pattern['t4']['price']:.2f} (idx={t4_idx})")
    print()
    
    # Симулируем разные сценарии
    scenarios = [
        {'name': 'Текущая цена выше open T4 (LONG)', 'current_idx': t4_idx, 'current_price_offset': 2},
        {'name': 'Текущая цена ниже open T4 (LONG)', 'current_idx': t4_idx, 'current_price_offset': -2},
        {'name': 'Текущая цена = open T4 (LONG)', 'current_idx': t4_idx, 'current_price_offset': 0},
    ]
    
    strategy = TradeStrategy()
    
    for scenario in scenarios:
        print(f"🔍 Сценарий: {scenario['name']}")
        
        # Обрезаем DataFrame до текущего индекса
        test_df = df.iloc[:scenario['current_idx'] + 1].copy()
        
        # Устанавливаем текущую цену
        t4_open = test_df.iloc[t4_idx]['open']
        current_price = t4_open + scenario['current_price_offset']
        
        # Обновляем close последней свечи
        test_df.iloc[-1, test_df.columns.get_loc('close')] = current_price
        
        print(f"   Текущий индекс: {len(test_df) - 1}")
        print(f"   T4 индекс: {t4_idx}")
        print(f"   Open T4: {t4_open:.2f}")
        print(f"   Текущая цена: {current_price:.2f}")
        
        signal, desc = strategy.check_entry_signal(
            test_df,
            pattern,
            entry_mode="parallel_lines",
            current_price=current_price
        )
        
        if signal:
            print(f"   ✅ СИГНАЛ НА ВХОД!")
        else:
            print(f"   ❌ Сигнала нет")
        print(f"   📝 {desc}")
        print()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Тестирование логики входа по параллельности')
    parser.add_argument('--mode', type=str, choices=['real', 'synthetic', 'both'], default='both',
                        help='Режим тестирования: real (реальные данные), synthetic (синтетические), both (оба)')
    args = parser.parse_args()
    
    if args.mode in ['real', 'both']:
        test_parallel_entry_with_real_data()
        print()
    
    if args.mode in ['synthetic', 'both']:
        test_parallel_entry_with_synthetic_data()
