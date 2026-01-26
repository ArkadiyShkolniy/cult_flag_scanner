import pandas as pd
import numpy as np

class TradeStrategy:
    """
    Класс, отвечающий за логику принятия решений о входе в сделку.
    """

    def __init__(self):
        pass

    def calculate_line_price(self, start_idx, start_price, end_idx, end_price, current_idx):
        """
        Рассчитывает цену линии тренда в текущей точке (current_idx).
        """
        if end_idx == start_idx:
            return start_price
            
        slope = (end_price - start_price) / (end_idx - start_idx)
        return start_price + slope * (current_idx - start_idx)


    def check_entry_signal(self, df: pd.DataFrame, pattern: dict, entry_mode: str = "ema_squeeze", current_price: float = None):
        """
        Проверяет условия входа в позицию.
        Использует только EMA Squeeze - вход когда цена между EMA и линией 1-3.
        
        Args:
            df: DataFrame со свечами (должен содержать 'ema_7', 'ema_14', 'close', 'open')
            pattern: Словарь с координатами паттерна
            entry_mode: Режим входа (не используется, всегда ema_squeeze)
            current_price: Текущая цена (если None, берется close последней свечи)
            
        Returns:
            bool: True если есть сигнал на вход, иначе False
            str: Описание причины (для логов)
            str: Режим входа (всегда 'ema_squeeze')
        """
        # Проверка EMA Squeeze
        try:
            ema_signal, ema_desc = self.check_entry_signal_ema_squeeze(df, pattern)
        except Exception as e:
            ema_signal, ema_desc = False, f"Ошибка проверки: {e}"
        
        if ema_signal:
            return (True, f"✅ ВХОД РАЗРЕШЕН (EMA Squeeze: {ema_desc})", 'ema_squeeze')
        else:
            return (False, f"❌ Вход запрещен (EMA Squeeze: {ema_desc})", None)

    def check_entry_signal_ema_squeeze(self, df: pd.DataFrame, pattern: dict):
        """
        Проверяет условия входа "EMA Squeeze" (между EMA и линией тренда).
        
        Args:
            df: DataFrame со свечами (должен содержать 'ema_7', 'ema_14', 'close', 'open')
            pattern: Словарь с координатами паттерна
            
        Returns:
            bool: True если есть сигнал на вход, иначе False
            str: Описание причины (для логов)
        """
        # Получаем последнюю свечу
        current_candle = df.iloc[-1]
        current_idx = df.index[-1] # Или len(df)-1, зависит от индексации
        
        # 0. Проверка свежести паттерна
        if 't4' in pattern and 'idx' in pattern['t4']:
            t4_idx = int(pattern['t4']['idx'])
            # Используем len(df)-1 для сравнения
            current_pos = len(df) - 1
            bars_since_t4 = current_pos - t4_idx
            
            # Динамический расчет допустимой задержки
            pattern_len = 20  # Значение по умолчанию
            if 't0' in pattern and 'idx' in pattern['t0']:
                try:
                    t0_idx = int(pattern['t0']['idx'])
                    # Длина паттерна от начала до T4
                    pattern_len = max(5, t4_idx - t0_idx)
                except:
                    pass
            
            # Логика свежести:
            # Разрешаем задержку не более 20% от длины паттерна
            # Жесткие рамки: минимум 2 свечи, максимум 12 свечей
            # Для часового паттерна длиной 48 часов (2 дня) -> допустимо ~9 часов задержки
            # Для пятиминутного длиной 24 свечи (2 часа) -> допустимо ~4 свечи (20 минут)
            max_allowed_delay = min(12, max(2, int(pattern_len * 0.2)))
            
            if bars_since_t4 > max_allowed_delay:
                return False, f"Паттерн устарел (прошло {bars_since_t4} свечей, max: {max_allowed_delay} для длины {pattern_len})"
        
        # Индикаторы
        ema7 = current_candle['ema_7']
        ema14 = current_candle['ema_14']
        close_price = current_candle['close']
        open_price = current_candle['open']
        
        # Координаты точек паттерна
        t1 = pattern['t1']
        t3 = pattern['t3']
        t2 = pattern['t2']
        t4 = pattern['t4']
        
        # Определяем направление паттерна
        # Если в названии есть BEARISH - это шорт, иначе лонг
        is_bullish = 'BEARISH' not in pattern.get('pattern', 'FLAG')
        
        if is_bullish:
            # --- ЛОГИКА LONG ---
            
            # 1. Проверка тренда (EMA 7 выше EMA 14)
            if ema7 <= ema14:
                return False, "Нет тренда (EMA 7 <= EMA 14)"
                
            # 2. Проверка положения цены относительно EMA
            # Цена должна быть выше EMA 7 (сильный тренд) или хотя бы выше EMA 14
            # Строгий вариант: Close > EMA 7
            if close_price < ema7:
                return False, "Цена ниже EMA 7"
                
            # 3. Расчет линии сопротивления (T1-T3)
            # Нам нужно спроецировать линию на текущую свечу
            # ВАЖНО: индексы в df должны совпадать с индексами паттерна
            t1_idx = t1['idx']
            t3_idx = t3['idx']
            
            # Текущий индекс относительно начала df (если паттерн найден на истории)
            # Если мы торгуем в реальном времени, current_idx это последняя свеча
            # Предполагаем, что current_idx > t4_idx
            
            line_1_3_price = self.calculate_line_price(
                t1_idx, t1['price'], 
                t3_idx, t3['price'], 
                len(df) - 1 # Индекс последней свечи
            )
            
            # 4. Проверка: Цена ниже линии 1-3? (Мы входим ВНУТРИ треугольника)
            if close_price > line_1_3_price:
                return False, "Цена уже пробила линию 1-3 (поздно для Squeeze входа)"
                
            # 5. Триггер: Зеленая свеча (подтверждение отскока)
            if close_price <= open_price:
                return False, "Свеча не зеленая"
                
            return True, f"SIGNAL LONG: Price {close_price:.2f} зажата между EMA7 ({ema7:.2f}) и Линией 1-3 ({line_1_3_price:.2f})"

        else:
            # --- ЛОГИКА SHORT ---
            
            # 1. Проверка тренда (EMA 7 ниже EMA 14)
            if ema7 >= ema14:
                return False, "Нет тренда (EMA 7 >= EMA 14)"
                
            # 2. Проверка цены (Ниже EMA 7)
            if close_price > ema7:
                return False, "Цена выше EMA 7"
                
            # 3. Линия поддержки (T1-T3 для шорта это нижняя линия)
            t1_idx = t1['idx']
            t3_idx = t3['idx']
            
            line_1_3_price = self.calculate_line_price(
                t1_idx, t1['price'], 
                t3_idx, t3['price'], 
                len(df) - 1
            )
            
            # 4. Проверка: Цена выше линии 1-3? (Внутри флага)
            if close_price < line_1_3_price:
                return False, "Цена уже пробила линию 1-3 вниз"
                
            # 5. Триггер: Красная свеча
            if close_price >= open_price:
                return False, "Свеча не красная"
                
            return True, f"SIGNAL SHORT: Price {close_price:.2f} зажата между EMA7 ({ema7:.2f}) и Линией 1-3 ({line_1_3_price:.2f})"


    def calculate_exit_levels(self, df: pd.DataFrame, pattern: dict, entry_price: float, entry_mode: str = "ema_squeeze"):
        """
        Рассчитывает уровни Stop Loss и Take Profit.
        
        Args:
            df: DataFrame со свечами (нужен для EMA)
            pattern: Словарь паттерна (нужен для T0/T1)
            entry_price: Цена входа
            entry_mode: Режим входа (всегда "ema_squeeze")
            
        Returns:
            dict: {'stop_loss': float, 'take_profit': float}
        """
        # Направление сделки
        is_bullish = 'BEARISH' not in pattern.get('pattern', 'FLAG')
        
        # EMA14 текущей свечи для стопа (используется для ema_squeeze)
        current_ema14 = df.iloc[-1]['ema_14']
        
        # Координаты T4 для параллельного входа
        t4_price = pattern['t4']['price']
        
        if is_bullish:
            # --- LONG ---
            
            # Для EMA Squeeze стоп за EMA 14
            stop_loss = current_ema14 * 0.999
            desc_sl = f"SL: EMA14-0.1% ({stop_loss:.2f})"
            
            # Take Profit: Цель - T1 (вершина флагштока для Long)
            # В нотации пользователя T0 -> T1 это движение флагштока.
            # Для Long: T0 - минимум, T1 - максимум. Цель - вернуться к T1.
            take_profit = pattern['t1']['price']
            
            return {
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'desc': f"{desc_sl}, TP: T1 ({take_profit:.2f})"
            }
            
        else:
            # --- SHORT ---
            
            # Для EMA Squeeze стоп за EMA 14
            stop_loss = current_ema14 * 1.001
            desc_sl = f"SL: EMA14+0.1% ({stop_loss:.2f})"
            
            # Take Profit: Цель - T1 (дно флагштока)
            take_profit = pattern['t1']['price']
            
            return {
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'desc': f"{desc_sl}, TP: T1 ({take_profit:.2f})"
            }

