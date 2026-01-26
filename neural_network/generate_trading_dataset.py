import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path
from datetime import timedelta
from tqdm import tqdm
from dotenv import load_dotenv

# Добавляем путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from t_tech.invest import Client, CandleInterval, InstrumentIdType
from t_tech.invest.utils import quotation_to_decimal

# Импортируем нашу стратегию
from trading_bot.trade_strategy import TradeStrategy

load_dotenv()

class BacktestGenerator:
    def __init__(self):
        self.token = os.environ.get("TINKOFF_INVEST_TOKEN")
        self.strategy = TradeStrategy()
        self.output_file = Path("neural_network/data/ml_trading_dataset.csv")
        self.annotations_file = Path("neural_network/data/annotations.csv")

    def get_candles(self, ticker, start_time, end_time, timeframe):
        """Загружает свечи через API"""
        try:
            interval = CandleInterval.CANDLE_INTERVAL_HOUR if '1h' in timeframe else CandleInterval.CANDLE_INTERVAL_5_MIN
            
            with Client(self.token) as client:
                # Ищем инструмент
                instruments = client.instruments.shares().instruments
                # Пытаемся найти в акциях
                item = next((i for i in instruments if i.ticker == ticker), None)
                
                # Если нет, ищем во фьючерсах (упрощенно)
                if not item:
                    futures = client.instruments.futures().instruments
                    item = next((i for i in futures if i.ticker == ticker), None)

                if not item:
                    return pd.DataFrame()

                candles = client.get_all_candles(
                    instrument_id=item.uid,
                    from_=start_time,
                    to=end_time,
                    interval=interval
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
                
                df = pd.DataFrame(data)
                if not df.empty:
                    df['time'] = pd.to_datetime(df['time']).dt.tz_convert('Europe/Moscow').dt.tz_localize(None)
                    # EMA для стратегии
                    df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
                    df['ema_14'] = df['close'].ewm(span=14, adjust=False).mean()
                
                return df
        except Exception as e:
            # print(f"Error loading {ticker}: {e}")
            return pd.DataFrame()

    def simulate_trade(self, row):
        """
        Симулирует сделку для одной строки аннотации.
        """
        ticker = row['ticker']
        timeframe = row.get('timeframe', '1h')
        
        # Точки паттерна
        t4_price = row['t4_price']
        # Предполагаем, что t4_idx в аннотации относится к файлу, которого у нас может не быть
        # Поэтому нам важно время. Но в annotations.csv часто нет времени T4.
        # Придется опираться на имя файла, если там есть дата.
        
        # ПАРСИНГ ВРЕМЕНИ ИЗ ИМЕНИ ФАЙЛА
        # Пример: ROSN_1h_20251120_120000.csv
        try:
            filename = row['file']
            date_str = filename.split('_')[-2] # 20251120
            time_str = filename.split('_')[-1].split('.')[0] # 120000
            end_datetime = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
        except:
            return None # Не можем восстановить время

        # Загружаем историю: за 5 дней ДО (для индикаторов) и 10 дней ПОСЛЕ (для результата)
        start_load = end_datetime - timedelta(days=10)
        end_load = end_datetime + timedelta(days=20)
        
        df = self.get_candles(ticker, start_load, end_load, timeframe)
        if df.empty: return None

        # Находим индекс свечи, соответствующей концу паттерна (примерно T4)
        # Ищем ближайшую свечу к end_datetime
        # end_datetime - это время окончания паттерна (последняя свеча в файле разметки)
        
        # Срез данных ПОСЛЕ паттерна
        future_df = df[df['time'] > end_datetime].copy().reset_index(drop=True)
        history_df = df[df['time'] <= end_datetime].copy()
        
        if future_df.empty or history_df.empty: return None

        # --- ПОДГОТОВКА ПАТТЕРНА ДЛЯ СТРАТЕГИИ ---
        pattern = {
            'pattern': 'FLAG' if row['label'] == 1 else 'BEARISH_FLAG',
            't0': {'price': row['t0_price']},
            't1': {'price': row['t1_price'], 'idx': row['t1_idx']}, # idx здесь условный
            't2': {'price': row['t2_price'], 'idx': row['t2_idx']},
            't3': {'price': row['t3_price'], 'idx': row['t3_idx']},
            't4': {'price': row['t4_price'], 'idx': row['t4_idx']},
        }
        
        # Рассчитываем уровни выхода
        # Entry price берем как close последней свечи паттерна (или T4)
        entry_price = history_df.iloc[-1]['close']
        
        # Используем стратегию для расчета SL/TP
        exit_levels = self.strategy.calculate_exit_levels(history_df, pattern, entry_price)
        stop_loss = exit_levels['stop_loss']
        take_profit = exit_levels['take_profit']
        
        direction = 'LONG' if row['label'] == 1 else 'SHORT'
        
        # --- СИМУЛЯЦИЯ ---
        result = {
            'ticker': ticker,
            'timeframe': timeframe,
            'direction': direction,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'outcome': 'HOLD',
            'pnl_percent': 0.0,
            'bars_held': 0
        }
        
        for i, candle in future_df.iterrows():
            high = candle['high']
            low = candle['low']
            close = candle['close']
            
            # Проверка SL/TP
            if direction == 'LONG':
                # Сначала проверяем Low на предмет стопа
                if low <= stop_loss:
                    result['outcome'] = 'LOSS'
                    result['pnl_percent'] = (stop_loss - entry_price) / entry_price * 100
                    result['bars_held'] = i
                    break
                # Потом High на предмет тейка
                if high >= take_profit:
                    result['outcome'] = 'WIN'
                    result['pnl_percent'] = (take_profit - entry_price) / entry_price * 100
                    result['bars_held'] = i
                    break
            else: # SHORT
                # Сначала High на предмет стопа
                if high >= stop_loss:
                    result['outcome'] = 'LOSS'
                    result['pnl_percent'] = (entry_price - stop_loss) / entry_price * 100
                    result['bars_held'] = i
                    break
                # Потом Low на предмет тейка
                if low <= take_profit:
                    result['outcome'] = 'WIN'
                    result['pnl_percent'] = (entry_price - take_profit) / entry_price * 100
                    result['bars_held'] = i
                    break
                    
        # Если закончились данные, а сделка не закрыта
        if result['outcome'] == 'HOLD':
            last_close = future_df.iloc[-1]['close']
            if direction == 'LONG':
                result['pnl_percent'] = (last_close - entry_price) / entry_price * 100
            else:
                result['pnl_percent'] = (entry_price - last_close) / entry_price * 100
            result['bars_held'] = len(future_df)

        # Добавляем геометрические фичи (для обучения)
        # Отношение коррекции к древку
        pole_height = abs(row['t1_price'] - row['t0_price'])
        correction_depth = abs(row['t2_price'] - row['t1_price'])
        result['correction_ratio'] = correction_depth / pole_height if pole_height != 0 else 0
        
        # Наклон канала
        result['slope_channel'] = (row['t3_price'] - row['t1_price']) / (row['t3_idx'] - row['t1_idx']) if (row['t3_idx'] - row['t1_idx']) != 0 else 0
        
        return result

    def run(self):
        print("🚀 Генерация датасета для обучения торговой модели...")
        if not self.annotations_file.exists():
            print("❌ Файл аннотаций не найден")
            return

        df_ann = pd.read_csv(self.annotations_file)
        # Фильтруем только полные паттерны
        df_ann = df_ann.dropna(subset=['t4_price'])
        
        results = []
        
        print(f"   Обработка {len(df_ann)} паттернов...")
        for idx, row in tqdm(df_ann.iterrows(), total=len(df_ann)):
            try:
                res = self.simulate_trade(row)
                if res:
                    results.append(res)
            except Exception as e:
                pass # Игнорируем ошибки загрузки отдельных тикеров
                
        if results:
            df_res = pd.DataFrame(results)
            df_res.to_csv(self.output_file, index=False)
            
            print(f"\n✅ Датасет создан: {self.output_file}")
            print(f"   Всего записей: {len(df_res)}")
            print(f"   Win Rate: {len(df_res[df_res['outcome']=='WIN']) / len(df_res) * 100:.1f}%")
        else:
            print("❌ Не удалось создать датасет (возможно, нет данных API)")

if __name__ == "__main__":
    from datetime import datetime
    gen = BacktestGenerator()
    gen.run()
