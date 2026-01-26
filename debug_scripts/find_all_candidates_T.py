#!/usr/bin/env python3
"""
Поиск всех кандидатов паттернов на акции T, включая отклоненные
Визуализация с пометкой причин отклонения
"""

import os
import sys
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

from scanners.bullish_flag_scanner import BullishFlagScanner
from scanners.bearish_flag_scanner import BearishFlagScanner
from config import TIMEFRAMES
from neural_network.check_annotations_geometry import check_long_constraints, check_short_constraints, check_lines_intersect_candles

load_dotenv()


def find_all_candidates_with_violations(scanner, df, timeframe, is_bullish=True):
    """Находит все кандидаты паттернов, включая отклоненные, с информацией о нарушениях"""
    candidates = []
    
    # Используем внутреннюю логику сканера
    # Для этого нужно временно модифицировать сканер или использовать его внутренние методы
    
    # Проще всего - найти точки вручную по логике сканера
    # Но это сложно, поэтому используем другой подход:
    # Временно отключим финальную проверку, модифицировав код
    
    # Вместо этого, найдем паттерны через analyze с debug=True
    # и перехватим информацию из логов или модифицируем сканер
    
    return candidates


def main():
    print("=" * 80)
    print("ПОИСК ВСЕХ КАНДИДАТОВ ПАТТЕРНОВ (ВКЛЮЧАЯ ОТКЛОНЕННЫЕ)")
    print("=" * 80)
    print()
    
    ticker = "T"
    class_code = "TQBR"
    start_date = "2025-11-17"
    end_date = "2026-01-09"
    timeframe = "1h"
    
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        print("❌ Токен не найден!")
        return
    
    bullish_scanner = BullishFlagScanner(token)
    bearish_scanner = BearishFlagScanner(token)
    
    # Загружаем данные
    df = bullish_scanner.get_candles_df(ticker, class_code, days_back=60, interval=TIMEFRAMES[timeframe]['interval'])
    df['time'] = pd.to_datetime(df['time'])
    df = df[(df['time'] >= start_date) & (df['time'] <= end_date)]
    
    print(f"✅ Загружено {len(df)} свечей")
    print()
    
    print("💡 Для показа отклоненных паттернов нужно временно модифицировать сканеры")
    print("   или создать упрощенную версию поиска паттернов")
    print()
    print("📊 Из логов отладки видно, что паттерны находятся, но отклоняются из-за:")
    print("   • T2, T3, T4 ниже требуемых уровней фибоначчи")
    print("   • Пересечения линий со свечами")
    print()
    print("🔧 Рекомендации:")
    print("   1. Проверить расчеты фибоначчи - возможно, ошибка в формулах")
    print("   2. Смягчить проверку пересечения линий - разрешить касание границ")
    print("   3. Увеличить погрешность для таймфрейма 1h (сейчас 0.3%)")


if __name__ == "__main__":
    main()
