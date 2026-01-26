"""
Трекер паттернов без T4 для отслеживания в реальном времени
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import pandas as pd


class PatternWatcher:
    """
    Класс для отслеживания паттернов без T4 и входа в момент формирования T4
    """
    
    def __init__(self):
        # Храним паттерны без T4: ключ = (ticker, timeframe, t1_time), значение = паттерн
        self.watched_patterns: Dict[Tuple[str, str, str], dict] = {}
    
    def add_pattern_without_t4(self, ticker: str, timeframe: str, pattern: dict):
        """
        Добавляет паттерн без T4 для отслеживания
        
        Args:
            ticker: Тикер инструмента
            timeframe: Таймфрейм
            pattern: Паттерн с T0, T1, T2, T3 (без T4)
        """
        t1 = pattern.get('t1', {})
        t1_time = t1.get('time', '')
        key = (ticker, timeframe, t1_time)
        
        # Сохраняем паттерн для отслеживания
        self.watched_patterns[key] = {
            'ticker': ticker,
            'timeframe': timeframe,
            'pattern': pattern,
            'added_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def check_t4_formation(self, ticker: str, timeframe: str, df: pd.DataFrame, 
                          current_idx: int, tolerance_percent: float = 0.01) -> Optional[dict]:
        """
        Проверяет, сформировалась ли T4 для отслеживаемых паттернов.
        T4 должна лежать на линии, параллельной 1-3, проходящей через T2.
        
        Args:
            ticker: Тикер инструмента
            timeframe: Таймфрейм
            df: DataFrame со свечами
            current_idx: Текущий индекс (последняя свеча)
            tolerance_percent: Допустимое отклонение цены T4 от параллельной линии (0.01 = 1%)
            
        Returns:
            dict: Паттерн с T4, если T4 сформировалась и лежит на параллельной линии, иначе None
        """
        # Ищем паттерны для этого тикера и таймфрейма
        for key, watched in list(self.watched_patterns.items()):
            if watched['ticker'] == ticker and watched['timeframe'] == timeframe:
                pattern = watched['pattern']
                
                # Проверяем, сформировалась ли T4
                # T4 должна быть на текущей свече или предыдущей
                t3 = pattern.get('t3', {})
                t3_idx = t3.get('idx', -1)
                
                # T4 должна быть после T3
                if current_idx > t3_idx:
                    # Проверяем, можем ли мы определить T4
                    # T4 должна быть на current_idx или current_idx - 1
                    if current_idx >= t3_idx + 1:
                        # Вычисляем ожидаемую цену T4 на основе параллельной линии через T2
                        expected_t4_price = self.calculate_t4_price_from_parallel_line(pattern, current_idx)
                        
                        # Получаем фактическую цену T4
                        t4_candle = df.iloc[current_idx]
                        actual_t4_price = float(t4_candle['close'])
                        t4_time = t4_candle.get('time', '') if 'time' in df.columns else ''
                        
                        # Проверяем, что фактическая цена T4 близка к ожидаемой (лежит на параллельной линии)
                        price_diff = abs(actual_t4_price - expected_t4_price)
                        price_diff_percent = price_diff / expected_t4_price if expected_t4_price != 0 else float('inf')
                        
                        if price_diff_percent <= tolerance_percent:
                            # T4 лежит на параллельной линии - паттерн сформирован
                            full_pattern = pattern.copy()
                            full_pattern['t4'] = {
                                'idx': current_idx,
                                'price': actual_t4_price,
                                'time': t4_time
                            }
                            
                            # Удаляем из отслеживаемых
                            del self.watched_patterns[key]
                            
                            return full_pattern
                        # Если цена T4 не соответствует параллельной линии, продолжаем отслеживание
        
        return None
    
    def check_lines_parallel_without_t4(self, pattern: dict, tolerance_percent: float = 0.01) -> Tuple[bool, str]:
        """
        Проверяет, что можно построить линию через T2, параллельную линии 1-3.
        Когда T4 еще нет, мы строим линию через T2, параллельную 1-3, и проверяем параллельность.
        
        Args:
            pattern: Паттерн с T0, T1, T2, T3 (без T4)
            tolerance_percent: Допустимое отклонение (0.01 = 1%)
            
        Returns:
            Tuple[bool, str]: (True если линии могут быть параллельны, описание)
        """
        t1 = pattern.get('t1', {})
        t2 = pattern.get('t2', {})
        t3 = pattern.get('t3', {})
        
        if not all([t1, t2, t3]):
            return False, "Недостаточно точек для проверки параллельности"
        
        # Линия 1-3: от T1 до T3
        t1_idx = t1['idx']
        t1_price = t1['price']
        t3_idx = t3['idx']
        t3_price = t3['price']
        
        # Вычисляем slope линии 1-3
        if t3_idx == t1_idx:
            slope_1_3 = 0
        else:
            slope_1_3 = (t3_price - t1_price) / (t3_idx - t1_idx)
        
        # Строим линию через T2, параллельную 1-3
        # Параллельная линия имеет тот же slope, но проходит через T2
        t2_idx = t2['idx']
        t2_price = t2['price']
        
        # Уравнение параллельной линии через T2: price = t2_price + slope_1_3 * (idx - t2_idx)
        # Проверяем, что T3 лежит близко к этой линии (для проверки, что линии действительно параллельны)
        # Но на самом деле, если slope одинаковый, линии параллельны по определению
        
        # Для проверки параллельности 1-3 и 2-4 (когда T4 еще нет):
        # Мы строим линию через T2 с тем же slope, что и 1-3
        # Это и есть линия 2-4 (когда T4 будет найдена, она должна лежать на этой линии)
        
        # Проверяем, что slope не слишком большой (чтобы избежать деления на ноль)
        if abs(slope_1_3) < 0.001:
            # Горизонтальная линия - всегда параллельна
            return True, "Линия 1-3 горизонтальна, линия через T2 также будет горизонтальна (параллельны)"
        
        # Линии параллельны, если slope одинаковый
        # Мы строим линию через T2 с тем же slope, что и 1-3 - они автоматически параллельны
        # Проверяем только, что это имеет смысл (T2 находится в правильном месте относительно T1 и T3)
        
        # Для бычьего паттерна: T2 должна быть между T1 и T3 по цене
        # Для медвежьего паттерна: T2 должна быть между T1 и T3 по цене
        is_bullish = 'BEARISH' not in pattern.get('pattern', 'FLAG')
        
        if is_bullish:
            # Для бычьего: T1 (верх) > T2 (низ) > T3 (верх канала)
            # T2 должна быть ниже T1 и T3
            if t2_price >= t1_price or t2_price >= t3_price:
                return False, f"T2 ({t2_price:.2f}) не в правильном положении для бычьего паттерна (T1={t1_price:.2f}, T3={t3_price:.2f})"
        else:
            # Для медвежьего: T1 (низ) < T2 (верх) < T3 (низ канала)
            # T2 должна быть выше T1 и T3
            if t2_price <= t1_price or t2_price <= t3_price:
                return False, f"T2 ({t2_price:.2f}) не в правильном положении для медвежьего паттерна (T1={t1_price:.2f}, T3={t3_price:.2f})"
        
        # Линии могут быть параллельны (мы построим линию через T2 с тем же slope, что и 1-3)
        return True, f"Линия 1-3 имеет slope={slope_1_3:.4f}, линия через T2 будет параллельна (slope={slope_1_3:.4f})"
    
    def calculate_t4_price_from_parallel_line(self, pattern: dict, t4_idx: int) -> float:
        """
        Вычисляет ожидаемую цену T4 на основе параллельной линии через T2
        
        Args:
            pattern: Паттерн с T0, T1, T2, T3 (без T4)
            t4_idx: Индекс, где должна быть T4
            
        Returns:
            float: Ожидаемая цена T4
        """
        t1 = pattern['t1']
        t2 = pattern['t2']
        t3 = pattern['t3']
        
        # Вычисляем slope линии 1-3
        t1_idx = t1['idx']
        t1_price = t1['price']
        t3_idx = t3['idx']
        t3_price = t3['price']
        
        if t3_idx == t1_idx:
            slope_1_3 = 0
        else:
            slope_1_3 = (t3_price - t1_price) / (t3_idx - t1_idx)
        
        # Строим линию через T2, параллельную 1-3
        # Уравнение: price = t2_price + slope_1_3 * (idx - t2_idx)
        t2_idx = t2['idx']
        t2_price = t2['price']
        
        expected_t4_price = t2_price + slope_1_3 * (t4_idx - t2_idx)
        
        return expected_t4_price
    
    def remove_old_patterns(self, max_age_minutes: int = 60):
        """
        Удаляет старые паттерны из отслеживания
        
        Args:
            max_age_minutes: Максимальный возраст паттерна в минутах
        """
        current_time = datetime.now()
        keys_to_remove = []
        
        for key, watched in self.watched_patterns.items():
            added_time = datetime.strptime(watched['added_time'], '%Y-%m-%d %H:%M:%S')
            age_minutes = (current_time - added_time).total_seconds() / 60
            
            if age_minutes > max_age_minutes:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.watched_patterns[key]
    
    def get_watched_patterns(self, ticker: Optional[str] = None, timeframe: Optional[str] = None) -> List[dict]:
        """
        Получает список отслеживаемых паттернов
        
        Args:
            ticker: Фильтр по тикеру (если None, все тикеры)
            timeframe: Фильтр по таймфрейму (если None, все таймфреймы)
            
        Returns:
            List[dict]: Список отслеживаемых паттернов
        """
        result = []
        for watched in self.watched_patterns.values():
            if ticker and watched['ticker'] != ticker:
                continue
            if timeframe and watched['timeframe'] != timeframe:
                continue
            result.append(watched)
        return result
