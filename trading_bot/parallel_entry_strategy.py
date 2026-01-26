"""
Стратегия входа в позицию на основе параллельности линий 1-3 и 2-4.
Вход происходит в момент формирования T4, когда линии параллельны.
"""

import pandas as pd
import numpy as np


class ParallelEntryStrategy:
    """
    Класс для проверки условий входа на основе параллельности линий 1-3 и 2-4.
    """
    
    def __init__(self, tolerance_percent: float = 0.01):
        """
        Args:
            tolerance_percent: Допустимое отклонение угла наклона в процентах (0.01 = 1%)
        """
        self.tolerance_percent = tolerance_percent
    
    def check_lines_parallel(self, pattern: dict):
        """
        Проверяет параллельность линий 1-3 и 2-4.
        
        Args:
            pattern: Словарь с координатами паттерна
            
        Returns:
            bool: True если линии параллельны, иначе False
            float: Угол наклона линии 1-3
            float: Угол наклона линии 2-4
            str: Описание результата
        """
        t1 = pattern['t1']
        t2 = pattern['t2']
        t3 = pattern['t3']
        t4 = pattern['t4']
        
        # Вычисляем углы наклона (slope) для обеих линий
        # Линия 1-3: от T1 до T3
        t1_idx = t1['idx']
        t1_price = t1['price']
        t3_idx = t3['idx']
        t3_price = t3['price']
        
        # Линия 2-4: от T2 до T4
        t2_idx = t2['idx']
        t2_price = t2['price']
        t4_idx = t4['idx']
        t4_price = t4['price']
        
        # Вычисляем slope (изменение цены на единицу индекса)
        if t3_idx == t1_idx:
            slope_1_3 = 0
        else:
            slope_1_3 = (t3_price - t1_price) / (t3_idx - t1_idx)
        
        if t4_idx == t2_idx:
            slope_2_4 = 0
        else:
            slope_2_4 = (t4_price - t2_price) / (t4_idx - t2_idx)
        
        # Проверяем параллельность: сравниваем абсолютные значения slopes
        # Если оба slope равны нулю или очень близки к нулю - считаем параллельными
        if abs(slope_1_3) < 0.001 and abs(slope_2_4) < 0.001:
            return True, slope_1_3, slope_2_4, "Линии горизонтальны (оба slope ≈ 0)"
        
        # Если один из slopes равен нулю, а другой нет - не параллельны
        if abs(slope_1_3) < 0.001 or abs(slope_2_4) < 0.001:
            return False, slope_1_3, slope_2_4, "Одна линия горизонтальна, другая нет"
        
        # Вычисляем относительное отклонение
        avg_slope = (abs(slope_1_3) + abs(slope_2_4)) / 2
        diff = abs(slope_1_3 - slope_2_4)
        relative_diff = diff / avg_slope if avg_slope != 0 else float('inf')
        
        # Проверяем, что отклонение в пределах допустимого
        is_parallel = relative_diff <= self.tolerance_percent
        
        if is_parallel:
            desc = f"Линии параллельны (отклонение {relative_diff*100:.2f}% <= {self.tolerance_percent*100:.0f}%)"
        else:
            desc = f"Линии не параллельны (отклонение {relative_diff*100:.2f}% > {self.tolerance_percent*100:.0f}%)"
        
        return is_parallel, slope_1_3, slope_2_4, desc
    
    def check_t4_formation(self, df: pd.DataFrame, pattern: dict, current_price: float = None):
        """
        Проверяет, что мы находимся в момент формирования T4.
        T4 должна быть точкой входа в позицию.
        Проверяем по текущей цене, а не по закрытию свечи.
        
        Args:
            df: DataFrame со свечами
            pattern: Словарь с координатами паттерна
            current_price: Текущая цена (если None, берется close последней свечи)
            
        Returns:
            bool: True если T4 формируется, иначе False
            str: Описание результата
            int: Индекс T4 в DataFrame (для использования как точка входа)
            float: Текущая цена для проверки условий входа
        """
        current_idx = len(df) - 1
        t4_idx = pattern['t4']['idx']
        
        # T4 должна быть сформирована (current_idx >= t4_idx)
        if current_idx < t4_idx:
            return False, f"T4 еще не сформирована: current_idx={current_idx}, t4_idx={t4_idx}", t4_idx, None
        
        # Вход строго в момент формирования T4 (допускаем погрешность ±1 свеча)
        # Это критично: мы должны войти именно когда T4 формируется, а не позже
        if abs(current_idx - t4_idx) > 1:
            return False, f"Не на T4: current_idx={current_idx}, t4_idx={t4_idx} (вход должен быть в момент формирования T4, разница {abs(current_idx - t4_idx)} свечей)", t4_idx, None
        
        # Получаем текущую цену
        if current_price is None:
            # Если свеча T4 еще формируется (current_idx == t4_idx), берем текущий close
            # Если свеча T4 уже закрылась (current_idx > t4_idx), берем close свечи T4
            if current_idx == t4_idx:
                # Свеча T4 еще формируется - используем текущий close как текущую цену
                current_price = df.iloc[t4_idx]['close']
            else:
                # Свеча T4 уже закрылась - используем close свечи T4
                current_price = df.iloc[t4_idx]['close']
        else:
            # Используем переданную текущую цену
            pass
        
        return True, f"T4 формируется: current_idx={current_idx}, t4_idx={t4_idx} (T4 - точка входа, проверка по текущей цене)", t4_idx, current_price
    
    def check_direction_condition(self, pattern: dict, is_bullish: bool):
        """
        Проверяет условие направления для входа.
        
        Args:
            pattern: Словарь с координатами паттерна
            is_bullish: True для LONG, False для SHORT
            
        Returns:
            bool: True если условие выполнено, иначе False
            str: Описание результата
        """
        t2 = pattern['t2']
        t4 = pattern['t4']
        
        if is_bullish:
            # Для LONG: T4 должна быть ниже или равна T2 (нижняя точка коррекции перед отскоком вверх)
            if t4['price'] > t2['price']:
                return False, f"T4 ({t4['price']:.2f}) выше T2 ({t2['price']:.2f}) для LONG"
            return True, f"T4 ({t4['price']:.2f}) <= T2 ({t2['price']:.2f}) - условие LONG выполнено"
        else:
            # Для SHORT: T4 должна быть выше или равна T2 (верхняя точка коррекции перед падением вниз)
            if t4['price'] < t2['price']:
                return False, f"T4 ({t4['price']:.2f}) ниже T2 ({t2['price']:.2f}) для SHORT"
            return True, f"T4 ({t4['price']:.2f}) >= T2 ({t2['price']:.2f}) - условие SHORT выполнено"
    
    def check_candle_confirmation(self, df: pd.DataFrame, is_bullish: bool):
        """
        Проверяет подтверждение свечи (зеленая для LONG, красная для SHORT).
        
        Args:
            df: DataFrame со свечами
            is_bullish: True для LONG, False для SHORT
            
        Returns:
            bool: True если свеча подтверждает направление, иначе False
            str: Описание результата
        """
        current_candle = df.iloc[-1]
        close_price = current_candle['close']
        open_price = current_candle['open']
        
        if is_bullish:
            # Для LONG нужна зеленая свеча
            if close_price <= open_price:
                return False, f"Свеча не зеленая: open={open_price:.2f}, close={close_price:.2f}"
            return True, f"Зеленая свеча: open={open_price:.2f}, close={close_price:.2f}"
        else:
            # Для SHORT нужна красная свеча
            if close_price >= open_price:
                return False, f"Свеча не красная: open={open_price:.2f}, close={close_price:.2f}"
            return True, f"Красная свеча: open={open_price:.2f}, close={close_price:.2f}"
    
    def check_entry_signal_long(self, df: pd.DataFrame, pattern: dict, current_price: float = None, debug: bool = False):
        """
        Проверяет условия входа LONG на основе параллельности линий 1-3 и 2-4.
        Вход происходит в момент формирования T4, если линии параллельны.
        Проверка по текущей цене, а не по закрытию свечи.
        
        УСЛОВИЯ ДЛЯ LONG:
        1. T4 формируется (current_idx >= t4_idx, погрешность ±1 свеча)
        2. Линии 1-3 и 2-4 параллельны (отклонение <= tolerance_percent)
        3. T4 <= T2 (нижняя точка коррекции перед отскоком вверх)
        4. Текущая цена выше open свечи T4 - подтверждение отскока вверх
        
        Args:
            df: DataFrame со свечами (должен содержать 'close', 'open')
            pattern: Словарь с координатами паттерна
            current_price: Текущая цена (если None, берется close последней свечи)
            debug: Если True, возвращает детальную информацию для отладки
            
        Returns:
            Если debug=False:
                bool: True если есть сигнал на вход, иначе False
                str: Описание причины (для логов)
            Если debug=True:
                dict: Детальная информация о проверках
        """
        debug_info = {
            'direction': 'LONG',
            't4_formation': None,
            'parallel_lines': None,
            'direction_condition': None,
            'candle_confirmation': None,
            'all_checks': []
        }
        
        # 1. Проверка формирования T4 (T4 - точка входа, проверка по текущей цене)
        t4_ok, t4_desc, t4_idx, actual_current_price = self.check_t4_formation(df, pattern, current_price)
        debug_info['t4_formation'] = {'ok': t4_ok, 'desc': t4_desc, 't4_idx': t4_idx, 'current_price': actual_current_price}
        debug_info['all_checks'].append(('1. T4 формируется (точка входа, проверка по текущей цене)', t4_ok, t4_desc))
        
        if not t4_ok:
            if debug:
                return debug_info
            return False, t4_desc
        
        # Используем актуальную текущую цену
        if actual_current_price is None:
            if debug:
                return debug_info
            return False, "Не удалось определить текущую цену"
        
        # 2. Проверка параллельности линий
        is_parallel, slope_1_3, slope_2_4, parallel_desc = self.check_lines_parallel(pattern)
        debug_info['parallel_lines'] = {
            'ok': is_parallel,
            'slope_1_3': slope_1_3,
            'slope_2_4': slope_2_4,
            'desc': parallel_desc
        }
        debug_info['all_checks'].append(('2. Параллельность линий 1-3 и 2-4', is_parallel, parallel_desc))
        
        if not is_parallel:
            if debug:
                return debug_info
            return False, parallel_desc
        
        # 3. Проверка условия направления для LONG: T4 должна быть ниже или равна T2
        t2 = pattern['t2']
        t4 = pattern['t4']
        if t4['price'] > t2['price']:
            direction_desc = f"T4 ({t4['price']:.2f}) выше T2 ({t2['price']:.2f}) - условие LONG не выполнено"
            debug_info['direction_condition'] = {'ok': False, 'desc': direction_desc}
            debug_info['all_checks'].append(('3. T4 <= T2 (LONG)', False, direction_desc))
            if debug:
                return debug_info
            return False, direction_desc
        
        direction_desc = f"T4 ({t4['price']:.2f}) <= T2 ({t2['price']:.2f}) - условие LONG выполнено"
        debug_info['direction_condition'] = {'ok': True, 'desc': direction_desc}
        debug_info['all_checks'].append(('3. T4 ниже T2 (LONG)', True, direction_desc))
        
        # 4. Проверка подтверждения для LONG: текущая цена выше open свечи T4
        # Проверяем по текущей цене, а не по закрытию свечи
        t4_candle = df.iloc[t4_idx]
        t4_open_price = t4_candle['open']
        
        if actual_current_price <= t4_open_price:
            candle_desc = f"Текущая цена ({actual_current_price:.2f}) не выше open T4 ({t4_open_price:.2f}) - условие LONG не выполнено"
            debug_info['candle_confirmation'] = {'ok': False, 'desc': candle_desc, 'current_price': actual_current_price, 't4_open': t4_open_price}
            debug_info['all_checks'].append(('4. Текущая цена выше open T4 (LONG)', False, candle_desc))
            if debug:
                return debug_info
            return False, candle_desc
        
        candle_desc = f"Текущая цена ({actual_current_price:.2f}) выше open T4 ({t4_open_price:.2f}) - условие LONG выполнено"
        debug_info['candle_confirmation'] = {'ok': True, 'desc': candle_desc, 'current_price': actual_current_price, 't4_open': t4_open_price}
        debug_info['all_checks'].append(('4. Текущая цена выше open T4 (LONG)', True, candle_desc))
        debug_info['entry_price'] = actual_current_price  # Цена входа = текущая цена
        
        # Все проверки пройдены
        success_msg = (
            f"SIGNAL LONG (Parallel Lines): "
            f"Линии 1-3 и 2-4 параллельны (slope={slope_1_3:.4f}), "
            f"T4 ({t4['price']:.2f}) <= T2 ({t2['price']:.2f}), "
            f"текущая цена ({actual_current_price:.2f}) выше open T4 ({t4_open_price:.2f}), ВХОД на {actual_current_price:.2f}"
        )
        
        debug_info['success'] = True
        debug_info['message'] = success_msg
        
        if debug:
            return debug_info
        
        return True, success_msg
    
    def check_entry_signal_short(self, df: pd.DataFrame, pattern: dict, current_price: float = None, debug: bool = False):
        """
        Проверяет условия входа SHORT на основе параллельности линий 1-3 и 2-4.
        Вход происходит в момент формирования T4, если линии параллельны.
        Проверка по текущей цене, а не по закрытию свечи.
        
        УСЛОВИЯ ДЛЯ SHORT:
        1. T4 формируется (current_idx >= t4_idx, погрешность ±1 свеча)
        2. Линии 1-3 и 2-4 параллельны (отклонение <= tolerance_percent)
        3. T4 >= T2 (верхняя точка коррекции перед падением вниз)
        4. Текущая цена ниже open свечи T4 - подтверждение падения вниз
        
        Args:
            df: DataFrame со свечами (должен содержать 'close', 'open')
            pattern: Словарь с координатами паттерна
            current_price: Текущая цена (если None, берется close последней свечи)
            debug: Если True, возвращает детальную информацию для отладки
            
        Returns:
            Если debug=False:
                bool: True если есть сигнал на вход, иначе False
                str: Описание причины (для логов)
            Если debug=True:
                dict: Детальная информация о проверках
        """
        debug_info = {
            'direction': 'SHORT',
            't4_formation': None,
            'parallel_lines': None,
            'direction_condition': None,
            'candle_confirmation': None,
            'all_checks': []
        }
        
        # 1. Проверка формирования T4 (T4 - точка входа, проверка по текущей цене)
        t4_ok, t4_desc, t4_idx, actual_current_price = self.check_t4_formation(df, pattern, current_price)
        debug_info['t4_formation'] = {'ok': t4_ok, 'desc': t4_desc, 't4_idx': t4_idx, 'current_price': actual_current_price}
        debug_info['all_checks'].append(('1. T4 формируется (точка входа, проверка по текущей цене)', t4_ok, t4_desc))
        
        if not t4_ok:
            if debug:
                return debug_info
            return False, t4_desc
        
        # Используем актуальную текущую цену
        if actual_current_price is None:
            if debug:
                return debug_info
            return False, "Не удалось определить текущую цену"
        
        # 2. Проверка параллельности линий
        is_parallel, slope_1_3, slope_2_4, parallel_desc = self.check_lines_parallel(pattern)
        debug_info['parallel_lines'] = {
            'ok': is_parallel,
            'slope_1_3': slope_1_3,
            'slope_2_4': slope_2_4,
            'desc': parallel_desc
        }
        debug_info['all_checks'].append(('2. Параллельность линий 1-3 и 2-4', is_parallel, parallel_desc))
        
        if not is_parallel:
            if debug:
                return debug_info
            return False, parallel_desc
        
        # 3. Проверка условия направления для SHORT: T4 должна быть выше или равна T2
        t2 = pattern['t2']
        t4 = pattern['t4']
        if t4['price'] < t2['price']:
            direction_desc = f"T4 ({t4['price']:.2f}) ниже T2 ({t2['price']:.2f}) - условие SHORT не выполнено"
            debug_info['direction_condition'] = {'ok': False, 'desc': direction_desc}
            debug_info['all_checks'].append(('3. T4 >= T2 (SHORT)', False, direction_desc))
            if debug:
                return debug_info
            return False, direction_desc
        
        direction_desc = f"T4 ({t4['price']:.2f}) >= T2 ({t2['price']:.2f}) - условие SHORT выполнено"
        debug_info['direction_condition'] = {'ok': True, 'desc': direction_desc}
        debug_info['all_checks'].append(('3. T4 выше T2 (SHORT)', True, direction_desc))
        
        # 4. Проверка подтверждения для SHORT: текущая цена ниже open свечи T4
        # Проверяем по текущей цене, а не по закрытию свечи
        t4_candle = df.iloc[t4_idx]
        t4_open_price = t4_candle['open']
        
        if actual_current_price >= t4_open_price:
            candle_desc = f"Текущая цена ({actual_current_price:.2f}) не ниже open T4 ({t4_open_price:.2f}) - условие SHORT не выполнено"
            debug_info['candle_confirmation'] = {'ok': False, 'desc': candle_desc, 'current_price': actual_current_price, 't4_open': t4_open_price}
            debug_info['all_checks'].append(('4. Текущая цена ниже open T4 (SHORT)', False, candle_desc))
            if debug:
                return debug_info
            return False, candle_desc
        
        candle_desc = f"Текущая цена ({actual_current_price:.2f}) ниже open T4 ({t4_open_price:.2f}) - условие SHORT выполнено"
        debug_info['candle_confirmation'] = {'ok': True, 'desc': candle_desc, 'current_price': actual_current_price, 't4_open': t4_open_price}
        debug_info['all_checks'].append(('4. Текущая цена ниже open T4 (SHORT)', True, candle_desc))
        debug_info['entry_price'] = actual_current_price  # Цена входа = текущая цена
        
        # Все проверки пройдены
        success_msg = (
            f"SIGNAL SHORT (Parallel Lines): "
            f"Линии 1-3 и 2-4 параллельны (slope={slope_1_3:.4f}), "
            f"T4 ({t4['price']:.2f}) >= T2 ({t2['price']:.2f}), "
            f"текущая цена ({actual_current_price:.2f}) ниже open T4 ({t4_open_price:.2f}), ВХОД на {actual_current_price:.2f}"
        )
        
        debug_info['success'] = True
        debug_info['message'] = success_msg
        
        if debug:
            return debug_info
        
        return True, success_msg
    
    def check_entry_signal(self, df: pd.DataFrame, pattern: dict, current_price: float = None, debug: bool = False):
        """
        Проверяет условия входа на основе параллельности линий 1-3 и 2-4.
        Вход происходит в момент формирования T4, если линии параллельны.
        Автоматически определяет направление (LONG или SHORT) и вызывает соответствующий метод.
        
        Args:
            df: DataFrame со свечами (должен содержать 'close', 'open')
            pattern: Словарь с координатами паттерна
            current_price: Текущая цена (если None, берется close последней свечи)
            debug: Если True, возвращает детальную информацию для отладки
            
        Returns:
            Если debug=False:
                bool: True если есть сигнал на вход, иначе False
                str: Описание причины (для логов)
            Если debug=True:
                dict: Детальная информация о проверках
        """
        # Определяем направление паттерна
        is_bullish = 'BEARISH' not in pattern.get('pattern', 'FLAG')
        
        if is_bullish:
            return self.check_entry_signal_long(df, pattern, current_price, debug)
        else:
            return self.check_entry_signal_short(df, pattern, current_price, debug)


