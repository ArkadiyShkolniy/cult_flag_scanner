import os
import pandas as pd
import numpy as np
from datetime import timedelta
from t_tech.invest import Client, CandleInterval, InstrumentIdType, InstrumentStatus
from t_tech.invest.utils import now, quotation_to_decimal
from dotenv import load_dotenv

load_dotenv()

class BullishFlagScanner:
    """
    Сканер для поиска паттерна Бычий Флаг (лонг) со структурой 0-1-2-3-4:
    
    - T0: Начало (Low перед флагштоком)
    - T1: Вершина флагштока (High)
    - T2: Первый откат (Low)
    - T3: Второй пик (High, <= T1)
    - T4: Второй откат (Low, >= T0)
    - Пробой: Цена закрытия пробивает линию тренда T1-T3 вверх
    """
    
    def __init__(self, token: str):
        self.token = token
    
    def get_all_shares(self):
        """Получает список всех доступных акций Мосбиржи (TQBR)"""
        with Client(self.token) as client:
            response = client.instruments.shares(instrument_status=InstrumentStatus.INSTRUMENT_STATUS_BASE)
            shares = [
                s for s in response.instruments 
                if s.class_code == 'TQBR' and s.api_trade_available_flag and s.buy_available_flag
            ]
            return shares
        
    def get_candles_df(self, ticker: str, class_code: str, days_back: int = 5, interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_HOUR) -> pd.DataFrame:
        """Загружает свечи по Тикеру с указанным интервалом"""
        try:
            with Client(self.token) as client:
                item = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                    class_code=class_code,
                    id=ticker
                ).instrument
                
                candles = client.get_all_candles(
                    instrument_id=item.uid,
                    from_=now() - timedelta(days=days_back),
                    to=now(),
                    interval=interval,
                )
                
                data = []
                for c in candles:
                    data.append({
                        'time': c.time,
                        'open': float(quotation_to_decimal(c.open)),
                        'high': float(quotation_to_decimal(c.high)),
                        'low': float(quotation_to_decimal(c.low)),
                        'close': float(quotation_to_decimal(c.close)),
                        'volume': c.volume
                    })
                    
            if not data:
                return pd.DataFrame()
                
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'])
            # Конвертируем время в московский часовой пояс
            if df['time'].dt.tz is None:
                df['time'] = df['time'].dt.tz_localize('UTC')
            df['time'] = df['time'].dt.tz_convert('Europe/Moscow').dt.tz_localize(None)
            return df
            
        except Exception as e:
            return pd.DataFrame()
    
    def get_candles_df_by_dates(self, ticker: str, class_code: str, from_date, to_date, interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_HOUR) -> pd.DataFrame:
        """Загружает свечи по Тикеру за указанный период с указанным интервалом"""
        try:
            with Client(self.token) as client:
                item = client.instruments.get_instrument_by(
                    id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                    class_code=class_code,
                    id=ticker
                ).instrument
                
                candles = client.get_all_candles(
                    instrument_id=item.uid,
                    from_=from_date,
                    to=to_date,
                    interval=interval,
                )
                
                data = []
                for c in candles:
                    data.append({
                        'time': c.time,
                        'open': float(quotation_to_decimal(c.open)),
                        'high': float(quotation_to_decimal(c.high)),
                        'low': float(quotation_to_decimal(c.low)),
                        'close': float(quotation_to_decimal(c.close)),
                        'volume': c.volume
                    })
                    
            if not data:
                return pd.DataFrame()
                
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'])
            # Конвертируем время в московский часовой пояс
            if df['time'].dt.tz is None:
                df['time'] = df['time'].dt.tz_localize('UTC')
            df['time'] = df['time'].dt.tz_convert('Europe/Moscow').dt.tz_localize(None)
            return df
            
        except Exception as e:
            return pd.DataFrame()

    def get_candles_by_uid(self, uid: str, days_back: int = 5, interval: CandleInterval = CandleInterval.CANDLE_INTERVAL_HOUR) -> pd.DataFrame:
        """Оптимизированный метод загрузки по UID с указанным интервалом"""
        try:
            with Client(self.token) as client:
                candles = client.get_all_candles(
                    instrument_id=uid,
                    from_=now() - timedelta(days=days_back),
                    to=now(),
                    interval=interval,
                )
                data = []
                for c in candles:
                    data.append({
                        'time': c.time,
                        'open': float(quotation_to_decimal(c.open)),
                        'high': float(quotation_to_decimal(c.high)),
                        'low': float(quotation_to_decimal(c.low)),
                        'close': float(quotation_to_decimal(c.close)),
                        'volume': c.volume
                    })
            if not data: return pd.DataFrame()
            df = pd.DataFrame(data)
            df['time'] = pd.to_datetime(df['time'])
            # Конвертируем время в московский часовой пояс
            if df['time'].dt.tz is None:
                df['time'] = df['time'].dt.tz_localize('UTC')
            df['time'] = df['time'].dt.tz_convert('Europe/Moscow').dt.tz_localize(None)
            return df
        except:
            return pd.DataFrame()

    def _find_local_extrema(self, df, window=3):
        """
        Находит локальные максимумы (highs) и минимумы (lows)
        window - количество соседних свечей для сравнения
        """
        highs_idx = []
        lows_idx = []
        
        for i in range(window, len(df) - window):
            # Максимум: high[i] больше всех соседей в окне
            window_highs = df.iloc[i-window:i+window+1]['high']
            if df.iloc[i]['high'] == window_highs.max():
                highs_idx.append(i)
            
            # Минимум: low[i] меньше всех соседей в окне
            window_lows = df.iloc[i-window:i+window+1]['low']
            if df.iloc[i]['low'] == window_lows.min():
                lows_idx.append(i)
        
        return np.array(highs_idx), np.array(lows_idx)

    def analyze(self, df: pd.DataFrame, debug=False, timeframe='1h'):
        """
        Основной метод анализа - ищет бычий флаг
        Возвращает список найденных паттернов
        """
        if len(df) < 50:
            return []
        
        return self.analyze_flag_0_1_2_3_4(df, debug=debug, timeframe=timeframe)

    def analyze_flag_0_1_2_3_4(self, df: pd.DataFrame, debug=False, timeframe='1h'):
        """
        Ищет паттерн Бычий Флаг со структурой 0-1-2-3-4
        
        Возвращает:
        - [] если паттерн не найден
        - [dict] с информацией о паттерне, если найден
        
        Args:
            debug: Если True, выводит детальную отладочную информацию
            timeframe: Строковое обозначение таймфрейма ('1h', '5m', '1d')
        """
        if len(df) < 50:
            if debug:
                print(f"❌ Недостаточно данных: {len(df)} < 50")
            return []
        
        try:
            if debug:
                print("=" * 60)
                print("НАЧАЛО АНАЛИЗА БЫЧЬЕГО ПАТТЕРНА 0-1-2-3-4")
                print("=" * 60)
            # Находим локальные экстремумы
            highs_idx, lows_idx = self._find_local_extrema(df, window=3)
            
            if debug:
                print(f"\nНайдено максимумов: {len(highs_idx)}, минимумов: {len(lows_idx)}")
                print(f"Максимумы (последние 10): {highs_idx[-10:]}")
                print(f"Минимумы (последние 10): {lows_idx[-10:]}")
            
            if len(highs_idx) < 2 or len(lows_idx) < 2:
                if debug:
                    print(f"❌ Недостаточно экстремумов: highs={len(highs_idx)}, lows={len(lows_idx)}")
                return []
            
            # Ищем структуру: T1 (high) -> T2 (low) -> T3 (high) -> T4 (low)
            # T1 - вершина флагштока (самый высокий максимум в недавнем диапазоне)
            # T3 - второй пик внутри флага (максимум после T1, но ниже T1)
            
            # Исключаем последний максимум при поиске T1 и T3 (он может быть пробоем)
            if len(highs_idx) < 3:
                if debug:
                    print(f"❌ Недостаточно максимумов для анализа: {len(highs_idx)} < 3")
                return []
            
            # Ищем T1 как самый высокий максимум среди последних (исключая последний, который может быть пробоем)
            search_highs = highs_idx[:-1]  # Исключаем последний максимум (может быть пробоем)
            if len(search_highs) < 2:
                if debug:
                    print(f"❌ Недостаточно максимумов после исключения последнего: {len(search_highs)} < 2")
                return []
            
            if debug:
                print(f"\n--- ПОИСК T1 (вершина флагштока) ---")
                print(f"Исключен последний максимум (индекс {highs_idx[-1]}) как возможный пробой")
            
            # T1 - самый высокий максимум среди кандидатов (вершина флагштока)
            t1_idx = None
            t1_price = 0
            for h_idx in search_highs:
                h_price = df.iloc[h_idx]['high']
                if h_price > t1_price:
                    t1_price = h_price
                    t1_idx = h_idx
            
            if t1_idx is None:
                if debug:
                    print(f"❌ T1 не найден")
                return []
            
            if debug:
                print(f"✅ T1 найден: индекс {t1_idx}, цена {t1_price:.2f}, время {df.iloc[t1_idx]['time']}")
            
            # T3 - максимум после T1, но ниже T1 (второй пик внутри флага)
            # Исключаем последние 3-4 свечи (они могут быть пробоем)
            search_end_idx = len(df) - 4  # Исключаем последние 4 свечи
            t3_idx = None
            t3_price = 0
            
            if debug:
                print(f"\n--- ПОИСК T3 (второй пик внутри флага) ---")
                print(f"Исключаем свечи после индекса {search_end_idx} (последние 4 свечи)")
                print(f"Ищем максимум после T1 (idx {t1_idx}), не превышающий T1 более чем на 5%")
            
            # Сначала пробуем найти среди экстремумов (ищем последний подходящий, не максимальный)
            for h_idx in reversed(search_highs):  # Идем с конца
                if t1_idx < h_idx <= search_end_idx:
                    h_price = df.iloc[h_idx]['high']
                    if debug:
                        print(f"  Проверяем экстремум idx {h_idx}: high={h_price:.2f}, условие: {h_price:.2f} <= {t1_price * 1.05:.2f}")
                    if h_price <= t1_price * 1.05:  # T3 не должен значительно превышать T1
                        t3_price = h_price
                        t3_idx = h_idx
                        if debug:
                            print(f"  ✅ Найден T3 среди экстремумов: idx {t3_idx}, цена {t3_price:.2f}")
                        break  # Берем последний подходящий, а не максимальный
            
            # Если не нашли среди экстремумов, ищем среди всех свечей (также с конца)
            if t3_idx is None:
                if debug:
                    print(f"  Не найдено среди экстремумов, ищем среди всех свечей...")
                for idx in range(search_end_idx, t1_idx, -1):  # Идем с конца к началу
                    h_price = df.iloc[idx]['high']
                    if h_price <= t1_price * 1.05:
                        # Проверяем, что это локальный максимум (больше соседних)
                        if idx > 0 and idx < len(df) - 1:
                            if h_price >= df.iloc[idx-1]['high'] and h_price >= df.iloc[idx+1]['high']:
                                t3_price = h_price
                                t3_idx = idx
                                if debug:
                                    print(f"  ✅ Найден T3 среди свечей: idx {t3_idx}, цена {t3_price:.2f}")
                                break
            
            if t3_idx is None:
                if debug:
                    print(f"❌ T3 не найден")
                return []
            
            if debug:
                print(f"✅ T3 найден: индекс {t3_idx}, цена {t3_price:.2f}, время {df.iloc[t3_idx]['time']}")
            
            # T4 - последний минимум перед пробоем (но не на том же индексе, что и T3)
            t4_idx = None
            for l_idx in reversed(lows_idx):
                if l_idx != t3_idx:  # T4 не должен совпадать с T3
                    t4_idx = l_idx
                    break
            
            if t4_idx is None:
                if debug:
                    print(f"❌ T4 не найден (нет минимумов или все совпадают с T3)")
                return []
            
            if debug:
                print(f"\n--- ПОИСК T2 ---")
                print(f"T4 (последний минимум, не совпадающий с T3): индекс {t4_idx}, цена {df.iloc[t4_idx]['low']:.2f}, время {df.iloc[t4_idx]['time']}")
            
            # Ищем T2 - минимум между T1 и T4
            t2_idx = None
            for l in lows_idx:
                if t1_idx < l < t4_idx:  # T2 между T1 и T4
                    if t2_idx is None or l > t2_idx:  # Берем последний подходящий минимум
                        t2_idx = l
            
            if t2_idx is None:
                if debug:
                    print(f"❌ T2 не найден (нет минимума между T1={t1_idx} и T4={t4_idx})")
                return []
            
            if debug:
                print(f"✅ T2 найден: индекс {t2_idx}, цена {df.iloc[t2_idx]['low']:.2f}, время {df.iloc[t2_idx]['time']}")
            
            # Ищем T3 между T2 и T4 (T3 должна быть между ними, а не после T4)
            if t3_idx is None or t3_idx < t2_idx or t3_idx >= t4_idx:
                if debug:
                    if t3_idx is not None:
                        print(f"⚠️ T3 (idx {t3_idx}) не находится между T2 ({t2_idx}) и T4 ({t4_idx}), ищем заново...")
                    else:
                        print(f"⚠️ Ищем T3 между T2 ({t2_idx}) и T4 ({t4_idx})...")
                
                # Ищем T3 между T2 и T4
                t3_idx_new = None
                t3_price_new = 0
                for idx in range(t2_idx + 1, t4_idx):  # T3 должна быть между T2 и T4
                    h_price = df.iloc[idx]['high']
                    if h_price <= t1_price * 1.05:
                        # Проверяем, что это локальный максимум (>= соседних)
                        is_local_max = True
                        if idx > 0:
                            if h_price < df.iloc[idx-1]['high']:
                                is_local_max = False
                        if idx < len(df) - 1:
                            if h_price < df.iloc[idx+1]['high']:
                                is_local_max = False
                        
                        if is_local_max and h_price > t3_price_new:
                            # Берем локальный максимум с максимальным high
                            t3_price_new = h_price
                            t3_idx_new = idx
                
                if t3_idx_new is not None:
                    t3_idx = t3_idx_new
                    t3_price = t3_price_new
                    if debug:
                        print(f"✅ T3 найдена: idx {t3_idx}, цена {t3_price:.2f}, время {df.iloc[t3_idx]['time']}")
                else:
                    if debug:
                        print(f"❌ Не удалось найти T3 между T2 ({t2_idx}) и T4 ({t4_idx})")
                    return []
            
            # Проверяем логическую хронологию: T0 < T1 < T2 < T3 < T4
            if not (t1_idx < t2_idx < t3_idx < t4_idx):
                if debug:
                    print(f"❌ Нарушена хронология: T1 ({t1_idx}) >= T2 ({t2_idx})")
                return []
            
            if debug:
                print(f"\n✅ Хронология правильная: T1 ({t1_idx}) < T2 ({t2_idx})")
            
            # Получаем цены
            t1 = df.iloc[t1_idx]['high']  # Вершина флагштока
            t2 = df.iloc[t2_idx]['low']   # Первый откат
            t3 = df.iloc[t3_idx]['high']  # Второй пик (внутри флага)
            t4 = df.iloc[t4_idx]['low']   # Второй откат
            
            # Находим T0 (начало флагштока) - минимум перед T1
            t0_candidates = lows_idx[lows_idx < t1_idx]
            if len(t0_candidates) == 0:
                if debug:
                    print(f"❌ T0 не найден (нет минимума перед T1={t1_idx})")
                return []
            t0_idx = t0_candidates[-1]
            t0 = df.iloc[t0_idx]['low']
            
            if debug:
                print(f"\n✅ T0 найден: индекс {t0_idx}, цена {t0:.2f}, время {df.iloc[t0_idx]['time']}")
                print(f"\nВсе точки найдены:")
                print(f"  T0: {t0:.2f} (idx {t0_idx})")
                print(f"  T1: {t1:.2f} (idx {t1_idx})")
                print(f"  T2: {t2:.2f} (idx {t2_idx})")
                print(f"  T3: {t3:.2f} (idx {t3_idx})")
                print(f"  T4: {t4:.2f} (idx {t4_idx})")
            
            # --- ГЕОМЕТРИЧЕСКИЕ УСЛОВИЯ ---
            
            if debug:
                print(f"\n{'='*60}")
                print("ПРОВЕРКА ГЕОМЕТРИЧЕСКИХ УСЛОВИЙ")
                print(f"{'='*60}")
            
            # 1. Флагшток (0-1): Должен быть значительный рост
            pole_height = t1 - t0
            if debug:
                print(f"\n1. Флагшток (T1-T0): {pole_height:.2f}")
            if pole_height <= 0:
                if debug:
                    print(f"   ❌ Высота флагштока <= 0")
                return []
            
            # Минимальная высота флагштока (можно настроить)
            avg_range = df['high'].subtract(df['low']).mean()
            min_pole_height = avg_range * 1.5
            if debug:
                print(f"   Средний диапазон: {avg_range:.2f}")
                print(f"   Требование: pole_height >= {min_pole_height:.2f}")
            if pole_height < min_pole_height:
                if debug:
                    print(f"   ❌ Флагшток слишком мал: {pole_height:.2f} < {min_pole_height:.2f}")
                return []
            if debug:
                print(f"   ✅ Флагшток достаточной высоты")
            
            # 2. T3 (Peak 2): Максимум не должен значительно превышать предыдущий
            # Разрешаем небольшое превышение (до 5%) для учета волатильности
            max_t3 = t1 * 1.05
            if debug:
                print(f"\n2. T3 <= T1 * 1.05: {t3:.2f} <= {max_t3:.2f}")
            if t3 > max_t3:
                if debug:
                    print(f"   ❌ T3 слишком высокий: {t3:.2f} > {max_t3:.2f}")
                return []
            if debug:
                print(f"   ✅ T3 в допустимых пределах")
            
            # 3. Глубина коррекции T2: Не должна быть слишком глубокой (не ниже 40% флагштока)
            min_t2 = t0 + 0.4 * pole_height
            if debug:
                print(f"\n3. T2 >= {min_t2:.2f} (не ниже 40% флагштока): T2 = {t2:.2f}")
            if t2 < min_t2:
                if debug:
                    print(f"   ❌ T2 слишком низкий: {t2:.2f} < {min_t2:.2f}")
                return []
            if debug:
                print(f"   ✅ T2 коррекция допустима")
            
            # 4. ВАЖНО: T4 (второй откат) не должен опускаться более чем на 50% от флагштока
            min_t4 = t0 + 0.5 * pole_height
            if debug:
                print(f"\n4. T4 >= {min_t4:.2f} (не ниже 50% флагштока): T4 = {t4:.2f}")
            if t4 < min_t4:
                if debug:
                    print(f"   ❌ T4 слишком низкий: {t4:.2f} < {min_t4:.2f}")
                return []
            if debug:
                print(f"   ✅ T4 коррекция допустима")
            
            # 5. Проверка направления линий тренда (T1-T3 и T2-T4 не должны расходиться)
            if (t3_idx - t1_idx) == 0 or (t4_idx - t2_idx) == 0:
                if debug:
                    print(f"\n5. Проверка направления линий: пропущена (деление на ноль)")
            else:
                slope_resistance = (t3 - t1) / (t3_idx - t1_idx)  # Наклон линии сопротивления T1-T3
                slope_support = (t4 - t2) / (t4_idx - t2_idx)      # Наклон линии поддержки T2-T4
                
                if debug:
                    print(f"\n5. Проверка направления линий тренда:")
                    print(f"   Наклон сопротивления (T1-T3): {slope_resistance:.4f}")
                    print(f"   Наклон поддержки (T2-T4): {slope_support:.4f}")
                    print(f"   Условие: slope_support >= slope_resistance (линии параллельны или сходятся)")
                
                # Для бычьего флага обе линии обычно идут вниз или горизонтально
                # Линии не должны расходиться: slope_support >= slope_resistance
                if slope_support < slope_resistance:
                    if debug:
                        print(f"   ❌ Линии расходятся: slope_support ({slope_support:.4f}) < slope_resistance ({slope_resistance:.4f})")
                    return []
                if debug:
                    print(f"   ✅ Линии параллельны или сходятся (не расходятся)")
            
            # 6. Проверка, что линии не пересекают тела свечей и их тени
            if debug:
                print(f"\n6. Проверка пересечения линий со свечами:")
            
            # Линия T1-T3 (сопротивление) должна проходить ВЫШЕ всех свечей между T1 и T3
            slope_resistance = (t3 - t1) / (t3_idx - t1_idx)
            line_crosses_resistance = False
            for idx in range(t1_idx + 1, t3_idx):
                line_price = t1 + slope_resistance * (idx - t1_idx)
                candle_high = df.iloc[idx]['high']
                if line_price <= candle_high:
                    line_crosses_resistance = True
                    if debug:
                        print(f"   ❌ Линия T1-T3 пересекает свечу {idx}: линия={line_price:.2f}, high={candle_high:.2f}")
                    break
            
            if line_crosses_resistance:
                if debug:
                    print(f"   ❌ Линия сопротивления T1-T3 пересекает свечи")
                return []
            
            # Линия T2-T4 (поддержка) должна проходить НИЖЕ всех свечей между T2 и T4
            slope_support = (t4 - t2) / (t4_idx - t2_idx)
            line_crosses_support = False
            for idx in range(t2_idx + 1, t4_idx):
                line_price = t2 + slope_support * (idx - t2_idx)
                candle_low = df.iloc[idx]['low']
                if line_price >= candle_low:
                    line_crosses_support = True
                    if debug:
                        print(f"   ❌ Линия T2-T4 пересекает свечу {idx}: линия={line_price:.2f}, low={candle_low:.2f}")
                    break
            
            if line_crosses_support:
                if debug:
                    print(f"   ❌ Линия поддержки T2-T4 пересекает свечи")
                return []
            
            if debug:
                print(f"   ✅ Линии не пересекают тела и тени свечей")
            
            # 7. Проверка линии тренда T1-T3 (верхняя граница флага)
            # Уравнение прямой через точки (t1_idx, t1) и (t3_idx, t3)
            current_idx = len(df) - 1
            current_price = df.iloc[-1]['close']
            
            if (t3_idx - t1_idx) == 0:
                if debug:
                    print(f"\n❌ Деление на ноль при расчете наклона T1-T3")
                return []  # Деление на ноль
            
            slope = (t3 - t1) / (t3_idx - t1_idx)
            resistance_price_now = t1 + slope * (current_idx - t1_idx)
            
            if debug:
                print(f"\n{'='*60}")
                print("ПРОВЕРКА ПРОБОЯ")
                print(f"{'='*60}")
                print(f"Линия сопротивления: y = {t1:.2f} + {slope:.4f} * (idx - {t1_idx})")
                print(f"Текущая цена: {current_price:.2f}")
                print(f"Линия сопротивления на текущей свече: {resistance_price_now:.2f}")
            
            # СИГНАЛ: Проверяем пробой линии сопротивления T1-T3
            # Ищем пробой среди последних свечей (проверяем high свечей)
            max_pattern_idx = max(t3_idx, t4_idx)
            breakout_found = False
            breakout_idx = None
            
            if debug:
                print(f"\nИщем пробой после max(T3={t3_idx}, T4={t4_idx}) = {max_pattern_idx}")
                print(f"Проверяем свечи от {max_pattern_idx + 1} до {current_idx}:")
            
            # Проверяем свечи после паттерна (от max_pattern_idx до текущей)
            for check_idx in range(max_pattern_idx + 1, min(current_idx + 1, len(df))):
                # Рассчитываем значение линии сопротивления для этой свечи
                resistance_at_check = t1 + slope * (check_idx - t1_idx)
                candle_high = df.iloc[check_idx]['high']
                if debug:
                    print(f"  Свеча {check_idx}: high={candle_high:.2f}, сопротивление={resistance_at_check:.2f}, пробой: {candle_high > resistance_at_check}")
                if candle_high > resistance_at_check:
                    breakout_found = True
                    breakout_idx = check_idx
                    if debug:
                        print(f"  ✅ ПРОБОЙ НАЙДЕН на свече {breakout_idx}!")
                    break
            
            if not breakout_found:
                if debug:
                    print(f"\n❌ Пробой не найден")
                return []
            
            # --- ФИЛЬТРЫ КАЧЕСТВА ПРОБОЯ ---
            if debug:
                print(f"\n{'='*60}")
                print("ПРОВЕРКА КАЧЕСТВА ПРОБОЯ")
                print(f"{'='*60}")
            
            # 8.1. Проверка силы пробоя
            resistance_at_breakout = t1 + slope * (breakout_idx - t1_idx)
            breakout_strength = ((df.iloc[breakout_idx]['high'] - resistance_at_breakout) / resistance_at_breakout) * 100
            min_breakout_strength = 0.3  # Минимум 0.3% выше линии
            
            if debug:
                print(f"\n8.1. Сила пробоя: {breakout_strength:.2f}% (минимум {min_breakout_strength}%)")
            if breakout_strength < min_breakout_strength:
                if debug:
                    print(f"   ❌ Слабый пробой: {breakout_strength:.2f}% < {min_breakout_strength}%")
                return []
            if debug:
                print(f"   ✅ Пробой достаточно сильный")
            
            # 8.2. Проверка объема на пробое
            avg_volume = df['volume'].mean()
            breakout_volume = df.iloc[breakout_idx]['volume']
            min_volume_multiplier = 1.15  # Объем должен быть минимум на 15% выше среднего
            
            if debug:
                print(f"\n8.2. Объем на пробое: {breakout_volume:.0f} (средний: {avg_volume:.0f}, требуется: {avg_volume * min_volume_multiplier:.0f})")
            if breakout_volume < avg_volume * min_volume_multiplier:
                if debug:
                    print(f"   ❌ Слабый объем на пробое: {breakout_volume:.0f} < {avg_volume * min_volume_multiplier:.0f}")
                return []
            if debug:
                print(f"   ✅ Объем на пробое достаточен")
            
            # 8.3. Проверка объема на флагштоке (импульсе)
            pole_volumes = df.iloc[t0_idx:t1_idx+1]['volume']
            avg_pole_volume = pole_volumes.mean()
            min_pole_volume_multiplier = 1.1  # Объем на импульсе должен быть выше среднего
            
            if debug:
                print(f"\n8.3. Средний объем на флагштоке: {avg_pole_volume:.0f} (средний общий: {avg_volume:.0f})")
            if avg_pole_volume < avg_volume * min_pole_volume_multiplier:
                if debug:
                    print(f"   ⚠️ Объем на флагштоке слабоват, но продолжаем")
                # Это предупреждение, не критично
            
            candles_after_pattern = current_idx - max_pattern_idx
            if debug:
                print(f"\nСвечей после паттерна: {candles_after_pattern}")
            if 1 <= candles_after_pattern <= 20:
                if debug:
                    print(f"✅ Пробой недавний (1-20 свечей)")
                
                # Рассчитываем оценку качества паттерна
                quality_score = 0
                volume_ratio = breakout_volume / avg_volume if avg_volume > 0 else 1
                pole_volume_ratio = avg_pole_volume / avg_volume if avg_volume > 0 else 1
                
                # Баллы за силу пробоя
                if breakout_strength > 1.0:
                    quality_score += 30
                elif breakout_strength > 0.5:
                    quality_score += 15
                else:
                    quality_score += 5
                
                # Баллы за объем на пробое
                if volume_ratio > 2.0:
                    quality_score += 30
                elif volume_ratio > 1.5:
                    quality_score += 20
                elif volume_ratio > 1.2:
                    quality_score += 10
                
                # Баллы за объем на флагштоке
                if pole_volume_ratio > 1.5:
                    quality_score += 20
                elif pole_volume_ratio > 1.2:
                    quality_score += 10
                
                # Баллы за соотношение высота/ширина флага
                flag_width = t4_idx - t1_idx
                if flag_width > 0:
                    aspect_ratio = pole_height / flag_width
                    if 0.01 <= aspect_ratio <= 0.1:  # Оптимальное соотношение
                        quality_score += 20
                
                if debug:
                    print(f"\n{'='*60}")
                    print(f"✅ БЫЧИЙ ПАТТЕРН НАЙДЕН! (Качество: {quality_score}/100)")
                    print(f"{'='*60}")
                
                return [{
                    'pattern': 'FLAG_0_1_2_3_4',
                    'timeframe': timeframe,
                    't0': {'idx': t0_idx, 'price': t0, 'time': df.iloc[t0_idx]['time']},
                    't1': {'idx': t1_idx, 'price': t1, 'time': df.iloc[t1_idx]['time']},
                    't2': {'idx': t2_idx, 'price': t2, 'time': df.iloc[t2_idx]['time']},
                    't3': {'idx': t3_idx, 'price': t3, 'time': df.iloc[t3_idx]['time']},
                    't4': {'idx': t4_idx, 'price': t4, 'time': df.iloc[t4_idx]['time']},
                    'current_price': current_price,
                    'resistance_line': resistance_price_now,
                    'pole_height': pole_height,
                    'quality_score': quality_score,
                    'breakout_strength': breakout_strength,
                    'breakout_volume_ratio': volume_ratio
                }]
            else:
                if debug:
                    print(f"❌ Пробой не недавний: {candles_after_pattern} свечей после паттерна (максимум 20)")
                return []
            
        except Exception as e:
            if debug:
                print(f"\n❌ Ошибка анализа: {e}")
                import traceback
                traceback.print_exc()
            return []
        
        return []


if __name__ == "__main__":
    # Тестирование
    TOKEN = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not TOKEN:
        raise ValueError("Токен не найден!")
    
    scanner = BullishFlagScanner(TOKEN)
    
    # Тест на RMH6
    ticker = "RMH6"
    class_code = "SPBFUT"
    
    print(f"Загрузка данных для {ticker}...")
    df = scanner.get_candles_df(ticker, class_code, days_back=5)
    
    if df.empty:
        print("Нет данных")
    else:
        print(f"Загружено {len(df)} свечей")
        patterns = scanner.analyze(df, debug=True)
        
        if patterns:
            print("\nНайденные паттерны:")
            for p in patterns:
                print(f"  {p}")
        else:
            print("\nПаттерны не найдены")
