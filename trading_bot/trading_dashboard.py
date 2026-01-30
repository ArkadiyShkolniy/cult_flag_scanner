import streamlit as st
import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from dotenv import load_dotenv
from t_tech.invest import Client, CandleInterval, InstrumentIdType
from t_tech.invest.utils import quotation_to_decimal

# Добавляем путь к корню проекта для импорта модулей
sys.path.insert(0, str(Path(__file__).parent.parent))

load_dotenv()

# Настройки страницы
st.set_page_config(
    page_title="🤖 Trading Bot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Определяем режим из переменной окружения (только для информации, не влияет на отображение)
BOT_ENV = os.environ.get("BOT_ENV", "DEBUG")
DATA_DIR_INFO = os.environ.get("DATA_DIR", "trading_bot")

# Пути к файлам
# Получаем путь из переменной окружения или используем дефолтный
DATA_DIR_PATH = os.environ.get("DATA_DIR", "trading_bot")
BASE_DIR = Path(DATA_DIR_PATH)
TRADES_ACTIVE = BASE_DIR / "trades_active.json"
TRADES_HISTORY = BASE_DIR / "trades_history.json"
ML_DATASET = BASE_DIR / "training_data" / "dataset_v1.csv"

def extract_timeframe(strategy_desc):
    """Извлекает таймфрейм из strategy_desc (формат: [1h] или (1h) и т.д.)"""
    if not strategy_desc:
        return "N/A"
    import re
    # Try square brackets
    match = re.search(r'\[(\w+)\]', strategy_desc)
    if match:
        return match.group(1)
    # Try parentheses
    match_p = re.search(r'\((\w+)\)', strategy_desc)
    if match_p:
        return match_p.group(1)
    return "N/A"

def load_data():
    """Загружает данные о сделках"""
    active_trades = {}
    history_trades = []
    
    if TRADES_ACTIVE.exists():
        try:
            with open(TRADES_ACTIVE, 'r') as f:
                loaded_trades = json.load(f)
                # Фильтруем только действительно активные позиции (status == 'OPEN')
                # Также проверяем, что это словарь (не список)
                if isinstance(loaded_trades, dict):
                    active_trades = {
                        ticker: trade 
                        for ticker, trade in loaded_trades.items() 
                        if trade.get('status', 'OPEN') == 'OPEN'
                    }
                    # Если после фильтрации остались закрытые позиции, сохраняем очищенный файл
                    if len(active_trades) < len(loaded_trades):
                        with open(TRADES_ACTIVE, 'w') as f_save:
                            json.dump(active_trades, f_save, indent=4, default=str)
        except Exception as e:
            print(f"Ошибка загрузки активных позиций: {e}")
        
    if TRADES_HISTORY.exists():
        try:
            with open(TRADES_HISTORY, 'r') as f:
                history_trades = json.load(f)
                # Убеждаемся, что это список
                if not isinstance(history_trades, list):
                    history_trades = []
        except Exception as e:
            print(f"Ошибка загрузки истории: {e}")
    
    return active_trades, history_trades

def create_trade_chart(df, pattern_info, trade_data):
    """
    Создает график сделки с паттерном, точками входа и выхода
    
    Args:
        df: DataFrame со свечами
        pattern_info: Словарь с информацией о паттерне (T0-T4)
        trade_data: Словарь с данными о сделке (entry_price, exit_price, stop_loss, take_profit, entry_time)
    """
    # Убеждаемся, что DataFrame отсортирован по времени
    if 'time' in df.columns:
        # Нормализуем timezone - убираем timezone info для корректного сравнения
        if pd.api.types.is_datetime64_any_dtype(df['time']):
            if df['time'].dt.tz is not None:
                df['time'] = df['time'].dt.tz_localize(None)
        # Если время строкой, пробуем преобразовать
        elif pd.api.types.is_object_dtype(df['time']):
             try:
                 df['time'] = pd.to_datetime(df['time'], format='ISO8601', errors='coerce')
                 if df['time'].dt.tz is not None:
                     df['time'] = df['time'].dt.tz_localize(None)
             except:
                 pass
                 
        df = df.sort_values('time').reset_index(drop=True)
    
    # Проверяем наличие всех необходимых колонок
    required_cols = ['open', 'high', 'low', 'close']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Отсутствует обязательная колонка: {col}")
        # Заполняем пропущенные значения
        if df[col].isna().any():
            df[col] = df[col].fillna(method='ffill').fillna(method='bfill')
    
    # Вычисляем EMA, если их нет в данных
    if 'ema_7' not in df.columns:
        df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
    if 'ema_14' not in df.columns:
        df['ema_14'] = df['close'].ewm(span=14, adjust=False).mean()
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('График сделки с паттерном', 'Объем')
    )
    
    # Используем индексы для оси X (как в дашборде разметки)
    indices_x = list(range(len(df)))
    customdata_candles = [[i, df.iloc[i]['time']] for i in range(len(df))] if 'time' in df.columns else [[i, ''] for i in range(len(df))]
    
    # Свечи - используем такой же стиль как в дашборде разметки
    fig.add_trace(
        go.Candlestick(
            x=indices_x,
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name='Цена',
            customdata=customdata_candles,
            hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                         '<b>Время:</b> %{customdata[1]}<br>' +
                         '<b>Open:</b> %{open:.2f}<br>' +
                         '<b>High:</b> %{high:.2f}<br>' +
                         '<b>Low:</b> %{low:.2f}<br>' +
                         '<b>Close:</b> %{close:.2f}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Добавляем EMA 7
    if 'ema_7' in df.columns and not df['ema_7'].isna().all():
        fig.add_trace(go.Scatter(
            x=indices_x,
            y=df['ema_7'],
            mode='lines',
            line=dict(color='yellow', width=1),
            name='EMA 7',
            opacity=0.7,
            hovertemplate='EMA 7: %{y:.2f}<extra></extra>'
        ), row=1, col=1)
    
    # Добавляем EMA 14
    if 'ema_14' in df.columns and not df['ema_14'].isna().all():
        fig.add_trace(go.Scatter(
            x=indices_x,
            y=df['ema_14'],
            mode='lines',
            line=dict(color='purple', width=1),
            name='EMA 14',
            opacity=0.7,
            hovertemplate='EMA 14: %{y:.2f}<extra></extra>'
        ), row=1, col=1)
    
    # Точки паттерна T0-T4
    if pattern_info:
        # Предварительная обработка индексов: пытаемся скорректировать их по времени
        corrected_indices = {}
        
        # Если в dataframe есть время, используем его для сопоставления
        if 'time' in df.columns:
            for point_key in ['t0', 't1', 't2', 't3', 't4']:
                if point_key in pattern_info and 'time' in pattern_info[point_key]:
                    try:
                        # Получаем время из паттерна
                        pt_str = pattern_info[point_key]['time']
                        pt = pd.to_datetime(pt_str)
                        if pt.tzinfo is not None:
                            pt = pt.replace(tzinfo=None)
                        
                        # Находим ближайшую свечу в df
                        # Используем float для вычитания, чтобы избежать проблем с таймзонами
                        # Преобразуем колонку времени в df в naive, если нужно (уже сделано в начале функции, но на всякий случай)
                        
                        # Вычисляем разницу по модулю
                        time_diffs = abs(df['time'] - pt)
                        closest_idx = time_diffs.idxmin()
                        min_diff = time_diffs.min()
                        
                        # Если разница небольшая (например, меньше интервала свечи * 2 или просто разумная)
                        # Для дневного ТФ это может быть много часов, для минутного - минуты
                        # Берем просто ближайшую, так как snapshot должен содержать эту точку
                        corrected_indices[point_key] = int(closest_idx)
                    except Exception as e:
                        print(f"Ошибка корректировки индекса для {point_key}: {e}")
                        pass

        points_data = [
            ('T0', pattern_info.get('t0', {}), 'lime', 'circle', 't0'),
            ('T1', pattern_info.get('t1', {}), 'red', 'diamond', 't1'),
            ('T2', pattern_info.get('t2', {}), 'cyan', 'circle', 't2'),
            ('T3', pattern_info.get('t3', {}), 'orange', 'diamond', 't3'),
            ('T4', pattern_info.get('t4', {}), 'magenta', 'circle', 't4'),
        ]
        
        for label, point, color, symbol, key in points_data:
            if point and 'price' in point:
                # Определяем индекс: сначала ищем в corrected, потом в исходном
                point_idx = None
                if key in corrected_indices:
                    point_idx = corrected_indices[key]
                elif 'idx' in point:
                    point_idx = int(point['idx'])
                
                if point_idx is not None:
                    point_price = float(point['price'])
                    
                    # Проверяем, что точка в диапазоне
                    if 0 <= point_idx < len(df):
                        # Используем индекс
                        point_x = point_idx
                        fig.add_trace(go.Scatter(
                            x=[point_x],
                            y=[point_price],
                            mode='markers+text',
                            marker=dict(size=12, color=color, symbol=symbol, line=dict(width=2, color='white')),
                            text=[label],
                            textposition='top center',
                            name=label,
                            showlegend=True,
                            hovertemplate=f'<b>{label}</b><br>Цена: {point_price:.2f}<extra></extra>'
                        ), row=1, col=1)
        
        # Функция для получения индекса точки
        def get_point_idx(key):
            if key in corrected_indices:
                return corrected_indices[key]
            if key in pattern_info and 'idx' in pattern_info[key]:
                return int(pattern_info[key]['idx'])
            return None

        # Линия флагштока T0-T1
        if 't0' in pattern_info and 't1' in pattern_info:
            t0 = pattern_info['t0']
            t1 = pattern_info['t1']
            t0_idx = get_point_idx('t0')
            t1_idx = get_point_idx('t1')
            
            if t0_idx is not None and t1_idx is not None:
                if 0 <= t0_idx < len(df) and 0 <= t1_idx < len(df):
                    fig.add_trace(go.Scatter(
                        x=[t0_idx, t1_idx],
                        y=[float(t0['price']), float(t1['price'])],
                        mode='lines',
                        line=dict(color='lime', width=2, dash='solid'),
                        name='Флагшток (T0-T1)',
                        showlegend=True
                    ), row=1, col=1)
        
        # Линии канала T1-T3 и T2-T4
        if 't1' in pattern_info and 't3' in pattern_info:
            t1 = pattern_info['t1']
            t3 = pattern_info['t3']
            t1_idx = get_point_idx('t1')
            t3_idx = get_point_idx('t3')
            
            if t1_idx is not None and t3_idx is not None:
                if 0 <= t1_idx < len(df) and 0 <= t3_idx < len(df):
                    fig.add_trace(go.Scatter(
                        x=[t1_idx, t3_idx],
                        y=[float(t1['price']), float(t3['price'])],
                        mode='lines',
                        line=dict(color='yellow', width=2, dash='dash'),
                        name='Канал верх (T1-T3)',
                        showlegend=True
                    ), row=1, col=1)
        
        if 't2' in pattern_info and 't4' in pattern_info:
            t2 = pattern_info['t2']
            t4 = pattern_info['t4']
            t2_idx = get_point_idx('t2')
            t4_idx = get_point_idx('t4')
            
            if t2_idx is not None and t4_idx is not None:
                if 0 <= t2_idx < len(df) and 0 <= t4_idx < len(df):
                    fig.add_trace(go.Scatter(
                        x=[t2_idx, t4_idx],
                        y=[float(t2['price']), float(t4['price'])],
                        mode='lines',
                        line=dict(color='purple', width=2, dash='dash'),
                        name='Канал низ (T2-T4)',
                        showlegend=True
                    ), row=1, col=1)
    
    # Точка входа
    if 'entry_price' in trade_data:
        entry_price = trade_data['entry_price']
        entry_idx = None
        
        # 1. Пробуем найти индекс по времени входа
        if 'entry_time' in trade_data and trade_data['entry_time'] and 'time' in df.columns:
            try:
                entry_dt = pd.to_datetime(trade_data['entry_time']).replace(tzinfo=None)
                # Ищем ближайшую свечу (разница по модулю минимальна)
                time_diff = abs(df['time'] - entry_dt)
                
                # Если разница небольшая (например, меньше 2 интервалов свечи), считаем совпадением
                # Но для простоты берем просто ближайшую
                entry_idx = time_diff.idxmin()
            except Exception as e:
                print(f"Ошибка поиска индекса по времени: {e}")
        
        # 2. Если по времени не нашли, используем T4 как fallback
        if entry_idx is None:
            if pattern_info and 't4' in pattern_info and 'idx' in pattern_info['t4']:
                entry_idx = int(pattern_info['t4']['idx'])
            else:
                entry_idx = len(df) - 1
        
        # Ограничиваем индекс диапазоном
        entry_idx = max(0, min(len(df) - 1, entry_idx))
        
        fig.add_trace(go.Scatter(
            x=[entry_idx],
            y=[entry_price],
            mode='markers+text',
            marker=dict(size=15, color='blue', symbol='star', line=dict(width=2, color='white')),
            text=['ENTRY'],
            textposition='top center',
            name='Вход',
            showlegend=True,
            hovertemplate=f'<b>ВХОД</b><br>Цена: {entry_price:.2f}<extra></extra>'
        ), row=1, col=1)
    
    # Точка выхода (если есть)
    if 'exit_price' in trade_data and trade_data.get('exit_price'):
        exit_price = trade_data['exit_price']
        exit_idx = len(df) - 1 # Default
        
        # 1. Пробуем найти по времени выхода
        if 'exit_time' in trade_data and trade_data['exit_time'] and 'time' in df.columns:
            try:
                exit_dt = pd.to_datetime(trade_data['exit_time']).replace(tzinfo=None)
                time_diff = abs(df['time'] - exit_dt)
                exit_idx = time_diff.idxmin()
            except:
                pass
        # 2. Если времени нет, ищем по цене после входа
        elif 'entry_price' in trade_data: # Fallback logic
             # Используем entry_idx который вычислили выше (но он локальный в блоке if)
             # Придется пересчитать или использовать T4
             start_search = 0
             if pattern_info and 't4' in pattern_info:
                 start_search = int(pattern_info['t4']['idx'])
             
             min_diff = float('inf')
             for i in range(start_search + 1, len(df)):
                candle = df.iloc[i]
                if candle['low'] <= exit_price <= candle['high']:
                    exit_idx = i
                    break
                diff = min(abs(candle['close'] - exit_price), abs(candle['open'] - exit_price))
                if diff < min_diff:
                    min_diff = diff
                    exit_idx = i
        
        fig.add_trace(go.Scatter(
            x=[exit_idx],
            y=[exit_price],
            mode='markers+text',
            marker=dict(size=15, color='gold', symbol='star', line=dict(width=2, color='black')),
            text=['EXIT'],
            textposition='bottom center',
            name='Выход',
            showlegend=True,
            hovertemplate=f'<b>ВЫХОД</b><br>Цена: {exit_price:.2f}<extra></extra>'
        ), row=1, col=1)
    
    # Линии Stop Loss и Take Profit
    if 'stop_loss' in trade_data:
        sl_price = trade_data['stop_loss']
        fig.add_trace(go.Scatter(
            x=[0, len(df) - 1],
            y=[sl_price, sl_price],
            mode='lines',
            line=dict(color='red', width=2, dash='dot'),
            name=f'Stop Loss ({sl_price:.2f})',
            showlegend=True
        ), row=1, col=1)
    
    if 'take_profit' in trade_data:
        tp_price = trade_data['take_profit']
        fig.add_trace(go.Scatter(
            x=[0, len(df) - 1],
            y=[tp_price, tp_price],
            mode='lines',
            line=dict(color='green', width=2, dash='dot'),
            name=f'Take Profit ({tp_price:.2f})',
            showlegend=True
        ), row=1, col=1)
    
    # Объем
    colors_volume = ['red' if df.iloc[i]['close'] < df.iloc[i]['open'] else 'green' 
                     for i in range(len(df))]
    fig.add_trace(go.Bar(
        x=indices_x,
        y=df['volume'],
        name='Объем',
        marker_color=colors_volume,
        customdata=customdata_candles,
        hovertemplate='<b>Индекс:</b> %{customdata[0]}<br>' +
                     '<b>Время:</b> %{customdata[1]}<br>' +
                     '<b>Объем:</b> %{y}<extra></extra>'
    ), row=2, col=1)
    
    # Настройка меток оси X (как в дашборде разметки)
    tick_step = max(1, len(df) // 20)
    tick_indices = list(range(0, len(df), tick_step))
    tick_times = []
    if 'time' in df.columns:
        for i in tick_indices:
            time_val = df.iloc[i]['time']
            if pd.isna(time_val):
                tick_times.append('')
            elif isinstance(time_val, pd.Timestamp):
                # Определяем формат на основе таймфрейма (если можем определить)
                # Для дневного таймфрейма используем только дату
                if len(df) > 1:
                    time_diff = (df.iloc[-1]['time'] - df.iloc[0]['time']) / len(df)
                    if time_diff.total_seconds() > 20 * 3600:
                        tick_times.append(time_val.strftime('%Y-%m-%d'))
                    else:
                        tick_times.append(time_val.strftime('%Y-%m-%d %H:%M'))
                else:
                    tick_times.append(time_val.strftime('%Y-%m-%d %H:%M'))
            else:
                tick_times.append(str(time_val))
    else:
        tick_times = [str(i) for i in tick_indices]
    
    # Настройки осей для единообразного отображения (как в дашборде разметки)
    fig.update_xaxes(
        title_text='Время',
        row=1, col=1,
        showgrid=True,
        gridcolor='rgba(128, 128, 128, 0.2)',
        tickmode='array',
        tickvals=tick_indices,
        ticktext=tick_times,
        tickangle=-45
    )
    fig.update_xaxes(
        title_text='Время',
        row=2, col=1,
        showgrid=True,
        gridcolor='rgba(128, 128, 128, 0.2)',
        tickmode='array',
        tickvals=tick_indices,
        ticktext=tick_times,
        tickangle=-45
    )
    fig.update_yaxes(
        title_text="Цена", 
        row=1, col=1,
        # Единые настройки для одинакового отображения независимо от таймфрейма
        showgrid=True,
        gridcolor='rgba(128, 128, 128, 0.2)'
    )
    fig.update_yaxes(
        title_text="Объем", 
        row=2, col=1,
        showgrid=True,
        gridcolor='rgba(128, 128, 128, 0.2)'
    )
    
    fig.update_layout(
        height=800,
        showlegend=True,
        hovermode='closest',
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        # Настройки для единообразного отображения на всех таймфреймах
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        # Единые настройки для осей X и Y для одинакового масштабирования
        xaxis=dict(
            type='linear',
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            # Фиксируем настройки масштабирования для единообразия
            autorange=True,  # Автоматический диапазон, но с одинаковыми настройками
            fixedrange=False  # Разрешаем зум, но с одинаковыми настройками
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(128, 128, 128, 0.2)',
            # Фиксируем настройки масштабирования для единообразия
            autorange=True,
            fixedrange=False
        )
    )
    
    return fig

def get_current_candles(ticker, class_code, from_date, interval=CandleInterval.CANDLE_INTERVAL_HOUR):
    """Загружает актуальные свечи для тикера"""
    token = os.environ.get("TINKOFF_INVEST_TOKEN")
    if not token:
        return pd.DataFrame()
    
    try:
        with Client(token) as client:
            item = client.instruments.get_instrument_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_TICKER,
                class_code=class_code,
                id=ticker
            ).instrument
            
            candles = client.get_all_candles(
                instrument_id=item.uid,
                from_=from_date,
                to=datetime.now(),
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
                # Вычисляем EMA
                df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
                df['ema_14'] = df['close'].ewm(span=14, adjust=False).mean()
            return df
    except Exception as e:
        st.error(f"Ошибка загрузки свечей для {ticker}: {e}")
        return pd.DataFrame()

def main():
    # Определяем режим из переменной окружения для подписи
    bot_env = os.environ.get("BOT_ENV", "DEBUG")
    data_dir = os.environ.get("DATA_DIR", "trading_bot")
    
    # Заголовок с подписью режима
    if bot_env == "PROD":
        st.title("🤖 Trading Bot Dashboard - 🟢 PRODUCTION")
        st.markdown("**📍 Режим:** Реальная торговля | **📁 Данные:** " + data_dir)
    else:
        st.title("🤖 Trading Bot Dashboard - 🧪 DEBUG")
        st.markdown("**📍 Режим:** Тестовая торговля (Paper Trading) | **📁 Данные:** " + data_dir)
    
    # --- SIDEBAR SETTINGS ---
    st.sidebar.header("⚙️ Настройки торговли")
    
    # Load config (тот же файл читает бот: trading_bot/trading_config.json или trading_bot/data_prod/trading_config.json)
    config_file = BASE_DIR / "trading_config.json"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    trading_config = {}
    if config_file.exists():
        try:
            with open(config_file, 'r') as f:
                trading_config = json.load(f)
        except Exception:
            pass
    current_lot = int(trading_config.get('fixed_lot_size', 1))
    
    new_lot = st.sidebar.number_input(
        "Количество лотов (Fixed Lot)", 
        min_value=1, 
        max_value=100, 
        value=current_lot,
        step=1,
        help="Количество лотов для каждой сделки. Сохраните — бот применит при следующем входе.",
        key="fixed_lot_input"
    )
    
    # Сохраняем при изменении или если конфига ещё нет (чтобы бот точно видел настройку)
    if new_lot != current_lot or not config_file.exists() or trading_config.get('fixed_lot_size') is None:
        trading_config['fixed_lot_size'] = new_lot
        try:
            with open(config_file, 'w') as f:
                json.dump(trading_config, f, indent=4)
            if new_lot != current_lot:
                st.sidebar.success(f"✅ Лоты сохранены: {new_lot}. Бот применит при следующей сделке.")
        except Exception as e:
            st.sidebar.error(f"Не удалось сохранить конфиг: {e}")
    
    if st.sidebar.button("💾 Сохранить настройки лотов", key="save_lot_config"):
        trading_config['fixed_lot_size'] = new_lot
        try:
            with open(config_file, 'w') as f:
                json.dump(trading_config, f, indent=4)
            st.sidebar.success(f"✅ Сохранено: {new_lot} лот(ов). Бот читает: {config_file.name}")
        except Exception as e:
            st.sidebar.error(f"Ошибка: {e}")
        st.rerun()
    
    # --- ЛОГИ РОБОТА ---
    st.sidebar.divider()
    st.sidebar.header("📋 Логи робота")
    
    # Определяем путь к логам в зависимости от режима
    # Используем путь относительно корня проекта
    project_root = Path(__file__).parent.parent
    if bot_env == "PROD":
        log_file = project_root / "logs" / "prod_bot.log"
    else:
        log_file = project_root / "logs" / "debug_bot.log"
    
    # Кнопка обновления логов
    if st.sidebar.button("🔄 Обновить логи", key="refresh_logs"):
        st.rerun()
    
    # Показываем последние N строк логов
    log_lines_count = st.sidebar.slider(
        "Количество строк:",
        min_value=10,
        max_value=100,
        value=50,
        step=10,
        key="log_lines_count"
    )
    
    # Читаем и отображаем логи
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                # Берем последние N строк
                recent_lines = all_lines[-log_lines_count:] if len(all_lines) > log_lines_count else all_lines
                
                # Отображаем логи в expander для удобства
                with st.sidebar.expander("📜 Показать логи", expanded=False):
                    # Создаем текстовую область с логами
                    log_text = ''.join(recent_lines)
                    st.text_area(
                        "Логи:",
                        value=log_text,
                        height=300,
                        key="log_display",
                        disabled=True,
                        label_visibility="collapsed"
                    )
                    
                    # Информация о логе
                    st.caption(f"📊 Всего строк в логе: {len(all_lines)} | Показано: {len(recent_lines)}")
                    
                    # Кнопка скачать логи
                    if st.button("💾 Скачать логи", key="download_logs"):
                        st.download_button(
                            label="⬇️ Скачать полный лог",
                            data=''.join(all_lines),
                            file_name=log_file.name,
                            mime="text/plain",
                            key="download_logs_file"
                        )
        except Exception as e:
            st.sidebar.error(f"❌ Ошибка чтения логов: {e}")
    else:
        st.sidebar.warning(f"⚠️ Файл логов не найден: {log_file}")
        st.sidebar.info("💡 Логи появятся после запуска робота")
    
    st.sidebar.divider()
    
    # Панель управления
    col_refresh, col_auto, col_close, col_stop = st.columns([1, 2, 1, 1])
    with col_refresh:
        if st.button("🔄 Обновить данные", key="refresh_data"):
            st.rerun()
    
    with col_auto:
        auto_refresh = st.checkbox("🔄 Автообновление (30 сек)", value=False, key="auto_refresh")
        if auto_refresh:
            import time
            time.sleep(30)
            st.rerun()
    
    with col_close:
        active_trades, _ = load_data()
        if active_trades:
            if st.button("🛑 Закрыть все позиции", key="close_all", type="secondary"):
                try:
                    # Получаем текущие цены через API
                    token = os.environ.get("TINKOFF_INVEST_TOKEN")
                    current_prices = {}
                    
                    if token:
                        with Client(token) as client:
                            for ticker, trade in active_trades.items():
                                try:
                                    uid = trade.get('uid')
                                    direction = trade.get('direction', 'LONG')
                                    
                                    if uid:
                                        # Для закрытия позиции нужна правильная цена:
                                        # LONG (продажа) -> bid цена (цена покупки в стакане)
                                        # SHORT (покупка) -> ask цена (цена продажи в стакане)
                                        
                                        try:
                                            # Получаем стакан (order book) для bid/ask
                                            orderbook = client.market_data.get_order_book(figi=uid, depth=1)
                                            
                                            if direction == 'LONG':
                                                # Для LONG позиции закрываем продажей -> используем bid (цена покупки)
                                                if orderbook.bids and len(orderbook.bids) > 0:
                                                    price = float(quotation_to_decimal(orderbook.bids[0].price))
                                                else:
                                                    # Если нет bid, используем last_price
                                                    last_price = client.market_data.get_last_prices(figi=[uid])
                                                    if last_price.last_prices:
                                                        price = float(quotation_to_decimal(last_price.last_prices[0].price))
                                                    else:
                                                        price = trade.get('entry_price', 0)
                                            else:  # SHORT
                                                # Для SHORT позиции закрываем покупкой -> используем ask (цена продажи)
                                                if orderbook.asks and len(orderbook.asks) > 0:
                                                    price = float(quotation_to_decimal(orderbook.asks[0].price))
                                                else:
                                                    # Если нет ask, используем last_price
                                                    last_price = client.market_data.get_last_prices(figi=[uid])
                                                    if last_price.last_prices:
                                                        price = float(quotation_to_decimal(last_price.last_prices[0].price))
                                                    else:
                                                        price = trade.get('entry_price', 0)
                                        except Exception as e:
                                            # Если не удалось получить стакан, используем last_price
                                            try:
                                                last_price = client.market_data.get_last_prices(figi=[uid])
                                                if last_price.last_prices:
                                                    price = float(quotation_to_decimal(last_price.last_prices[0].price))
                                                else:
                                                    price = trade.get('entry_price', 0)
                                            except:
                                                price = trade.get('entry_price', 0)
                                        
                                        if price <= 0:
                                            price = trade.get('entry_price', 0)
                                            
                                        current_prices[ticker] = {
                                            'price': price,
                                            'time': datetime.now().isoformat()
                                        }
                                except Exception as e:
                                    # Если не удалось получить цену, используем last_price или entry_price
                                    try:
                                        uid = trade.get('uid')
                                        if uid:
                                            last_price = client.market_data.get_last_prices(figi=[uid])
                                            if last_price.last_prices:
                                                price = float(quotation_to_decimal(last_price.last_prices[0].price))
                                            else:
                                                price = trade.get('entry_price', 0)
                                        else:
                                            price = trade.get('entry_price', 0)
                                    except:
                                        price = trade.get('entry_price', 0)
                                    
                                    if price <= 0:
                                        price = trade.get('entry_price', 0)
                                        
                                    current_prices[ticker] = {
                                        'price': price,
                                        'time': datetime.now().isoformat()
                                    }
                    
                    # Закрываем все позиции через TradeManager
                    import importlib
                    import trading_bot.trade_manager
                    importlib.reload(trading_bot.trade_manager)
                    from trading_bot.trade_manager import TradeManager
                    
                    # Используем тот же data_dir, что и дашборд
                    manager = TradeManager(token, dry_run=True, debug_mode=True, data_dir=DATA_DIR_PATH)
                    
                    # Используем метод close_all_positions, который правильно обрабатывает все
                    manager.close_all_positions(current_prices)
                    
                    # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: убеждаемся, что файл действительно очищен
                    # Загружаем файл и проверяем
                    import time
                    time.sleep(0.5)  # Даем время на сохранение
                    
                    # Проверяем результат
                    with open(TRADES_ACTIVE, 'r') as f:
                        remaining_trades = json.load(f)
                    remaining_count = len([t for t in remaining_trades.values() if t.get('status') == 'OPEN'])
                    
                    if remaining_count > 0:
                        # Если остались позиции, принудительно очищаем файл
                        cleaned_trades = {k: v for k, v in remaining_trades.items() if v.get('status') == 'OPEN'}
                        with open(TRADES_ACTIVE, 'w') as f:
                            json.dump(cleaned_trades, f, indent=4, default=str)
                        st.warning(f"⚠️ Очищено дополнительно {remaining_count} позиций")
                    
                    st.success(f"✅ Закрыто {len(active_trades)} позиций")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка закрытия позиций: {e}")
                    st.exception(e)
        else:
            st.button("🛑 Закрыть все позиции", key="close_all", disabled=True, help="Нет активных позиций")
    
    with col_stop:
        stop_flag_file = BASE_DIR / "stop_bot.flag"
        is_stopped = stop_flag_file.exists()
        
        if is_stopped:
            if st.button("▶️ Запустить бота", key="start_bot", type="primary"):
                try:
                    stop_flag_file.unlink()
                    st.success("✅ Бот запущен")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
        else:
            if st.button("⏹️ Остановить бота", key="stop_bot", type="secondary"):
                try:
                    stop_flag_file.parent.mkdir(parents=True, exist_ok=True)
                    stop_flag_file.touch()
                    st.warning("⚠️ Сигнал остановки отправлен. Бот закроет все позиции и остановится.")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
    
    active_trades, history_trades = load_data()
    
    # --- KPI Метрики ---
    total_trades = len(history_trades)
    
    if total_trades > 0:
        df_history = pd.DataFrame(history_trades)
        
        # Гарантируем числовой тип данных
        if 'net_profit' in df_history.columns:
            df_history['net_profit'] = pd.to_numeric(df_history['net_profit'], errors='coerce').fillna(0)
            
        total_pnl = df_history['net_profit'].sum()
        wins = len(df_history[df_history['net_profit'] > 0])
        win_rate = (wins / total_trades) * 100
        avg_trade = df_history['net_profit'].mean()
        
        gross_profit = df_history[df_history['net_profit'] > 0]['net_profit'].sum()
        gross_loss = abs(df_history[df_history['net_profit'] < 0]['net_profit'].sum())
        
        if gross_loss > 0:
            profit_factor = gross_profit / gross_loss
        else:
            profit_factor = float('inf') if gross_profit > 0 else 0
    else:
        total_pnl = 0
        win_rate = 0
        avg_trade = 0
        profit_factor = 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Общий P&L", f"{total_pnl:.2f} ₽", delta_color="normal")
    col2.metric("📊 Сделок", total_trades)
    col3.metric("🎯 Win Rate", f"{win_rate:.1f}%")
    col4.metric("⚖️ Profit Factor", f"{profit_factor:.2f}")
    
    # --- АКТИВНЫЕ ПОЗИЦИИ ---
    st.subheader(f"🟢 Активные позиции ({len(active_trades)})")
    
    if active_trades:
        # Сортируем активные позиции по времени входа, чтобы нумерация была хронологической и продолжала историю
        sorted_active = sorted(active_trades.items(), key=lambda x: x[1].get('entry_time', ''))
        start_number = len(history_trades) + 1
        
        active_list = []
        for i, (t, data) in enumerate(sorted_active, start_number):
            # Если нет текущих данных MFE/MAE, ставим 0
            mfe = data.get('mfe', 0)
            mae = data.get('mae', 0)
            
            active_list.append({
                "№": i,
                "Ticker": t,
                "Type": data.get('entry_mode', 'ema_squeeze' if 'EMA' in data.get('strategy_desc', '') or 'зажата' in data.get('strategy_desc', '') else 'Unknown'),
                "TF": extract_timeframe(data.get('strategy_desc', '')),
                "Dir": data['direction'],
                "Entry": data['entry_price'],
                "Lots": data['quantity_lots'],
                "SL": data['stop_loss'],
                "TP": data['take_profit'],
                "Time": data['entry_time'][5:16], # MM-DD HH:MM
                "MFE": f"{mfe:.2f}",
                "MAE": f"{mae:.2f}",
                "AI Prob": f"{data.get('ai_probability', 0):.1%}"
            })
        
        st.dataframe(pd.DataFrame(active_list), use_container_width=True)
    else:
        st.info("Нет активных позиций")
        
    # --- ИСТОРИЯ СДЕЛОК, АНАЛИТИКА, ПЕРЕРИСОВКИ И АКТИВНЫЕ ПОЗИЦИИ ---
    # Создаем вкладки всегда (даже если нет данных)
    tab_names = []
    tab_names.extend(["📜 История сделок", "📈 Кривая доходности", "📊 Аналитика", "🔄 Перерисовки"])
    tab_names.append("🟢 Активные позиции")
    
    tabs = st.tabs(tab_names)
    tab_idx = 0
    
    # Вкладка 1: История сделок
    with tabs[tab_idx]:
        st.subheader("📜 История сделок")
        if history_trades:
            # Преобразуем для таблицы
            history_display = []
            total_history = len(history_trades)
            for i, t in enumerate(reversed(history_trades)): # Новые сверху
                history_display.append({
                    "№": total_history - i,
                    "Time": t['exit_time'][5:16], # MM-DD HH:MM
                    "Ticker": t['ticker'],
                    "Type": t.get('entry_mode', 'ema_squeeze' if 'EMA' in t.get('strategy_desc', '') or 'зажата' in t.get('strategy_desc', '') else 'Unknown'),
                    "TF": extract_timeframe(t.get('strategy_desc', '')),
                    "Dir": t['direction'],
                    "P&L": f"{t['net_profit']:.2f}",
                    "Reason": t['close_reason'],
                    "MFE": f"{t.get('mfe', 0):.2f}",
                    "MAE": f"{t.get('mae', 0):.2f}",
                    "AI Prob": f"{t.get('ai_probability', 0):.1%}"
                })
                
            df_display = pd.DataFrame(history_display)
            
            # Подсветка P&L
            def highlight_pnl(val):
                try:
                    v = float(val)
                    color = 'green' if v > 0 else 'red'
                    return f'color: {color}'
                except:
                    return ''

            st.dataframe(df_display.style.applymap(highlight_pnl, subset=['P&L']), use_container_width=True)
            
            # --- ВИЗУАЛИЗАЦИЯ СДЕЛКИ ---
            st.divider()
            st.subheader("📊 Визуализация сделки")
        
            # Выбор сделки для визуализации
            trade_options = []
            total_history = len(history_trades)
            for i, t in enumerate(reversed(history_trades)):
                trade_num = total_history - i
                pnl = t['net_profit']
                pnl_sign = "✅" if pnl > 0 else "❌"
                timeframe = extract_timeframe(t.get('strategy_desc', ''))
                timeframe_str = f"[{timeframe}]" if timeframe != "N/A" else ""
                trade_options.append(f"#{trade_num} {pnl_sign} {t['ticker']} ({t['direction']}) {timeframe_str} - {t['exit_time'][5:16]} | P&L: {pnl:.2f} ₽")
            
            if trade_options:
                    selected_trade_idx = st.selectbox(
                        "Выберите сделку для визуализации:",
                        options=range(len(trade_options)),
                        format_func=lambda x: trade_options[x],
                        key='trade_selector'
                    )
                    
                    if selected_trade_idx is not None:
                        selected_trade = list(reversed(history_trades))[selected_trade_idx]
                        
                        # Загружаем snapshot свечей
                        snapshot_file = selected_trade.get('snapshot_file', '')
                        pattern_file = selected_trade.get('id', '') + '_pattern.json'
                        
                        snapshots_dir = BASE_DIR / "training_data" / "snapshots"
                        snapshot_path = snapshots_dir / snapshot_file if snapshot_file else None
                        pattern_path = snapshots_dir / pattern_file if pattern_file else None
                        
                        if snapshot_path and snapshot_path.exists():
                            try:
                                df_snapshot = pd.read_csv(snapshot_path)
                                
                                # Загружаем паттерн
                                pattern_info = None
                                if pattern_path and pattern_path.exists():
                                    with open(pattern_path, 'r') as f:
                                        pattern_info = json.load(f)
                                
                                # Создаем график
                                trade_data = {
                                    'entry_price': selected_trade.get('entry_price'),
                                    'exit_price': selected_trade.get('exit_price'),
                                    'stop_loss': selected_trade.get('stop_loss'),
                                    'take_profit': selected_trade.get('take_profit'),
                                    'entry_time': selected_trade.get('entry_time'),
                                    'exit_time': selected_trade.get('exit_time')
                                }
                                
                                fig = create_trade_chart(df_snapshot, pattern_info, trade_data)
                                
                                # Информация о сделке
                                qty = int(selected_trade.get('quantity_lots', 1))
                                lot_sz = int(selected_trade.get('lot_size', 1))
                                vol = qty * lot_sz
                                entry_p = selected_trade.get('entry_price') or 0
                                exit_p = selected_trade.get('exit_price') or 0
                                gross = selected_trade.get('gross_profit', 0)
                                net = selected_trade.get('net_profit', 0)
                                comm = selected_trade.get('commission_total', 0)
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("P&L (нетто)", f"{net:.2f} ₽", delta=f"{gross:.2f} ₽ (брутто)")
                                    st.caption(f"Комиссия: {comm:.2f} ₽")
                                with col2:
                                    st.metric("Вход", f"{entry_p:.2f} ₽")
                                    if exit_p:
                                        st.metric("Выход", f"{exit_p:.2f} ₽")
                                    st.caption(f"Объём: {vol} шт. ({qty} лотов × {lot_sz})")
                                with col3:
                                    st.metric("MFE (руб/шт.)", f"{selected_trade.get('mfe', 0):.2f}")
                                    st.metric("MAE (руб/шт.)", f"{selected_trade.get('mae', 0):.2f}")
                                # Формула для проверки: брутто = (выход − вход) × объём, нетто = брутто − комиссия
                                if entry_p and exit_p and vol:
                                    expected_gross = (exit_p - entry_p) * vol if (selected_trade.get('direction') or '').upper() == 'LONG' else (entry_p - exit_p) * vol
                                    st.caption(f"Проверка: (Выход − Вход) × {vol} = {expected_gross:.2f} ₽ брутто → нетто = {expected_gross:.2f} − {comm:.2f} = {expected_gross - comm:.2f} ₽")
                                
                                st.plotly_chart(fig, use_container_width=True, width='stretch')
                                
                                # Дополнительная информация
                                with st.expander("📋 Детали сделки"):
                                    st.json(selected_trade)
                                    if pattern_info:
                                        st.subheader("Информация о паттерне")
                                        st.json(pattern_info)
                            except Exception as e:
                                st.error(f"❌ Ошибка загрузки данных: {e}")
                                st.exception(e)
                        else:
                            st.warning(f"⚠️ Snapshot файл не найден: {snapshot_file}")
        else:
            st.info("Пока нет закрытых сделок")
            
        tab_idx += 1
        
        # Вкладка 2: Кривая доходности
        with tabs[tab_idx]:
            st.subheader("📈 Кривая доходности")
            if history_trades and total_trades > 0:
                df_history = pd.DataFrame(history_trades)
                df_history['exit_time'] = pd.to_datetime(df_history['exit_time'], format='ISO8601', errors='coerce')
                df_history = df_history.sort_values('exit_time')
                df_history['cumulative_pnl'] = df_history['net_profit'].cumsum()
                
                fig = px.line(df_history, x='exit_time', y='cumulative_pnl', markers=True)
                fig.update_layout(
                    xaxis_title="Дата и время",
                    yaxis_title="P&L (RUB)",
                    xaxis=dict(tickformat='%d.%m.%Y %H:%M')
                )
                st.plotly_chart(fig, use_container_width=True, width='stretch')
            else:
                st.info("Нет данных для построения графика доходности")
        
        tab_idx += 1

        # Вкладка 3: Аналитика
        with tabs[tab_idx]:
            if history_trades:
                st.subheader("📊 Анализ совершенных сделок")
                
                df_analysis = pd.DataFrame(history_trades)
                df_analysis['net_profit'] = pd.to_numeric(df_analysis['net_profit'], errors='coerce').fillna(0)
                df_analysis['entry_time'] = pd.to_datetime(df_analysis['entry_time'], format='ISO8601', errors='coerce')
                df_analysis['exit_time'] = pd.to_datetime(df_analysis['exit_time'], format='ISO8601', errors='coerce')
                
                # Убираем timezone для корректного вычитания (универсальный метод)
                # Используем более надежный подход - преобразуем через pd.to_datetime с utc=False
                if pd.api.types.is_datetime64_any_dtype(df_analysis['entry_time']):
                    # Преобразуем в naive datetime, удаляя timezone
                    try:
                        # Пробуем через dt.tz_convert если есть timezone
                        if df_analysis['entry_time'].dt.tz is not None:
                            df_analysis['entry_time'] = df_analysis['entry_time'].dt.tz_convert(None)
                    except:
                        pass
                    # Дополнительная проверка через apply для каждого элемента
                    df_analysis['entry_time'] = df_analysis['entry_time'].apply(
                        lambda x: x.replace(tzinfo=None) if x is not None and pd.notna(x) and hasattr(x, 'tzinfo') and x.tzinfo is not None else x
                    )
                    # Финальное преобразование через pd.to_datetime для гарантии
                    df_analysis['entry_time'] = pd.to_datetime(df_analysis['entry_time'], errors='coerce')
                
                if pd.api.types.is_datetime64_any_dtype(df_analysis['exit_time']):
                    try:
                        if df_analysis['exit_time'].dt.tz is not None:
                            df_analysis['exit_time'] = df_analysis['exit_time'].dt.tz_convert(None)
                    except:
                        pass
                    df_analysis['exit_time'] = df_analysis['exit_time'].apply(
                        lambda x: x.replace(tzinfo=None) if x is not None and pd.notna(x) and hasattr(x, 'tzinfo') and x.tzinfo is not None else x
                    )
                    df_analysis['exit_time'] = pd.to_datetime(df_analysis['exit_time'], errors='coerce')
                
                # Вычисляем время удержания только для валидных datetime
                valid_times = df_analysis['entry_time'].notna() & df_analysis['exit_time'].notna()
                df_analysis['hold_time_hours'] = None
                if valid_times.any():
                    # Используем преобразование в UTC для гарантированного вычитания
                    entry_s = pd.to_datetime(df_analysis.loc[valid_times, 'entry_time'], utc=True)
                    exit_s = pd.to_datetime(df_analysis.loc[valid_times, 'exit_time'], utc=True)
                    
                    # Вычисляем разницу
                    time_diff = exit_s - entry_s
                    # Конвертируем в часы
                    df_analysis.loc[valid_times, 'hold_time_hours'] = time_diff.dt.total_seconds() / 3600
                df_analysis['timeframe'] = df_analysis['strategy_desc'].apply(extract_timeframe)
                
                # Основные метрики
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    total_trades_count = len(df_analysis)
                    st.metric("Всего сделок", total_trades_count)
                with col2:
                    wins = len(df_analysis[df_analysis['net_profit'] > 0])
                    win_rate = (wins / total_trades_count * 100) if total_trades_count > 0 else 0
                    st.metric("Прибыльных", f"{wins} ({win_rate:.1f}%)")
                with col3:
                    avg_profit = df_analysis['net_profit'].mean()
                    st.metric("Средний P&L", f"{avg_profit:.2f} ₽")
                with col4:
                    total_commission = df_analysis.get('commission_total', pd.Series([0] * len(df_analysis))).sum()
                    st.metric("Комиссии", f"{total_commission:.2f} ₽")
                
                # Анализ по направлениям
                st.write("**📈 Анализ по направлениям:**")
                direction_stats = df_analysis.groupby('direction').agg({
                    'net_profit': ['count', 'sum', 'mean'],
                    'close_reason': lambda x: (x == 'TAKE PROFIT').sum()
                }).round(2)
                direction_stats.columns = ['Сделок', 'Общий P&L', 'Средний P&L', 'TP закрытий']
                st.dataframe(direction_stats, use_container_width=True)
                
                # Анализ по причинам закрытия
                st.write("**🎯 Анализ по причинам закрытия:**")
                reason_stats = df_analysis.groupby('close_reason').agg({
                    'net_profit': ['count', 'sum', 'mean']
                }).round(2)
                reason_stats.columns = ['Количество', 'Общий P&L', 'Средний P&L']
                st.dataframe(reason_stats, use_container_width=True)
                
                # Анализ по тикерам
                st.write("**🏷️ Топ-5 тикеров по количеству сделок:**")
                ticker_stats = df_analysis.groupby('ticker').agg({
                    'net_profit': ['count', 'sum', 'mean']
                }).round(2)
                ticker_stats.columns = ['Сделок', 'Общий P&L', 'Средний P&L']
                ticker_stats = ticker_stats.sort_values('Сделок', ascending=False).head(5)
                st.dataframe(ticker_stats, use_container_width=True)
                
                # Анализ по типам стратегии (entry_mode)
                st.write("**🧠 Анализ по типу входа (Entry Mode):**")
                # Проверяем, есть ли колонка entry_mode, если нет - создаем из strategy_desc
                if 'entry_mode' not in df_analysis.columns:
                     df_analysis['entry_mode'] = df_analysis['strategy_desc'].apply(
                         lambda x: 'ema_squeeze' if x and ('EMA' in x or 'зажата' in x) else 'Unknown'
                     )
                else:
                     # Заполняем пропуски для старых сделок
                     mask_unknown = df_analysis['entry_mode'].isna() | (df_analysis['entry_mode'] == 'Unknown')
                     if mask_unknown.any():
                         df_analysis.loc[mask_unknown, 'entry_mode'] = df_analysis.loc[mask_unknown, 'strategy_desc'].apply(
                             lambda x: 'ema_squeeze' if x and ('EMA' in x or 'зажата' in x) else 'Unknown'
                         )
                     
                mode_stats = df_analysis.groupby('entry_mode').agg({
                    'net_profit': ['count', 'sum', 'mean'],
                    'close_reason': lambda x: (x == 'TAKE PROFIT').sum()
                }).round(2)
                mode_stats.columns = ['Сделок', 'Общий P&L', 'Средний P&L', 'TP закрытий']
                st.dataframe(mode_stats, use_container_width=True)
                
                # Визуализация распределения P&L
                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig_hist = px.histogram(df_analysis, x='net_profit', nbins=20, 
                                           title='Распределение P&L по сделкам',
                                           labels={'net_profit': 'P&L (₽)', 'count': 'Количество'})
                    fig_hist.add_vline(x=0, line_dash="dash", line_color="red", 
                                      annotation_text="Безубыток")
                    st.plotly_chart(fig_hist, use_container_width=True)
                
                with col_chart2:
                    # Время удержания позиций
                    fig_hold = px.box(df_analysis, y='hold_time_hours', 
                                     title='Время удержания позиций (часы)',
                                     labels={'hold_time_hours': 'Часы'})
                    st.plotly_chart(fig_hold, use_container_width=True)
                
                # Выводы и рекомендации
                st.write("**💡 Выводы и рекомендации:**")
                conclusions = []
                
                if win_rate < 30:
                    conclusions.append(f"⚠️ **Низкий Win Rate ({win_rate:.1f}%)** - большинство сделок закрываются с убытком. Рекомендуется пересмотреть критерии входа или улучшить фильтрацию паттернов.")
                
                if avg_profit < 0:
                    conclusions.append(f"⚠️ **Средний P&L отрицательный ({avg_profit:.2f} ₽)** - стратегия в текущем виде убыточна. Необходима оптимизация параметров.")
                
                tp_closes = len(df_analysis[df_analysis['close_reason'] == 'TAKE PROFIT'])
                sl_closes = len(df_analysis[df_analysis['close_reason'] == 'STOP LOSS'])
                if sl_closes > tp_closes * 2:
                    conclusions.append(f"⚠️ **Дисбаланс выходов** - {sl_closes} закрытий по SL vs {tp_closes} по TP. Возможно, стопы слишком близко или тейки слишком далеко.")
                
                # Проверка комиссий
                avg_commission = total_commission / total_trades_count if total_trades_count > 0 else 0
                if avg_commission > abs(avg_profit) * 0.5:
                    conclusions.append(f"⚠️ **Высокие комиссии** - средняя комиссия ({avg_commission:.2f} ₽) составляет значительную долю от среднего P&L. Рассмотрите увеличение размера позиций или снижение частоты сделок.")
                
                # Проверка AI фильтра
                if df_analysis['ai_probability'].sum() == 0:
                    conclusions.append("ℹ️ **AI фильтр не активен** - все сделки имеют вероятность 0.0. Проверьте, загружена ли ML модель и работает ли фильтрация.")
                
                # Анализ по таймфреймам
                if 'timeframe' in df_analysis.columns:
                    tf_stats = df_analysis.groupby('timeframe')['net_profit'].agg(['count', 'sum', 'mean']).round(2)
                    tf_stats.columns = ['Сделок', 'Общий P&L', 'Средний P&L']
                    if len(tf_stats) > 0:
                        best_tf = tf_stats['Средний P&L'].idxmax()
                        conclusions.append(f"📊 **Лучший таймфрейм** - {best_tf} (средний P&L: {tf_stats.loc[best_tf, 'Средний P&L']:.2f} ₽)")
                
                if conclusions:
                    for conclusion in conclusions:
                        st.write(conclusion)
                else:
                    st.success("✅ Все показатели в норме!")
                
                # Дополнительная статистика
                with st.expander("📈 Детальная статистика"):
                    st.write("**Распределение по таймфреймам:**")
                    if 'timeframe' in df_analysis.columns:
                        st.dataframe(df_analysis.groupby('timeframe')['net_profit'].agg(['count', 'sum', 'mean']).round(2), 
                                   use_container_width=True)
                    
                    st.write("**Статистика MFE/MAE:**")
                    mfe_mae_stats = df_analysis[['mfe', 'mae']].describe()
                    st.dataframe(mfe_mae_stats, use_container_width=True)
            else:
                st.info("Нет данных для анализа")
        
        tab_idx += 1
        
        # Вкладка 4: Перерисовки
        with tabs[tab_idx]:
            st.subheader("🔄 История перерисовки паттернов")
            
            if history_trades:
                try:
                    from trading_bot.pattern_tracker import PatternTracker
                    pattern_tracker = PatternTracker()
                    
                    # Получаем список всех тикеров/таймфреймов с историей
                    all_keys = list(pattern_tracker.pattern_history.keys())
                    
                    if all_keys:
                        # Выбор тикера и таймфрейма для просмотра
                        selected_key = st.selectbox(
                            "Выберите тикер/таймфрейм:",
                            options=all_keys,
                            format_func=lambda x: x.replace('_', ' - '),
                            key='repaint_selector'
                        )
                        
                        if selected_key:
                            ticker, tf = selected_key.split('_', 1)
                            history = pattern_tracker.get_pattern_history(ticker, tf, limit=20)
                            
                            if history:
                                # Статистика перерисовок
                                repaint_count = sum(1 for p in history if p.get('is_repaint', False))
                                total_count = len(history)
                                repaint_rate = (repaint_count / total_count * 100) if total_count > 0 else 0
                                
                                col_stat1, col_stat2, col_stat3 = st.columns(3)
                                with col_stat1:
                                    st.metric("Всего паттернов", total_count)
                                with col_stat2:
                                    st.metric("Перерисованных", repaint_count)
                                with col_stat3:
                                    st.metric("Процент перерисовки", f"{repaint_rate:.1f}%")
                                
                                # Таблица истории
                                history_display = []
                                for i, record in enumerate(reversed(history[-20:]), 1):  # Последние 20
                                    pattern = record['pattern']
                                    t4 = pattern.get('t4', {})
                                    
                                    history_display.append({
                                        "№": len(history) - i + 1,
                                        "Время T4": record.get('t4_time', '')[:16] if record.get('t4_time') else 'N/A',
                                        "T0": f"{pattern.get('t0', {}).get('idx', 0)}",
                                        "T1": f"{pattern.get('t1', {}).get('idx', 0)}",
                                        "T4": f"{t4.get('idx', 0)}",
                                        "Перерисован": "✅ Да" if record.get('is_repaint') else "❌ Нет",
                                        "Подпись": (record.get('signature', '') or '')[:8] + "..."
                                    })
                                
                                df_history = pd.DataFrame(history_display)
                                st.dataframe(df_history, use_container_width=True)
                            else:
                                st.info("Нет истории паттернов для выбранного инструмента")
                    else:
                        st.info("Пока нет истории паттернов")
                except Exception as e:
                    st.warning(f"⚠️ Ошибка загрузки истории перерисовки: {e}")
            else:
                st.info("Нет данных для анализа перерисовок")
        
        tab_idx += 1
        
        # Вкладка 5: Активные позиции
        with tabs[tab_idx]:
            if active_trades:
                st.subheader("📊 Визуализация активной позиции")
                
                # Сортируем активные позиции по времени входа (как в таблице)
                # Это обеспечивает порядковую нумерацию, продолжающую историю
                sorted_active = sorted(active_trades.items(), key=lambda x: x[1].get('entry_time', ''))
                start_number = len(history_trades) + 1
                
                # Выбор активной позиции с порядковым номером
                active_options = []
                ticker_list = []  # Сохраняем соответствие между индексом и тикером
                
                for i, (ticker, data) in enumerate(sorted_active, start_number):
                    entry_time_str = data.get('entry_time', '')
                    entry_time_short = entry_time_str[11:19] if len(entry_time_str) > 19 else entry_time_str
                    timeframe = extract_timeframe(data.get('strategy_desc', ''))
                    timeframe_str = f"[{timeframe}]" if timeframe != "N/A" else ""
                    active_options.append(f"#{i}: {ticker} ({data['direction']}) {timeframe_str} - {entry_time_short}")
                    ticker_list.append(ticker)
                
                selected_active_idx = st.selectbox(
                    "Выберите активную позицию:",
                    options=range(len(active_options)),
                    format_func=lambda x: active_options[x],
                    key='active_trade_selector'
                )
                
                if selected_active_idx is not None and selected_active_idx < len(ticker_list):
                    selected_ticker = ticker_list[selected_active_idx]
                    selected_trade = active_trades[selected_ticker]
                    
                    # Загружаем snapshot
                    snapshot_file = selected_trade.get('snapshot_file', '')
                    pattern_file = selected_trade.get('id', '') + '_pattern.json'
                    
                    snapshots_dir = BASE_DIR / "training_data" / "snapshots"
                    snapshot_path = snapshots_dir / snapshot_file if snapshot_file else None
                    pattern_path = snapshots_dir / pattern_file if pattern_file else None
                    
                    # ВАЖНО: Сначала загружаем паттерн, чтобы знать времена точек
                    pattern_info = None
                    if pattern_path and pattern_path.exists():
                        try:
                            with open(pattern_path, 'r') as f:
                                pattern_info = json.load(f)
                            st.success(f"✅ Паттерн загружен из {pattern_path.name}")
                        except Exception as e:
                            st.warning(f"⚠️ Ошибка загрузки паттерна: {e}")
                    else:
                        if pattern_path:
                            st.warning(f"⚠️ Файл паттерна не найден: {pattern_path}")
                        else:
                            st.info(f"ℹ️ Файл паттерна не указан (pattern_file: {pattern_file})")
                    
                    if snapshot_path and snapshot_path.exists():
                        try:
                            # Загружаем snapshot для паттерна
                            df_snapshot = pd.read_csv(snapshot_path)
                            
                            # Для активных позиций загружаем актуальные свечи
                            use_live_data = st.checkbox("📊 Показать актуальные данные", value=True, key=f"live_data_{selected_ticker}")
                            
                            df_live = pd.DataFrame()  # Инициализируем пустым
                            current_price = None
                            current_pnl = selected_trade.get('mfe', 0)
                            
                            if use_live_data:
                                # Определяем таймфрейм из strategy_desc или используем 1h по умолчанию
                                strategy_desc = selected_trade.get('strategy_desc', '')
                                timeframe = extract_timeframe(strategy_desc)
                                
                                # Определяем интервал свечей на основе таймфрейма
                                from config import TIMEFRAMES
                                if timeframe in TIMEFRAMES:
                                    candle_interval = TIMEFRAMES[timeframe]['interval']
                                    days_back = TIMEFRAMES[timeframe]['days_back']
                                else:
                                    # По умолчанию используем часовой интервал
                                    candle_interval = CandleInterval.CANDLE_INTERVAL_HOUR
                                    days_back = 60
                                
                                entry_time = pd.to_datetime(selected_trade.get('entry_time', datetime.now() - timedelta(days=days_back)))
                                # Убираем timezone для корректного сравнения
                                if entry_time.tzinfo is not None:
                                    entry_time = entry_time.replace(tzinfo=None)
                                class_code = selected_trade.get('class_code', 'TQBR')
                                
                                # ВАЖНО: Если есть паттерн, загружаем данные с момента самого раннего времени паттерна
                                if pattern_info:
                                    # Находим самое раннее время из паттерна
                                    pattern_times = []
                                    for point_key in ['t0', 't1', 't2', 't3', 't4']:
                                        if point_key in pattern_info and 'time' in pattern_info[point_key]:
                                            try:
                                                pt = pd.to_datetime(pattern_info[point_key]['time'])
                                                if pt.tzinfo is not None:
                                                    pt = pt.replace(tzinfo=None)
                                                pattern_times.append(pt)
                                            except:
                                                pass
                                    
                                    if pattern_times:
                                        earliest_pattern_time = min(pattern_times)
                                        # Загружаем данные с момента паттерна (минус несколько дней для контекста)
                                        from_date = earliest_pattern_time - timedelta(days=5)
                                        # Но не раньше, чем days_back дней назад
                                        from_date = max(from_date, datetime.now() - timedelta(days=days_back))
                                    else:
                                        # Если нет времени в паттерне, используем стандартный метод
                                        from_date = max(entry_time, datetime.now() - timedelta(days=days_back))
                                else:
                                    # Загружаем свежие свечи с момента входа (или за последние days_back дней)
                                    from_date = max(entry_time, datetime.now() - timedelta(days=days_back))
                                
                                df_live = get_current_candles(selected_ticker, class_code, from_date, candle_interval)
                                
                                if not df_live.empty:
                                    # Убеждаемся, что колонка time есть и в правильном формате
                                    if 'time' not in df_snapshot.columns:
                                        # Если нет колонки time, создаем её из индекса
                                        df_snapshot = df_snapshot.reset_index(drop=True)
                                        # Определяем частоту на основе таймфрейма
                                        if timeframe == '1d':
                                            freq = 'D'  # Дневная частота
                                            start_time = entry_time - timedelta(days=len(df_snapshot))
                                        elif timeframe == '1h':
                                            freq = 'H'  # Часовая частота
                                            start_time = entry_time - timedelta(hours=len(df_snapshot))
                                        else:
                                            freq = 'H'  # По умолчанию часовая
                                            start_time = entry_time - timedelta(hours=len(df_snapshot))
                                        df_snapshot['time'] = pd.date_range(start=start_time, periods=len(df_snapshot), freq=freq)
                                    
                                    # Преобразуем time в datetime для обоих датафреймов и нормализуем timezone
                                    df_snapshot['time'] = pd.to_datetime(df_snapshot['time'], format='ISO8601', errors='coerce')
                                    if df_snapshot['time'].dt.tz is not None:
                                        df_snapshot['time'] = df_snapshot['time'].dt.tz_localize(None)
                                    
                                    df_live['time'] = pd.to_datetime(df_live['time'], format='ISO8601', errors='coerce')
                                    if df_live['time'].dt.tz is not None:
                                        df_live['time'] = df_live['time'].dt.tz_localize(None)
                                    
                                    # Объединяем snapshot и live данные
                                    # Берем все snapshot данные и добавляем live данные
                                    df_combined = pd.concat([df_snapshot, df_live], ignore_index=True)
                                    
                                    # Удаляем дубликаты по времени, оставляя последние (live данные имеют приоритет)
                                    df_combined = df_combined.drop_duplicates(subset=['time'], keep='last')
                                    
                                    # Сортируем по времени для правильного отображения свечей
                                    df_combined = df_combined.sort_values('time').reset_index(drop=True)
                                    
                                    # КОРРЕКТИРОВКА ИНДЕКСОВ ПАТТЕРНА:
                                    # Индексы паттерна были относительно df_snapshot, но теперь нужно найти
                                    # соответствующие индексы в df_combined по времени
                                    if pattern_info and 'time' in df_combined.columns:
                                        # Используем время из паттерна для точного сопоставления
                                        for point_key in ['t0', 't1', 't2', 't3', 't4']:
                                            if point_key in pattern_info and 'time' in pattern_info[point_key]:
                                                pattern_time_str = pattern_info[point_key]['time']
                                                try:
                                                    # Преобразуем время паттерна в datetime
                                                    pattern_time = pd.to_datetime(pattern_time_str)
                                                    if pattern_time.tzinfo is not None:
                                                        pattern_time = pattern_time.replace(tzinfo=None)
                                                    
                                                    # Находим ближайшую свечу в df_combined по времени
                                                    time_diffs = abs(df_combined['time'] - pattern_time)
                                                    closest_idx = time_diffs.idxmin()
                                                    
                                                    # Проверяем, что разница во времени не слишком большая (например, не более 1 дня)
                                                    min_diff = time_diffs.min()
                                                    if min_diff < pd.Timedelta(days=1):
                                                        # Обновляем индекс в pattern_info
                                                        pattern_info[point_key]['idx'] = int(closest_idx)
                                                    else:
                                                        st.warning(f"⚠️ Не найдена свеча для {point_key} (время: {pattern_time_str}, минимальная разница: {min_diff})")
                                                except Exception as e:
                                                    st.warning(f"⚠️ Ошибка сопоставления времени для {point_key}: {e}")
                                            elif point_key in pattern_info and 'idx' in pattern_info[point_key]:
                                                # Если нет времени, используем старый метод (смещение)
                                                snapshot_first_time = df_snapshot['time'].iloc[0] if not df_snapshot.empty and 'time' in df_snapshot.columns else None
                                                if snapshot_first_time is not None:
                                                    matching_indices = df_combined[df_combined['time'] == snapshot_first_time].index
                                                    if len(matching_indices) > 0:
                                                        snapshot_start_idx = matching_indices[0]
                                                        old_idx = int(pattern_info[point_key]['idx'])
                                                        new_idx = snapshot_start_idx + old_idx
                                                        if 0 <= new_idx < len(df_combined):
                                                            pattern_info[point_key]['idx'] = new_idx
                                    
                                    # Убеждаемся, что все необходимые колонки есть и в правильном формате
                                    required_cols = ['open', 'high', 'low', 'close']
                                    for col in required_cols:
                                        if col not in df_combined.columns:
                                            st.warning(f"⚠️ Отсутствует колонка {col} в данных")
                                        elif df_combined[col].isna().any():
                                            # Заполняем пропущенные значения предыдущими значениями
                                            df_combined[col] = df_combined[col].fillna(method='ffill').fillna(method='bfill')
                                    
                                    # Убеждаемся, что high >= max(open, close) и low <= min(open, close)
                                    df_combined['high'] = df_combined[['high', 'open', 'close']].max(axis=1)
                                    df_combined['low'] = df_combined[['low', 'open', 'close']].min(axis=1)
                                    
                                    # Вычисляем текущий P&L
                                    current_price = df_live.iloc[-1]['close']
                                    entry_price = selected_trade.get('entry_price')
                                    direction = selected_trade.get('direction', 'LONG')
                                    
                                    if direction == 'LONG':
                                        current_pnl = current_price - entry_price
                                    else:
                                        current_pnl = entry_price - current_price
                                    
                                    df_to_plot = df_combined
                                else:
                                    df_to_plot = df_snapshot
                                    current_pnl = selected_trade.get('mfe', 0)
                            else:
                                df_to_plot = df_snapshot
                                current_pnl = selected_trade.get('mfe', 0)
                            
                            # Создаем график (без exit_price, так как позиция еще открыта)
                            trade_data = {
                                'entry_price': selected_trade.get('entry_price'),
                                'exit_price': None,  # Позиция еще открыта
                                'stop_loss': selected_trade.get('stop_loss'),
                                'take_profit': selected_trade.get('take_profit'),
                                'entry_time': selected_trade.get('entry_time')
                            }
                            
                            fig = create_trade_chart(df_to_plot, pattern_info, trade_data)
                            
                            # Добавляем текущую цену на график, если используем live данные
                            if use_live_data and not df_live.empty and current_price is not None:
                                current_idx = len(df_to_plot) - 1
                                # Используем дату/время из DataFrame, если есть колонка 'time'
                                if 'time' in df_to_plot.columns and current_idx < len(df_to_plot):
                                    try:
                                        if not pd.api.types.is_datetime64_any_dtype(df_to_plot['time']):
                                            df_to_plot['time'] = pd.to_datetime(df_to_plot['time'], format='ISO8601', errors='coerce')
                                        current_x = df_to_plot['time'].iloc[current_idx]
                                    except:
                                        current_x = current_idx
                                else:
                                    current_x = current_idx
                                fig.add_trace(go.Scatter(
                                    x=[current_x],
                                    y=[current_price],
                                    mode='markers+text',
                                    marker=dict(size=15, color='orange', symbol='star', line=dict(width=2, color='white')),
                                    text=['CURRENT'],
                                    textposition='top center',
                                    name='Текущая цена',
                                    showlegend=True,
                                    hovertemplate=f'<b>ТЕКУЩАЯ ЦЕНА</b><br>Цена: {current_price:.2f}<br>P&L: {current_pnl:.2f}<extra></extra>'
                                ), row=1, col=1)
                            
                            # Информация о позиции
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                if use_live_data and not df_live.empty:
                                    st.metric("Текущий P&L", f"{current_pnl:.2f} ₽", 
                                            delta=f"MFE: {selected_trade.get('mfe', 0):.2f}")
                                else:
                                    st.metric("Текущий P&L", f"{selected_trade.get('mfe', 0):.2f} (MFE)")
                                st.metric("Худший P&L", f"{selected_trade.get('mae', 0):.2f} (MAE)")
                            with col2:
                                st.metric("Вход", f"{selected_trade.get('entry_price', 0):.2f} ₽")
                                if use_live_data and not df_live.empty and current_price is not None:
                                    st.metric("Текущая цена", f"{current_price:.2f} ₽")
                                st.metric("Stop Loss", f"{selected_trade.get('stop_loss', 0):.2f} ₽")
                            with col3:
                                st.metric("Take Profit", f"{selected_trade.get('take_profit', 0):.2f} ₽")
                                st.metric("AI Вероятность", f"{selected_trade.get('ai_probability', 0):.1%}")
                            
                            st.plotly_chart(fig, use_container_width=True, width='stretch')
                            
                        except Exception as e:
                            st.error(f"❌ Ошибка загрузки данных: {e}")
                            st.exception(e)
                    else:
                        st.warning(f"⚠️ Snapshot файл не найден: {snapshot_file}")
            else:
                st.info("Нет активных позиций для визуализации")

if __name__ == "__main__":
    main()