# Функция для удобного использования
def check_parallel_entry(df: pd.DataFrame, pattern: dict, current_price: float = None, tolerance_percent: float = 0.01, debug: bool = False):
    """
    Удобная функция для проверки входа по параллельности.
    Проверка по текущей цене, а не по закрытию свечи.
    
    Args:
        df: DataFrame со свечами
        pattern: Словарь с координатами паттерна
        current_price: Текущая цена (если None, берется close последней свечи)
        tolerance_percent: Допустимое отклонение угла наклона (0.01 = 1%)
        debug: Если True, возвращает детальную информацию для отладки
        
    Returns:
        Если debug=False:
            bool: True если есть сигнал на вход, иначе False
            str: Описание причины
        Если debug=True:
            dict: Детальная информация о проверках
    """
    strategy = ParallelEntryStrategy(tolerance_percent=tolerance_percent)
    return strategy.check_entry_signal(df, pattern, current_price, debug=debug)


if __name__ == "__main__":
    # Пример использования для отладки
    print("=" * 70)
    print("🧪 ТЕСТ СТРАТЕГИИ ВХОДА ПО ПАРАЛЛЕЛЬНОСТИ")
    print("=" * 70)
    print()
    print("Использование:")
    print("  from trading_bot.parallel_entry_strategy import check_parallel_entry")
    print("  signal, desc = check_parallel_entry(df, pattern)")
    print()
    print("Для отладки:")
    print("  debug_info = check_parallel_entry(df, pattern, debug=True)")
    print()
