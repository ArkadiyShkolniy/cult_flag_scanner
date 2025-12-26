import os
import pandas as pd
import numpy as np
from datetime import timedelta
from t_tech.invest import Client, CandleInterval, InstrumentIdType, InstrumentStatus
from t_tech.invest.utils import now, quotation_to_decimal
from dotenv import load_dotenv

load_dotenv()

class BearishFlagScanner:
    """
    Сканер для поиска паттерна Медвежий Флаг (шорт) со структурой 0-1-2-3-4:
    
    - T0: Начало падения (High перед флагштоком вниз)
    - T1: Низ флагштока (Low)
    - T2: Первый откат (High)
    - T3: Второй минимум (Low, >= T1)
    - T4: Второй откат (High, <= T2)
    - Сигнал: Генерируется при формировании T4 (паттерн готов к пробою)
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
        Основной метод анализа - ищет медвежий флаг
        Возвращает список найденных паттернов
        """
        if len(df) < 50:
            return []
        
        return self.analyze_bearish_flag_0_1_2_3_4(df, debug=debug, timeframe=timeframe)

    def analyze_bearish_flag_0_1_2_3_4(self, df: pd.DataFrame, debug=False, timeframe='1h'):
        """
        Ищет паттерн Медвежий Флаг (перевернутый) со структурой 0-1-2-3-4
        
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
                print("НАЧАЛО АНАЛИЗА МЕДВЕЖЬЕГО ПАТТЕРНА 0-1-2-3-4")
                print("=" * 60)
            
            # Находим локальные экстремумы
            highs_idx, lows_idx = self._find_local_extrema(df, window=3)
            
            if debug:
                print(f"\nНайдено максимумов: {len(highs_idx)}, минимумов: {len(lows_idx)}")
                print(f"Максимумы (последние 10): {highs_idx[-10:]}")
                print(f"Минимумы (последние 10): {lows_idx[-10:]}")
            
            if len(highs_idx) < 2 or len(lows_idx) < 3:
                if debug: 
                    print("❌ Недостаточно экстремумов")
                return []

            # --- ПОИСК ТОЧЕК ---
            
            # Ищем T1 (Дно флагштока - самый низкий минимум в недавнем диапазоне)
            # Исключаем последний минимум (может быть пробоем)
            search_lows = lows_idx[:-1]
            if len(search_lows) < 2: 
                if debug:
                    print("❌ Недостаточно минимумов для поиска T1")
                return []
            
            t1_idx = None
            t1_price = float('inf')
            
            # Ищем самый глубокий минимум среди последних
            for l_idx in search_lows:
                l_price = df.iloc[l_idx]['low']
                if l_price < t1_price:
                    t1_price = l_price
                    t1_idx = l_idx
            
            if t1_idx is None: 
                if debug:
                    print("❌ T1 не найден")
                return []
            if debug: 
                print(f"✅ T1 (дно) найден: idx {t1_idx}, цена {t1_price:.2f}, время {df.iloc[t1_idx]['time']}")

            # Ищем T3 (Второе дно - минимум после T1, чуть выше или равен T1)
            # Исключаем последние свечи (пробой)
            search_end_idx = len(df) - 4
            t3_idx = None
            t3_price = float('inf')
            
            if debug:
                print(f"\n--- ПОИСК T3 (второе дно) ---")
                print(f"Исключаем свечи после индекса {search_end_idx} (последние 4 свечи)")
                print(f"Ищем минимум после T1 (idx {t1_idx}), не ниже T1 более чем на 5%")
            
            # Ищем среди экстремумов
            for l_idx in reversed(search_lows):
                if t1_idx < l_idx <= search_end_idx:
                    l_price = df.iloc[l_idx]['low']
                    # T3 >= T1 * 0.95 (допускаем небольшой перелет вниз, но в целом выше)
                    if l_price >= t1_price * 0.95: 
                        t3_price = l_price
                        t3_idx = l_idx
                        if debug:
                            print(f"  ✅ Найден T3 среди экстремумов: idx {t3_idx}, цена {t3_price:.2f}")
                        break # Берем последний подходящий
            
            # Если не нашли среди экстремумов, ищем среди свечей
            if t3_idx is None:
                if debug:
                    print(f"  Не найдено среди экстремумов, ищем среди всех свечей...")
                for idx in range(search_end_idx, t1_idx, -1):
                    l_price = df.iloc[idx]['low']
                    if l_price >= t1_price * 0.95:
                        if idx > 0 and idx < len(df)-1:
                            if l_price <= df.iloc[idx-1]['low'] and l_price <= df.iloc[idx+1]['low']:
                                t3_price = l_price
                                t3_idx = idx
                                if debug:
                                    print(f"  ✅ Найден T3 среди свечей: idx {t3_idx}, цена {t3_price:.2f}")
                                break
            
            if t3_idx is None: 
                if debug:
                    print(f"❌ T3 не найден")
                return []
            if debug: 
                print(f"✅ T3 (второе дно) найден: idx {t3_idx}, цена {t3_price:.2f}, время {df.iloc[t3_idx]['time']}")

            # Ищем T2 (первый откат вверх после T1, перед T3)
            # T2 должен быть первым максимумом после T1, но до T3
            t2_idx = None
            t2_price = 0
            
            if debug:
                print(f"\n--- ПОИСК T2 (первый откат вверх) ---")
                print(f"Ищем первый максимум между T1 (idx {t1_idx}) и T3 (idx {t3_idx})")
            
            for h in highs_idx:
                if t1_idx < h < t3_idx:  # T2 между T1 и T3
                    h_price = df.iloc[h]['high']
                    if t2_idx is None or h < t2_idx:  # Берем первый (ранний) максимум, не последний
                        t2_idx = h
                        t2_price = h_price
            
            if t2_idx is None: 
                if debug: 
                    print(f"❌ T2 не найден (нет максимума между T1={t1_idx} и T3={t3_idx})")
                return []
            if debug: 
                print(f"✅ T2 (первый откат) найден: idx {t2_idx}, цена {t2_price:.2f}, время {df.iloc[t2_idx]['time']}")

            if not (t1_idx < t2_idx): 
                if debug: 
                    print(f"❌ Нарушена хронология: T1 ({t1_idx}) >= T2 ({t2_idx})")
                return []

            # Ищем T4 (второй откат вверх после T3, перед пробоем)
            # T4 должен быть последним максимумом после T3, но перед последними свечами (чтобы исключить пробой)
            search_end_idx_t4 = len(df) - 4  # Исключаем последние свечи (могут быть пробоем)
            t4_idx = None
            t4_price = 0
            
            if debug:
                print(f"\n--- ПОИСК T4 (второй откат вверх) ---")
                print(f"Ищем последний максимум между T3 (idx {t3_idx}) и индексом {search_end_idx_t4}")
            
            for h in highs_idx:
                if t3_idx < h <= search_end_idx_t4:  # T4 между T3 и концом (исключая пробой)
                    h_price = df.iloc[h]['high']
                    if t4_idx is None or h > t4_idx:  # Берем последний подходящий максимум
                        t4_idx = h
                        t4_price = h_price
            
            # Если T4 не найден среди экстремумов, ищем среди всех свечей
            if t4_idx is None:
                if debug:
                    print(f"⚠️ T4 не найден среди экстремумов, ищем среди всех свечей...")
                # Ищем максимум среди всех свечей после T3
                for idx in range(t3_idx + 1, len(df) - 2):  # Исключаем последние 2 свечи
                    h_price = df.iloc[idx]['high']
                    if h_price > t4_price:
                        t4_price = h_price
                        t4_idx = idx
            
            if t4_idx is None:
                if debug: 
                    print(f"❌ T4 не найден (нет максимума между T3={t3_idx} и концом)")
                return []
            if debug: 
                print(f"✅ T4 (второй откат) найден: idx {t4_idx}, цена {t4_price:.2f}, время {df.iloc[t4_idx]['time']}")

            # Ищем T0 (Начало падения - максимум перед T1)
            # T0 должна быть значительно выше T1, чтобы флагшток был длинным
            # Берем самый высокий максимум среди кандидатов перед T1
            t0_candidates = highs_idx[highs_idx < t1_idx]
            if len(t0_candidates) == 0: 
                if debug: 
                    print(f"❌ T0 не найден (нет максимума перед T1={t1_idx})")
                return []
            
            if debug:
                print(f"\n--- ПОИСК T0 (начало падения) ---")
                print(f"Ищем самый высокий максимум среди {len(t0_candidates)} кандидатов перед T1")
            
            # Ищем самый высокий максимум среди кандидатов для длинного флагштока
            t0_idx = None
            t0_price = 0
            for h_idx in t0_candidates:
                h_price = df.iloc[h_idx]['high']
                if h_price > t0_price:
                    t0_price = h_price
                    t0_idx = h_idx
            
            if t0_idx is None:
                if debug: 
                    print(f"❌ T0 не найден")
                return []
            
            t0 = df.iloc[t0_idx]['high'] # High для медвежьего флага
            if debug: 
                print(f"✅ T0 (начало) найден: idx {t0_idx}, цена {t0:.2f}, время {df.iloc[t0_idx]['time']}")

            # Получаем цены
            t1 = df.iloc[t1_idx]['low']
            t2 = df.iloc[t2_idx]['high']
            t3 = df.iloc[t3_idx]['low']
            t4 = df.iloc[t4_idx]['high']

            if debug:
                print(f"\nВсе точки найдены:")
                print(f"  T0: {t0:.2f} (idx {t0_idx})")
                print(f"  T1: {t1:.2f} (idx {t1_idx})")
                print(f"  T2: {t2:.2f} (idx {t2_idx})")
                print(f"  T3: {t3:.2f} (idx {t3_idx})")
                print(f"  T4: {t4:.2f} (idx {t4_idx})")

            # --- ГЕОМЕТРИЯ ---
            
            if debug:
                print(f"\n{'='*60}")
                print("ПРОВЕРКА ГЕОМЕТРИЧЕСКИХ УСЛОВИЙ")
                print(f"{'='*60}")
            
            # 1. Флагшток (T0-T1) - падение
            pole_height = t0 - t1
            if debug:
                print(f"\n1. Флагшток (T0-T1): {pole_height:.2f}")
            if pole_height <= 0: 
                if debug:
                    print(f"   ❌ Высота флагштока <= 0")
                return []
            
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
            
            # 2. T3 >= T1 * 0.95 (уже проверено при поиске)
            if debug:
                print(f"\n2. T3 >= T1 * 0.95: {t3:.2f} >= {t1 * 0.95:.2f}")
                print(f"   ✅ T3 в допустимых пределах")
            
            # 3. T2 (откат вверх) не должен быть слишком высоким (не выше 60% коррекции)
            # В медвежьем флаге консолидация идет внизу.
            max_t2 = t1 + 0.6 * pole_height 
            if debug:
                print(f"\n3. T2 <= {max_t2:.2f} (не выше 60% коррекции): T2 = {t2:.2f}")
            if t2 > max_t2:
                if debug: 
                    print(f"   ❌ T2 слишком высокий: {t2:.2f} > {max_t2:.2f}")
                return []
            if debug:
                print(f"   ✅ T2 коррекция допустима")

            # 4. T4 не должен быть слишком высоким (не выше 50% коррекции)
            max_t4 = t1 + 0.5 * pole_height
            if debug:
                print(f"\n4. T4 <= {max_t4:.2f} (не выше 50% коррекции): T4 = {t4:.2f}")
            if t4 > max_t4:
                if debug: 
                    print(f"   ❌ T4 слишком высокий: {t4:.2f} > {max_t4:.2f}")
                return []
            if debug:
                print(f"   ✅ T4 коррекция допустима")

            # 5. Линии T1-T3 (поддержка) и T2-T4 (сопротивление) не должны расходиться
            # В медвежьем флаге (канал вверх) сопротивление (верх) и поддержка (низ).
            # Они должны сходиться или быть параллельны, но не расходиться.
            if (t3_idx - t1_idx) == 0 or (t4_idx - t2_idx) == 0:
                if debug:
                    print(f"\n5. Проверка направления линий: пропущена (деление на ноль)")
            else:
                slope_support = (t3 - t1) / (t3_idx - t1_idx)
                slope_resistance = (t4 - t2) / (t4_idx - t2_idx)
                
                if debug:
                    print(f"\n5. Проверка направления линий тренда:")
                    print(f"   Наклон поддержки (T1-T3): {slope_support:.4f}")
                    print(f"   Наклон сопротивления (T2-T4): {slope_resistance:.4f}")
                    print(f"   Условие: slope_resistance <= slope_support + 0.05 (линии параллельны или сходятся)")
                
                # Линии не должны расходиться (расширяться вправо)
                # Значит верхняя линия (Res) не должна расти быстрее нижней (Sup)
                # slope_resistance <= slope_support (примерно)
                if slope_resistance > slope_support + 0.05: # Допуск
                    if debug: 
                        print(f"   ❌ Линии расходятся: slope_resistance ({slope_resistance:.4f}) > slope_support ({slope_support:.4f}) + 0.05")
                    return []
                if debug:
                    print(f"   ✅ Линии параллельны или сходятся (не расходятся)")

            # 6. Проверка, что линии не пересекают тела свечей и их тени
            if debug:
                print(f"\n6. Проверка пересечения линий со свечами:")
            
            # Линия T1-T3 (поддержка) должна проходить НИЖЕ всех свечей между T1 и T3
            slope_support = (t3 - t1) / (t3_idx - t1_idx)
            line_crosses_support = False
            for idx in range(t1_idx + 1, t3_idx):
                line_price = t1 + slope_support * (idx - t1_idx)
                candle_low = df.iloc[idx]['low']
                if line_price >= candle_low:
                    line_crosses_support = True
                    if debug:
                        print(f"   ❌ Линия T1-T3 пересекает свечу {idx}: линия={line_price:.2f}, low={candle_low:.2f}")
                    break
            
            if line_crosses_support:
                if debug:
                    print(f"   ❌ Линия поддержки T1-T3 пересекает свечи")
                return []
            
            # Линия T2-T4 (сопротивление) должна проходить ВЫШЕ всех свечей между T2 и T4
            slope_resistance = (t4 - t2) / (t4_idx - t2_idx)
            line_crosses_resistance = False
            for idx in range(t2_idx + 1, t4_idx):
                line_price = t2 + slope_resistance * (idx - t2_idx)
                candle_high = df.iloc[idx]['high']
                if line_price <= candle_high:
                    line_crosses_resistance = True
                    if debug:
                        print(f"   ❌ Линия T2-T4 пересекает свечу {idx}: линия={line_price:.2f}, high={candle_high:.2f}")
                    break
            
            if line_crosses_resistance:
                if debug:
                    print(f"   ❌ Линия сопротивления T2-T4 пересекает свечи")
                return []
            
            if debug:
                print(f"   ✅ Линии не пересекают тела и тени свечей")

            # 7. Проверка что T4 сформирована недавно (сигнал генерируется при формировании T4)
            current_idx = len(df) - 1
            current_price = df.iloc[-1]['close']
            
            # Проверяем, что T4 близка к текущей свече (паттерн только что сформировался)
            candles_after_t4 = current_idx - t4_idx
            
            if debug:
                print(f"\n{'='*60}")
                print("ПРОВЕРКА СВЕЖЕСТИ ПАТТЕРНА")
                print(f"{'='*60}")
                print(f"Текущий индекс: {current_idx}, T4 индекс: {t4_idx}")
                print(f"Свечей после T4: {candles_after_t4}")
            
            # T4 должна быть на последней свече или очень близко к ней (максимум 2-3 свечи после)
            max_candles_after_t4 = 3  # Допускаем максимум 3 свечи после T4
            
            if candles_after_t4 > max_candles_after_t4:
                if debug:
                    print(f"   ❌ T4 слишком старая: {candles_after_t4} свечей после T4 (максимум {max_candles_after_t4})")
                return []
            if debug:
                print(f"   ✅ T4 свежая, паттерн только что сформировался")
            
            # --- ФИЛЬТРЫ КАЧЕСТВА ПАТТЕРНА ---
            if debug:
                print(f"\n{'='*60}")
                print("ПРОВЕРКА КАЧЕСТВА ПАТТЕРНА")
                print(f"{'='*60}")
            
            # 8.1. Проверка объема на флагштоке (импульсе)
            avg_volume = df['volume'].mean()
            pole_volumes = df.iloc[t0_idx:t1_idx+1]['volume']
            avg_pole_volume = pole_volumes.mean()
            
            if debug:
                print(f"\n8.1. Средний объем на флагштоке: {avg_pole_volume:.0f} (средний общий: {avg_volume:.0f})")
            
            # 8.2. Проверка объема на T4 (завершение формирования паттерна)
            t4_volume = df.iloc[t4_idx]['volume']
            
            if debug:
                print(f"\n8.2. Объем на T4: {t4_volume:.0f} (средний: {avg_volume:.0f})")
            
            # Рассчитываем оценку качества паттерна
            quality_score = 0
            pole_volume_ratio = avg_pole_volume / avg_volume if avg_volume > 0 else 1
            t4_volume_ratio = t4_volume / avg_volume if avg_volume > 0 else 1
            
            # Баллы за объем на флагштоке
            if pole_volume_ratio > 1.5:
                quality_score += 30
            elif pole_volume_ratio > 1.2:
                quality_score += 20
            elif pole_volume_ratio > 1.1:
                quality_score += 10
            
            # Баллы за объем на T4
            if t4_volume_ratio > 1.2:
                quality_score += 20
            elif t4_volume_ratio > 0.9:
                quality_score += 10
            
            # Баллы за соотношение высота/ширина флага
            flag_width = t4_idx - t1_idx
            if flag_width > 0:
                aspect_ratio = pole_height / flag_width
                if 0.01 <= aspect_ratio <= 0.1:  # Оптимальное соотношение
                    quality_score += 30
                elif 0.005 <= aspect_ratio <= 0.15:
                    quality_score += 20
            
            # Баллы за свежесть паттерна (чем свежее, тем лучше)
            if candles_after_t4 == 0:
                quality_score += 20  # T4 на последней свече
            elif candles_after_t4 <= 1:
                quality_score += 15
            elif candles_after_t4 <= 2:
                quality_score += 10
            
            # Рассчитываем линию поддержки для информации (но не проверяем пробой)
            if (t3_idx - t1_idx) != 0:
                slope = (t3 - t1) / (t3_idx - t1_idx)
                support_price_now = t1 + slope * (current_idx - t1_idx)
            else:
                support_price_now = t1
            
            if candles_after_t4 <= max_candles_after_t4:
                if debug:
                    print(f"\n{'='*60}")
                    print(f"✅ МЕДВЕЖИЙ ПАТТЕРН НАЙДЕН! (Качество: {quality_score}/100)")
                    print(f"{'='*60}")
                return [{
                    'pattern': 'BEARISH_FLAG_0_1_2_3_4',
                    'timeframe': timeframe,
                    't0': {'idx': t0_idx, 'price': t0, 'time': df.iloc[t0_idx]['time']},
                    't1': {'idx': t1_idx, 'price': t1, 'time': df.iloc[t1_idx]['time']},
                    't2': {'idx': t2_idx, 'price': t2, 'time': df.iloc[t2_idx]['time']},
                    't3': {'idx': t3_idx, 'price': t3, 'time': df.iloc[t3_idx]['time']},
                    't4': {'idx': t4_idx, 'price': t4, 'time': df.iloc[t4_idx]['time']},
                    'current_price': current_price,
                    'resistance_line': support_price_now,  # Для графика это линия поддержки
                    'pole_height': pole_height,
                    'quality_score': quality_score,
                    'pole_volume_ratio': pole_volume_ratio,
                    't4_volume_ratio': t4_volume_ratio
                }]
            else:
                if debug:
                    print(f"❌ T4 слишком старая: {candles_after_t4} свечей после T4 (максимум {max_candles_after_t4})")
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
    
    scanner = BearishFlagScanner(TOKEN)
    
    # Тест на MXH6
    ticker = "MXH6"
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
